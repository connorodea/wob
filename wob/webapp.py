"""wob web dashboard — stdlib-only server + single-file frontend.

Run: wob app [--port 8765] [--open]
API (all JSON):
  GET /api/stats                     counts, avg discount, total saved
  GET /api/deals?top=100&min_off=0.7&quality=0&q=title-substr
  GET /api/search?isbn=...           cross-web compare (openlibrary, googlebooks,
                                     local; paid sources excluded unless paid=1)
  GET /api/search?term=...
  GET /api/coursepacks               all packs
  GET /api/coursepack/<id>           per-book basket vs local deals
  GET /api/recommend?like=a;b        taste recommendations
  GET /api/alerts  GET /api/history?top=25
"""

import json
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import alerts as alerts_mod
from . import deals as deals_mod
from . import isbnutil
from .coursepacks import get_coursepack, list_coursepacks, match_deals
from .curated import _norm_multi
from .recommend import recommend as recommend_books

STATIC_DIR = Path(__file__).parent / "webapp_static"
DEFAULT_PORT = 8765

_ISBN_RE = re.compile(r"(?:97[89][-\s]?)?\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,7}[-\s]?[\dXx]")


def parse_line(line):
    """One syllabus line -> (isbn13 | None, title-string)."""
    line = line.strip()
    if not line:
        return None, ""
    m = _ISBN_RE.search(line.replace("ISBN", ""))
    if m:
        isbn = isbnutil.to13(m.group(0))
        title = line.replace(m.group(0), "").strip(" ,;-\t")
        if isbn:
            return isbn, title
    return None, line


def _match_title(title, rows):
    """Loose title match: all significant normalized words present."""
    words = [w for w in _norm_multi(title).split() if len(w) >= 3][:6]
    if len(words) < 2:
        return []
    hits = []
    for r in rows:
        hay = _norm_multi(r.get("title", ""), r.get("author", ""))
        if all(w in hay for w in words):
            hits.append(r)
    hits.sort(key=lambda r: r["used_price"])
    return hits


def price_lines(lines, heal=False):
    rows = _deal_rows()
    out = []
    missing_titles = []
    for line in lines:
        isbn, title = parse_line(line)
        if not isbn and not title:
            continue
        if isbn:
            hits = [r for r in rows if r.get("isbn13") == isbn]
            if not hits:
                hits = _match_title(title, rows) if title else []
        else:
            hits = _match_title(title, rows)
        if hits:
            b = hits[0]
            out.append({
                "line": line, "found": True, "type": "isbn" if isbn else "title",
                "title": b["title"], "price": b["used_price"], "pct_off": b["pct_off"],
                "condition": b["condition"], "site": b["site"], "quality": b["quality"],
                "url": b["url"],
            })
        else:
            if heal and not isbn and len(missing_titles) < 12:
                missing_titles.append(title)
            out.append({"line": line, "found": False, "title": title or line, "price": None, "condition": "", "site": "", "url": ""})
    # heal pass: resolve missing titles to ISBNs via OpenLibrary (free, polite)
    known_isbns = {r["isbn13"] for r in rows if r.get("isbn13")}
    for t in missing_titles:
        try:
            from .providers import openlibrary
            hits = openlibrary.search(t, limit=1)
            isbn = None
            if hits and hits[0].get("meta", {}).get("isbn"):
                isbn = isbnutil.to13(hits[0]["meta"]["isbn"][0])
            if isbn and isbn in known_isbns:
                b = next(r for r in rows if r.get("isbn13") == isbn)
                for o in out:
                    if not o["found"] and (o["title"] or "").lower() in t.lower():
                        o.update(found=True, type="isbn-heal", title=b["title"],
                                 price=b["used_price"], pct_off=b["pct_off"],
                                 condition=b["condition"], site=b["site"],
                                 quality=b["quality"], url=b["url"])
                        break
        except Exception:
            continue
    found = sum(1 for o in out if o["found"])
    total = round(sum(o["price"] for o in out if o["found"]), 2)
    return {"rows": out, "found": found, "in": len(out), "total_price": total}


def _json(handler, obj, code=200):
    body = json.dumps(obj, default=str).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _qs(handler):
    return urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)


def _int(qs, key, default):
    try:
        return int(qs.get(key, [default])[0])
    except (ValueError, IndexError):
        return default


def _float(qs, key, default):
    try:
        return float(qs.get(key, [default])[0])
    except (ValueError, IndexError):
        return default


def _deal_rows():
    rows = deals_mod.load_deals()
    return [
        {
            "title": r.get("title", ""),
            "author": r.get("author", ""),
            "site": r.get("site", "wob"),
            "quality": bool(r.get("quality")),
            "used_price": r.get("used_price"),
            "new_price": r.get("new_price"),
            "pct_off": r.get("pct_off"),
            "condition": r.get("condition", ""),
            "isbn13": r.get("isbn13", ""),
            "url": r.get("url", ""),
        }
        for r in rows
    ]


def stats():
    rows = _deal_rows()
    q = sum(1 for r in rows if r["quality"])
    saved = sum(
        (r["new_price"] or 0) - (r["used_price"] or 0)
        for r in rows
    )
    avg = (sum(r["pct_off"] or 0 for r in rows) / len(rows) * 100) if rows else 0
    return {
        "deals": len(rows),
        "quality": q,
        "avg_pct": round(avg, 1),
        "saved": round(saved, 2),
    }


def api_deals(qs):
    rows = _deal_rows()
    min_off = _float(qs, "min_off", 0.0)
    quality = _int(qs, "quality", 0)
    q = (qs.get("q", [""])[0] or "").lower()
    top = _int(qs, "top", 100)
    if min_off > 0:
        rows = [r for r in rows if (r["pct_off"] or 0) >= min_off]
    if quality:
        rows = [r for r in rows if r["quality"]]
    if q:
        rows = [r for r in rows if q in r["title"].lower() or q in r["author"].lower()]
    return {"rows": rows[:top], "total": len(rows)}


def api_search(qs):
    from . import providers as providers_mod

    isbn = (qs.get("isbn", [""])[0] or "").strip()
    term = (qs.get("term", [""])[0] or "").strip()
    sites = [s.strip() for s in (qs.get("sites", ["googlebooks,openlibrary"])[0] or "googlebooks,openlibrary").split(",") if s.strip()]
    if bool(qs.get("paid", ["0"])[0] in ("1", "true")):
        sites += ["googleshopping", "amazon"]

    isbn13 = None
    if isbn:
        isbn13 = isbnutil.to13(isbn)
        if not isbn13:
            return {"error": f"not a recognizable ISBN: {isbn!r}"}, 400
    rows = []
    title_kw = None
    for name, mod in providers_mod.available().items():
        if name not in sites:
            continue
        try:
            if isbn13:
                if name in ("googleshopping", "amazon") and not title_kw:
                    continue
                got = mod.lookup(isbn13)
                got = got if isinstance(got, list) else [got] if got else []
            else:
                if not hasattr(mod, "search") or not term:
                    continue
                got = mod.search(term, limit=5)
            rows.extend([g for g in got if g] if got else [])
            if isbn13 and not title_kw and rows:
                for g in rows:
                    if g.get("title"):
                        title_kw = g["title"][:100]
                        break
        except Exception as e:
            rows.append({"site": name, "error": str(e)[:120], "price": None, "condition": "", "title": ""})
    if isbn13 and "googleshopping" in sites or "amazon" in sites:
        for name in ("googleshopping", "amazon"):
            if name not in sites or not title_kw:
                continue
            try:
                mod = providers_mod.load(name)
                got = mod.lookup(isbn13, keyword=title_kw)
                rows.extend(got or [])
            except Exception as e:
                rows.append({"site": name, "error": str(e)[:120], "price": None, "condition": "", "title": ""})
    for r in _deal_rows():
        if isbn13 and r.get("isbn13") == isbn13:
            rows.append({
                "site": f"local:{r['site']}", "title": r["title"],
                "condition": r["condition"], "price": r["used_price"],
                "currency": "USD", "url": r["url"], "source": "local-deal",
                "meta": {"pct_off": r["pct_off"]},
            })
    priced = sorted([r for r in rows if r.get("price") is not None], key=lambda r: r["price"])
    meta = [r for r in rows if r.get("price") is None]
    refs = [r["price"] for r in priced if r.get("source") == "retail"]
    ref = min(refs) if refs else None
    return {
        "isbn13": isbn13,
        "ref": ref,
        "rows": [{"site": r.get("site"), "title": r.get("title", ""), "price": r.get("price"),
                  "currency": r.get("currency", "USD"), "condition": r.get("condition", ""),
                  "url": r.get("url", ""), "source": r.get("source", ""),
                  "seller": (r.get("meta") or {}).get("seller", ""),
                  "pct_off": (r.get("meta") or {}).get("pct_off"),
                  "error": r.get("error", "")} for r in priced + meta],
    }, 200


def api_coursepack(cid):
    cid2, pack = get_coursepack(cid)
    if not pack:
        return {"error": f"unknown course {cid!r}"}, 404
    name, books = pack
    rows = deals_mod.load_deals()
    books_out = []
    for label, tokens in books:
        matches = match_deals(rows, tokens)
        if matches:
            b = matches[0]
            books_out.append({
                "book": label, "found": True,
                "price": b["used_price"], "pct_off": b["pct_off"],
                "condition": b.get("condition", ""), "site": b.get("site", "wob"),
                "quality": bool(b.get("quality")), "url": b.get("url", ""),
            })
        else:
            books_out.append({"book": label, "found": False})
    found = sum(1 for b in books_out if b["found"])
    total = round(sum(b["price"] for b in books_out if b["found"]), 2)
    return {"id": cid2, "name": name, "found": found, "total": total,
            "books": books_out}, 200


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/api/pricelist":
                n = int(self.headers.get("Content-Length", 0) or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                lines = body.get("lines") or []
                heal = bool(body.get("heal"))
                return _json(self, price_lines([str(l) for l in lines], heal=heal))
            _json(self, {"error": "not found"}, 404)
        except Exception as e:  # pragma: no cover
            _json(self, {"error": f"{type(e).__name__}: {e}"}, 500)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/" or ".." not in path and (STATIC_DIR / path.lstrip("/")).is_file():
                f = (STATIC_DIR / path.lstrip("/")) if path != "/" else (STATIC_DIR / "index.html")
                if not f.is_file():
                    f = STATIC_DIR / "index.html"
                body = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            qs = _qs(self)
            if path == "/api/stats":
                return _json(self, stats())
            if path == "/api/deals":
                return _json(self, api_deals(qs))
            if path == "/api/search":
                data, code = api_search(qs)
                return _json(self, data, code)
            if path == "/api/coursepacks":
                return _json(self, {"packs": [
                    {"id": c, "name": n, "books": len(b)} for c, (n, b) in list_coursepacks()]})
            if path.startswith("/api/coursepack/"):
                data, code = api_coursepack(path.rsplit("/", 1)[-1])
                return _json(self, data, code)
            if path == "/api/recommend":
                likes = [x for x in (qs.get("like", [""])[0] or "").split(";") if x.strip()]
                top = _int(qs, "top", 6)
                return _json(self, {"rows": recommend_books(likes, top=top)})
            if path == "/api/alerts":
                return _json(self, {"rows": alerts_mod.check()})
            if path.startswith("/api/action/scan"):
                isbn = (qs.get("isbn", [""])[0] or "").strip()
                if not isbn:
                    return _json(self, {"msg": "no isbn given"}, 400)
                threading.Thread(target=_run_scan, args=(isbn,), daemon=True).start()
                return _json(self, {"msg": f"scan started for {isbn} — results appear as the scan finishes"})
            if path == "/api/history":
                h = deals_mod.load_history()
                deltas = []
                for ident, snaps in h.items():
                    if len(snaps) < 2:
                        continue
                    a, b = snaps[-1], snaps[-2]
                    if a["used_price"] is None or b["used_price"] is None:
                        continue
                    deltas.append({
                        "ident": ident, "delta": round(a["used_price"] - b["used_price"], 2),
                        "prev": b["used_price"], "cur": a["used_price"],
                        "site": a.get("site", ""), "pct_off": a.get("pct_off"),
                    })
                drops = sorted([d for d in deltas if d["delta"] < 0], key=lambda d: d["delta"])
                return _json(self, {"rows": drops[:_int(qs, "top", 25)]})
            _json(self, {"error": "not found"}, 404)
        except Exception as e:  # pragma: no cover
            _json(self, {"error": f"{type(e).__name__}: {e}"}, 500)

    def log_message(self, *a):
        pass  # quiet server


def _run_scan(term):
    import argparse as _ap

    from .cli import cmd_scan

    try:
        cmd_scan(_ap.Namespace(
            term=term, keywords=None, sites="wob,tb", pages=1,
            max_hits=120, min_off=0.7, fresh=False,
        ))
    except Exception as e:  # pragma: no cover
        print(f"webapp scan error: {e}")


def run(port=DEFAULT_PORT, open_browser=False):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    print(f"wob dashboard → {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass