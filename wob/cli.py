import argparse
import os
import sys

import requests

from . import alerts as alerts_mod
from . import cart, deals as deals_mod
from . import isbnutil
from . import providers
from . import theme as T
from .coursepacks import get_coursepack, list_coursepacks, match_deals
from .products import best_deal, fetch_product
from .recommend import recommend as recommend_books
from .schedule import add as schedule_add
from .schedule import list_jobs as schedule_list
from .schedule import remove as schedule_remove
from .schedule import run_now as schedule_now
from .search import iter_search_results
from .session import login, polite_wait
from .site_thriftbooks import analyze as tb_analyze
from .site_thriftbooks import search_results as tb_search
from .viz import cmd_viz


def cmd_login(args):
    try:
        ok = login()
    except (RuntimeError, requests.RequestException) as e:
        print(T.status("err", f"login failed: {e}"))
        sys.exit(1)
    if ok:
        print(T.status("ok", "logged in — session cookie saved"))
        sys.exit(0)
    print(T.status("err", "login failed (bad credentials?)"))
    sys.exit(1)


def _load_keywords(args):
    if getattr(args, "term", None):
        return [args.term]
    path = args.keywords
    if not os.path.exists(path) and path == "keywords.txt":
        bundled = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keywords.txt"
        )
        if os.path.exists(bundled):
            path = bundled
    return [
        line.strip()
        for line in open(path).read().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _acquire_scan_lock():
    lock = deals_mod.DATA_DIR / ".scan.lock"
    deals_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            old = int(lock.read_text().strip() or "0")
            if old <= 0:
                raise ValueError("empty lock")
            os.kill(old, 0)
            print("another scan is already running, skipping this run")
            return False
        except (ProcessLookupError, ValueError, PermissionError):
            lock.unlink(missing_ok=True)
            return _acquire_scan_lock()


def _release_scan_lock():
    (deals_mod.DATA_DIR / ".scan.lock").unlink(missing_ok=True)


def cmd_scan(args):
    if not _acquire_scan_lock():
        return
    try:
        _scan_locked(args)
    finally:
        _release_scan_lock()


def _scan_locked(args):
    keywords = _load_keywords(args)
    if not keywords:
        print("no keywords")
        return
    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    if args.fresh:
        seen = {
            (rec.get("isbn13") or rec["product_id"])
            if rec.get("site") in (None, "wob")
            else f"tb:{rec['product_id']}"
            for rec in deals_mod.load_deals()
        }
    else:
        seen = deals_mod.existing_ids() | deals_mod.load_scan_state()
    total_deals = 0
    for site in sites:
        if site == "wob":
            total_deals += _scan_wob(keywords, args, seen)
        elif site == "tb":
            total_deals += _scan_tb(keywords, args, seen)
        else:
            print(f"unknown site {site!r}, skipping")
        deals_mod.save_scan_state(seen)
    print()
    print(
        T.status(
            "ok",
            f"{total_deals} new deals · {str(len(seen)).rjust(0)} books tracked · data/ up to date",
        )
    )
    print(
        T.whisper(
            'next idea: wob alerts --notify  ·  wob coursepack <id>  ·  wob recommend --like "..."'
        )
    )


def _scan_wob(keywords, args, seen):
    total = 0
    n = len(keywords)
    for i, kw in enumerate(keywords, 1):
        print(
            f"{T.dim(f'[{i:>2}/{n}]')} {T.paint('wob', 'accent')} {T.bold(kw)}", end="", flush=True
        )
        products = list(iter_search_results(kw, args.pages, args.max_hits))
        print(T.dim(f"  → {len(products)} hits"), flush=True)
        batch = []
        for p in products:
            if not p["id"] or p["id"] in seen:
                continue
            conds = set(p["meta"].get("availableConditions") or [])
            if conds and conds == {"NEW"}:
                continue
            if p["meta"].get("inStock") is False:
                continue
            try:
                product = fetch_product(p["handle"])
                deal = best_deal(product, args.min_off, meta=p["meta"])
            except Exception:
                print(f"    {T.paint('skip', 'rose')} {T.dim(p['handle'][:44])}")
                continue
            seen.add(p["id"])
            if deal:
                batch.append(deal)
            polite_wait()
        if batch:
            wrote = deals_mod.append_deals(batch)
            total += wrote
            print(f"    {T.paint(f'+{wrote}', 'ok', 'bold')} {T.dim('new deals')}")
        else:
            print(f"    {T.paint('·', 'dim')} {T.dim('0 new')}")
    return total


def _scan_tb(keywords, args, seen):
    total = 0
    n = len(keywords)
    for i, kw in enumerate(keywords, 1):
        print(f"{T.dim(f'[{i:>2}/{n}]')} {T.paint('tb', 'warn')} {T.bold(kw)}", end="", flush=True)
        works = list(tb_search(kw, args.pages))
        print(T.dim(f"  → {len(works)} works"), flush=True)
        batch = []
        for w in works:
            key = f"tb:{w['id']}"
            if not w["id"] or key in seen:
                continue
            if not w["meta"].get("availableCopies"):
                continue
            try:
                deal = tb_analyze(w["url"], args.min_off, w["meta"])
            except Exception:
                print(f"    {T.paint('skip', 'rose')} {T.dim(str(w['id'])[:40])}")
                continue
            seen.add(key)
            if deal:
                batch.append(deal)
            polite_wait()
        if batch:
            wrote = deals_mod.append_deals(batch)
            total += wrote
            print(f"    {T.paint(f'+{wrote}', 'ok', 'bold')} {T.dim('new deals')}")
        else:
            print(f"    {T.paint('·', 'dim')} {T.dim('0 new')}")
    return total


def cmd_deals(args):
    rows = deals_mod.load_deals()
    if args.quality:
        rows = [r for r in rows if r.get("quality")]
    if args.top:
        rows = rows[: args.top]
    if args.min_off > 0:
        rows = [r for r in rows if r["pct_off"] >= args.min_off]
    print(
        T.frame(
            f"deals{(' quality' if args.quality else '')} {('top ' + str(args.top)) if args.top else ''}".strip(),
            T.dim(f"{len(rows)} books · sorted by discount"),
        )
    )
    print()
    for r in rows:
        author = f" — {r.get('author', '')[:22]}" if r.get("author") else ""
        title = r["title"][:44]
        anchor = (
            f"was ${r['new_price']:.2f}"
            if r["used_price"] < r["new_price"]
            else f"at ${r['new_price']:.2f}"
        )
        line = (
            f"{T.q_star(r.get('quality'))} {T.pct_colored(r['pct_off'])}  "
            f"{T.money(r['used_price'])}  {T.dim(anchor)}  "
            f"{T.cond_badge(r['condition'])}  {T.site_tag(r.get('site', 'wob'))}  {T.bold(title)}{T.dim(author)}"
        )
        print(" " + line)
    print()
    print(T.whisper(f"{len(rows)} deals · full archive: data/deals.csv"))


def cmd_cart(args):
    try:
        _cmd_cart(args)
    except (RuntimeError, requests.RequestException) as e:
        print(T.status("err", f"cart error: {e}"))
        sys.exit(1)


def _cmd_cart(args):
    if args.show:
        c = cart.cart_contents()
        print(T.frame("cart", T.dim("api session · worldofbooks.com")))
        print()
        for i in c.get("items", []):
            print(
                f"  {T.paint(str(i['quantity']) + 'x', 'accent')}  {i['title'][:52]}  {T.money(i['price'] / 100)}"
            )
        print()
        print(
            T.status(
                "star",
                f"{c.get('item_count', 0)} items · total {T.money(c.get('total_price', 0) / 100, positive=True)}",
            )
        )
        return
    if args.cookie:
        v = cart.cart_cookie()
        if not v:
            print(T.status("info", "no cart cookie in jar yet — run wob cart --add first"))
            return
        print(
            T.frame(
                "cookie transplant", "paste into DevTools on worldofbooks.com, then reload /cart"
            )
        )
        print()
        print(f"  {T.paint('document.cookie="cart={v}; path=/; domain=.worldofbooks.com"', 'hi')}")
        return
    if args.clear:
        n = cart.clear_session_cart()
        print(T.status("ok", f"session cart cleared ({n} items)"))
        return
    if args.add:
        rows = [r for r in deals_mod.load_deals() if r.get("site") == "wob"][: args.add]
        n = cart.add_variants_in_session(rows)
        print(T.status("ok", f"added {n} items to the api session cart"))
        return


def cmd_search(args):
    isbn13 = None
    if args.isbn or args.barcode:
        raw = args.isbn or args.barcode
        isbn13 = isbnutil.to13(raw)
        if not isbn13:
            print(f"not a recognizable ISBN/barcode: {raw!r}")
            sys.exit(1)
        print(f"searching ISBN {isbn13} ({isbnutil.mask(isbn13)}) across the web\n")

    site_names = [s.strip() for s in args.sites.split(",") if s.strip()]
    available = providers.available()
    chosen = []
    for s in site_names:
        if s in available:
            chosen.append(available[s])
        else:
            print(f"  provider {s!r} unavailable (disabled or unknown), skipping")
    if not chosen:
        print(
            "no providers available (ebay needs EBAY_APP_ID+EBAY_ACCESS_TOKEN in ~/.config/wob/.env)"
        )
        sys.exit(1)

    rows = []
    title_kw = None
    for mod in chosen:
        try:
            if isbn13:
                if mod.NAME == "googleshopping" and not title_kw:
                    continue  # needs a title anchor; second pass below
                got = mod.lookup(isbn13)
                if got is None:
                    continue
                got = got if isinstance(got, list) else [got]
            else:
                if not hasattr(mod, "search"):
                    continue
                got = mod.search(args.term, limit=args.limit)
            rows.extend(got)
            if isbn13 and title_kw is None:
                for g in got:
                    if g.get("title"):
                        title_kw = g["title"][:100]
                        break
        except Exception as e:
            print(f"  {mod.NAME}: error {e}")

    # second pass: title-anchored shopping lookup
    if isbn13 and title_kw:
        for mod in chosen:
            if mod.NAME == "googleshopping":
                try:
                    got = mod.lookup(isbn13, keyword=title_kw)
                    if got:
                        rows.extend(got)
                except Exception as e:
                    print(f"  googleshopping: error {e}")

    # local inventory matches (our scanned deals for this ISBN)
    if isbn13:
        for r in deals_mod.load_deals():
            if r.get("isbn13") == isbn13 or r.get("barcode") == isbn13:
                rows.append(
                    {
                        "site": f"local:{r.get('site', 'wob')}",
                        "title": r.get("title", ""),
                        "condition": r.get("condition", "UNKNOWN"),
                        "price": r.get("used_price"),
                        "currency": "USD",
                        "url": r.get("url", ""),
                        "source": "local-deal",
                        "meta": {"pct_off": r.get("pct_off")},
                    }
                )

    if not rows:
        print("no results from any provider")
        return

    # reference price: best retail/new anchor we can find
    refs = [r["price"] for r in rows if r.get("source") == "retail" and r.get("price")]
    ref = min(refs) if refs else None

    priced = [r for r in rows if r.get("price") is not None]
    metadata = [r for r in rows if r.get("price") is None]
    priced.sort(key=lambda r: r["price"])

    if args.json:
        import json as _json

        print(_json.dumps({"isbn13": isbn13, "ref": ref, "rows": rows}, indent=2, default=str))
        return

    def _pct(r, ref):
        if ref and r.get("price"):
            v = 1 - r["price"] / ref
        elif r.get("meta", {}).get("pct_off") is not None:
            v = r["meta"]["pct_off"]
        else:
            v = None
        return T.pct_colored(round(v, 4) if v is not None else None)

    title = f"search {isbnutil.mask(isbn13)}" if isbn13 else f"search “{args.term}”"
    print(
        T.frame(
            title,
            T.dim(
                f"{len(priced)} priced offers · {len(metadata)} metadata · {len(chosen)} sources"
            ),
        )
    )
    print()
    print(
        f"  {T.dim('provider'):>12}  {T.dim('cond'):<11} {T.dim('price'):>8} {T.dim('ref%'):>7}  {T.dim('link')}"
    )
    print("  " + T.rule())
    best = priced[0] if priced else None
    for i, r in enumerate(priced + metadata):
        price = T.money(r.get("price"))
        link = r.get("url", "")[:50]
        mark = T.paint("▲", "ok", "bold") if priced and r is best else " "
        provider = T.paint(f"{r['site']:<12}", "accent" if r is best else "hi")
        if r.get("meta", {}).get("seller"):
            link = f"{r['meta']['seller'][:18]} · {link[:26]}" if link else r["meta"]["seller"][:44]
        print(
            f"  {mark}{provider}  {T.cond_badge(r.get('condition', ''))}  {price}  {_pct(r, ref):>9}  {T.dim(link)}"
        )
    if ref:
        print()
        print(
            T.status(
                "star",
                f"reference (new) {T.money(ref)}  ·  best {T.paint('$%.2f' % best['price'], 'ok', 'bold')}  ({_pct(best, ref).strip()} off)"
                if best
                else f"reference (new) {T.money(ref)}",
            )
        )
    print()
    print(T.whisper("add googleshopping/amazon/ebay to --sites for more sources"))


def cmd_coursepack(args):
    if not args.course or args.course == "list":
        print(
            T.frame(
                "course packs",
                T.dim(f"{len(list_coursepacks())} catalogs · wob coursepack <id> [--scan] [--web]"),
            )
        )
        print()
        for cid, (name, books) in list_coursepacks():
            print(
                f"  {T.paint(cid, 'accent'):<24}{name}{T.dim(' · ' + str(len(books)) + ' books')}"
            )
        print()
        print(T.whisper("usage: wob coursepack <id>            e.g. wob coursepack stanford-cs229"))
        return

    cid, pack = get_coursepack(args.course)
    if not pack:
        print(f"unknown course {args.course!r} (run: wob coursepack list)")
        sys.exit(1)
    name, books = pack
    print(T.frame(f"{cid} · {name}", T.dim(f"{len(books)} books")))

    rows = deals_mod.load_deals()

    if args.scan:
        missing = []
        for label, tokens in books:
            if not match_deals(rows, tokens):
                missing.append((label, tokens))
        if not missing:
            print(T.status("ok", "shelf complete — nothing missing to scan"))
        else:
            print(T.section(f"scanning {len(missing)} missing titles"))
            for label, tokens in missing:
                term = label.split(" (")[0]
                scan_args = argparse.Namespace(
                    term=term,
                    keywords=None,
                    sites=getattr(args, "sites", "wob,tb"),
                    pages=1,
                    max_hits=150,
                    min_off=args.min_off,
                    fresh=False,
                )
                cmd_scan(scan_args)
            rows = deals_mod.load_deals()  # reload after scans
        print()

    found = 0
    total = 0.0
    site_totals = {}
    for label, tokens in books:
        matches = match_deals(rows, tokens)
        if not matches:
            if args.web:
                web = _web_lookup_missing(label)
                if web:
                    price = web["price"]
                    site = web["site"]
                    print(f"  {T.money(price)}  {T.site_tag('web:' + site):<8}  {label[:58]}")
                    total += price
                    site_totals[site] = site_totals.get(site, 0) + price
                    found += 1
                    continue
            print(
                f"  {T.dim('—'.rjust(9))}  {T.dim('[not found]'):<8}  {label[:58]}{T.dim('  · scan: wob scan --term "' + label.split(' (')[0] + '"')}"
            )
            continue
        best = matches[0]
        total += best["used_price"]
        site = best.get("site", "wob")
        site_totals[site] = site_totals.get(site, 0) + best["used_price"]
        found += 1
        print(
            f"  {T.money(best['used_price'])}  {T.site_tag(site):<8} {T.q_star(best.get('quality'))} {T.cond_badge(best['condition'])}  {T.bold(label[:48])}"
        )
    print()
    print(
        T.status(
            "star", f"basket {found}/{len(books)} found · total {T.money(total, positive=True)}"
        )
    )
    if len(site_totals) > 1:
        best_site = min(site_totals, key=site_totals.get)
        print(
            T.status(
                "info",
                f"ship from {T.paint(best_site, 'accent')} — one parcel, less shipping: {', '.join(f'{s} {T.money(t)}' for s, t in sorted(site_totals.items(), key=lambda x: -x[1]))}",
            )
        )
    if found < len(books):
        print(T.whisper("missing books: run with --scan and --web, or scan titles above"))


def _web_lookup_missing(label):
    title = label.split(" (")[0]
    try:
        from wob.providers import openlibrary, googleshopping

        ol = openlibrary.search(title, limit=1)
        isbn = None
        if ol and ol[0].get("meta", {}).get("isbn"):
            isbn = ol[0]["meta"]["isbn"][0]
        elif ol and ol[0].get("meta"):
            pass
        if not isbn:
            return None
        from . import isbnutil

        isbn = isbnutil.to13(isbn)
        if not isbn:
            return None
        q = googleshopping.lookup(isbn, keyword=title)
        if q:
            q = [x for x in q if x.get("price")]
            if q:
                q.sort(key=lambda x: x["price"])
                return {"site": q[0]["site"], "price": q[0]["price"]}
    except Exception:
        return None
    return None


def cmd_recommend(args):
    texts = [t.strip() for t in args.like if t.strip()]
    if not texts:
        print(
            T.frame(
                "recommend", 'usage: wob recommend --like "<book you loved>" [--like ...] [--top N]'
            )
        )
        print(T.whisper('example: wob recommend --like "Pattern Recognition and Machine Learning"'))
        sys.exit(1)
    seed = ", ".join(texts[:3])
    print(T.frame("recommend", f"you like  {T.paint(seed, 'hi')}"))
    print()
    recs = recommend_books(texts, top=args.top)
    if not recs:
        print(T.status("info", "no matching seed in the curated shelf (192 titles)"))
        return
    for r in recs:
        bar = T.score_bar(r["sim"])
        sim_txt = f"{r['sim']:.3f}"
        line = f"{bar}  {T.paint(sim_txt, 'gold')}"
        if r["price"] is not None:
            line += f"  {T.money(r['price'])}  {T.cond_badge(r['cond'])}  {T.site_tag(r.get('site', ''))}  {T.bold(r['title'][:44])}"
        else:
            line += f"  {T.paint('—', 'dim'):>9}  {T.dim('[not scanned]'):<12}  {r['label'][:46]}"
        print("  " + line)
    print()
    print(T.whisper("closer bar = closer to your taste · priced rows are buyable today"))


def cmd_alerts(args):
    all_a = alerts_mod.check()
    if not all_a:
        print(T.frame("alerts", T.dim("nothing today — a quiet market is a patient market")))
        return
    drops = [a for a in all_a if a["kind"] == "drop"]
    screams = [a for a in all_a if a["kind"] == "scream"]
    print(T.frame("alerts", T.dim(f"{len(drops)} price drops · {len(screams)} screaming deals")))
    print()
    for a in all_a:
        if a["kind"] == "drop":
            drop_amt = f"-${a['prev'] - a['price']:.2f}"
            trail = f"${a['prev']:.2f} → ${a['price']:.2f}"
            print(
                f"  {T.paint('▼', 'ok', 'bold')} {T.paint(drop_amt, 'ok')}  {a['title'][:44]}{T.dim('  ' + trail)}  {T.site_tag(a['site'])}"
            )
        else:
            print(
                f"  {T.paint('✦', 'gold', 'bold')} {T.money(a['price'])}  {a['title'][:44]}  "
                f"{T.pct_colored(a['pct_off'])}  {T.site_tag(a.get('site', ''))}  {T.dim(a.get('url', '')[:30])}"
            )
    if args.notify:
        fresh = alerts_mod.new_since_last(all_a)
        alerts_mod.notify(fresh)
    print()
    print(
        T.whisper(f"{len(all_a)} alert(s) · re-run with --notify for a desktop ping on what is new")
    )


def cmd_history(args):
    h = deals_mod.load_history()
    deltas = []
    for ident, snaps in h.items():
        if len(snaps) < 2:
            continue
        a, b = snaps[-1], snaps[-2]
        if a["used_price"] is None or b["used_price"] is None:
            continue
        deltas.append(
            {
                "ident": ident,
                "delta": a["used_price"] - b["used_price"],
                "prev": b["used_price"],
                "cur": a["used_price"],
                "site": a.get("site", ""),
                "pct_off": a.get("pct_off"),
            }
        )
    drops = [d for d in deltas if d["delta"] < 0]
    drops.sort(key=lambda d: d["delta"])
    print(
        T.frame("price history", T.dim(f"{len(deltas)} books tracked · {len(drops)} price drops"))
    )
    print()
    for d in drops[: args.top]:
        off = T.pct_colored(d["pct_off"]) if d["pct_off"] is not None else T.paint("   —  ", "dim")
        drop_amt = f"-${abs(d['delta']):.2f}"
        trail = f"${d['prev']:.2f} →"
        print(
            f"  {T.paint('▼', 'ok', 'bold')} {T.paint(drop_amt, 'ok'):>8}  "
            f"{d['ident'][:42]:<42} {T.dim(trail)} {T.money(d['cur'])}  {off}  {T.site_tag(d['site'])}"
        )
    print()
    print(
        T.whisper("data/history.jsonl holds every snapshot · drops appear as re-scans accumulate")
    )


def cmd_track(args):
    """Re-price already-tracked wob deals and snapshot history (drop detection)."""
    rows = [r for r in deals_mod.load_deals() if r.get("site") == "wob" and r.get("handle")][
        : args.top
    ]
    if not rows:
        print(T.status("info", "no tracked wob deals to re-price"))
        return
    print(T.frame("track", T.dim(f"re-pricing {len(rows)} tracked books ({args.top} cap)")))
    print()
    snapped = 0
    failed = 0
    for i, r in enumerate(rows, 1):
        try:
            product = fetch_product(r["handle"])
            deal = best_deal(product, 0.0, meta={})
        except Exception:
            failed += 1
            print(f"  {T.dim(f'[{i:>2}]')} {T.paint('✗', 'rose')} {T.dim(r['title'][:52])}")
            polite_wait()
            continue
        if deal:
            deal["isbn13"] = r.get("isbn13", "")
            deal["barcode"] = r.get("barcode", "")
            deals_mod.snapshot_history([deal])
            snapped += 1
            arrow = (
                "▼"
                if deal["used_price"] < r["used_price"]
                else "▲"
                if deal["used_price"] > r["used_price"]
                else "·"
            )
            tone = "ok" if deal["used_price"] <= r["used_price"] else "rose"
            print(
                f"  {T.dim(f'[{i:>2}]')} {T.paint(arrow, tone)} {T.money(deal['used_price'])}"
                f"  {T.cond_badge(deal['condition'])}  {T.dim(r['title'][:40])}"
            )
        polite_wait()
    print()
    print(
        T.status(
            "ok" if failed == 0 else "info",
            f"{snapped} re-priced · {failed} fetch failures · history updated",
        )
    )
    print(T.whisper("run: wob history   →   see price drops since the previous snapshot"))


def cmd_app(args):
    from .webapp import run

    run(port=args.port, open_browser=args.open)


def cmd_wos(args):
    from .profile import build_profile
    from .scoring import compute_deal_scores

    profile = None
    if args.interests or args.authors:
        profile = build_profile(
            "cli",
            [i.strip() for i in args.interests.split(",") if i.strip()],
            favored_authors=[a.strip() for a in args.authors.split(",") if a.strip()],
            min_condition=args.min_condition,
            budget_cents=int(args.budget * 100) if args.budget else None,
        )
    rows = deals_mod.load_deals()
    scored = compute_deal_scores(
        rows, budget_cents=profile.budget_cents if profile else None, profile=profile
    )
    print(
        T.frame(
            "wos — the shelf ranked by opportunity",
            T.dim(
                f"{len(scored)} candidates"
                + (" · your interests" if profile else " · curated-shelf relevance")
                + (f" · budget ${args.budget or '-'}" if args.budget else "")
            ),
        )
    )
    print()
    for r, s in scored[: args.top]:
        print(
            f"  {T.paint(f'{s.score:.3f}', 'ok', 'bold')}  {T.money(r['used_price'])}  "
            f"{T.cond_badge(r['condition'])}  {T.site_tag(r.get('site', 'wob'))}  {r['title'][:46]}"
        )
        print(T.dim(f"        {s.explanation[:150]}"))
    print()
    print(T.whisper("wos = relevance · discount · condition · scarcity · match · budget"))


def cmd_watch(args):
    from . import watch as W

    if args.sub == "add":
        try:
            e = W.add(
                "cli",
                args.isbn,
                min_condition=args.min_condition,
                target_price_cents=int(args.target * 100) if args.target else None,
            )
        except ValueError as err:
            print(T.status("err", str(err)))
            sys.exit(1)
        if e is None:
            print(T.status("info", "already on the watchlist"))
        else:
            print(
                T.status(
                    "ok",
                    f"watching {e.edition_id} "
                    f"({'any price' if e.target_price_cents is None else f'<= ${e.target_price_cents / 100:.2f}'}, "
                    f"min {e.min_condition})",
                )
            )
        return
    if args.sub == "list":
        entries = W.load_all()
        if not entries:
            print(T.frame("watchlist", T.dim("nothing watched yet — wob watch add --isbn ...")))
            return
        print(T.frame("watchlist", T.dim(f"{len(entries)} book(s)")))
        for e in entries:
            target = f"<= ${e.target_price_cents / 100:.2f}" if e.target_price_cents else "any"
            print(
                f"  {T.paint(e.watch_id, 'accent')}  {e.edition_id}  {T.dim(target + ', min ' + e.min_condition)}"
            )
        return
    if args.sub == "remove":
        n = W.remove(args.identity)
        print(T.status("ok" if n else "info", f"removed {n} watch(es)"))
        return
    if args.sub == "check":
        rows = deals_mod.load_deals()
        hits = W.check(rows)
        found = [h for h in hits if h["found"]]
        print(T.frame("watch check", T.dim(f"{len(hits)} watched · {len(found)} qualified")))
        print()
        for h in found:
            mark = T.paint("✓", "ok") if h["within_budget"] else T.paint("✗", "rose")
            print(
                f"  {mark}  {T.money(h['price'])}  {h['condition']:<10}  {h['isbn']}  "
                f"{T.dim(h['reason'][:60])}"
            )
        for h in hits:
            if not h["found"]:
                print(f"  {T.paint('·', 'dim')}  {h['isbn']}  {T.dim('not found locally')}")
        if args.notify:
            from . import alerts as alerts_mod

            fresh = alerts_mod.new_since_last(
                [
                    {
                        "kind": "watch",
                        "title": h["isbn"],
                        "price": h["price"],
                        "prev": None,
                        "pct_off": None,
                        "site": "wob",
                        "url": h.get("url", ""),
                    }
                    for h in found
                    if h["within_budget"]
                ]
            )
            alerts_mod.notify(fresh)
        return


def cmd_js_plan(args):
    rows = [r for r in deals_mod.load_deals() if r.get("site") == "wob" and r.get("variant_id")][
        : args.top
    ]
    for r in rows:
        body = f"id={r['variant_id']}&quantity=1"
        js = (
            f"fetch('/cart/add.js',{{method:'POST',"
            f"headers:{{'Content-Type':'application/x-www-form-urlencoded'}},"
            f"body:{body!r}}}).then(x=>x.json()).then(j=>"
            f"console.log('ADDED',j.title,j.quantity))"
        )
        print(f"# {r['pct_off'] * 100:.0f}% off — {r['title'][:60]}")
        print(js)
        print()
    print(f"# {len(rows)} items (open url: {cart.BASE}/cart)")


def main():
    ap = argparse.ArgumentParser(prog="wob")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("login", help="log the api session into your WoB account")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("scan", help="scan keywords for 70%+ off deals")
    p.add_argument("--keywords", default="keywords.txt")
    p.add_argument("--term", default="", help="single search term (overrides --keywords)")
    p.add_argument("--sites", default="wob,tb", help="comma list: wob, tb")
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--max-hits", type=int, default=400, help="products per keyword (wob only)")
    p.add_argument("--min-off", type=float, default=0.70)
    p.add_argument(
        "--fresh",
        action="store_true",
        help="re-queue state-only items; existing deals stay skipped",
    )
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("deals", help="print found deals sorted by discount")
    p.add_argument("--top", type=int, default=0)
    p.add_argument("--min-off", type=float, default=0.7)
    p.add_argument("--quality", action="store_true", help="only curated/great learning titles")
    p.set_defaults(func=cmd_deals)

    p = sub.add_parser("cart", help="api-session cart operations")
    p.add_argument("--show", action="store_true")
    p.add_argument("--cookie", action="store_true", help="print cart cookie transplant snippet")
    p.add_argument("--clear", action="store_true")
    p.add_argument("--add", type=int, default=0, metavar="N")
    p.set_defaults(func=cmd_cart)

    p = sub.add_parser("search", help="cross-web price compare by ISBN/barcode/term")
    p.add_argument("--isbn", default="", help="ISBN-10/13 or EAN")
    p.add_argument("--barcode", default="", help="barcode (same normalization as --isbn)")
    p.add_argument("--term", default="", help="title/author search (ignored with --isbn)")
    p.add_argument("--sites", default="googlebooks,openlibrary", help="comma list of providers")
    p.add_argument("--limit", type=int, default=5, help="hits per provider (search mode)")
    p.add_argument("--json", action="store_true", help="raw JSON output")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("coursepack", help="semester reading list -> cheapest basket")
    p.add_argument("course", nargs="?", default="list")
    p.add_argument(
        "--web",
        action="store_true",
        help="price missing books across the web (paid sources may be used)",
    )
    p.add_argument(
        "--scan",
        action="store_true",
        help="scan missing titles first (wob,tb), then price the basket",
    )
    p.add_argument("--sites", default="wob,tb", help="sites for --scan")
    p.add_argument("--min-off", type=float, default=0.70)
    p.set_defaults(func=cmd_coursepack)

    p = sub.add_parser("recommend", help="books adjacent to what you like, ranked with prices")
    p.add_argument(
        "--like", action="append", default=[], help="a book you loved (repeatable, free text)"
    )
    p.add_argument("--top", type=int, default=5)
    p.set_defaults(func=cmd_recommend)

    p = sub.add_parser("alerts", help="price drops + screaming Q-tier deals")
    p.add_argument(
        "--notify", action="store_true", help="macOS notification for NEW findings since last run"
    )
    p.set_defaults(func=cmd_alerts)

    p = sub.add_parser("history", help="tracked price changes (drops first)")
    p.add_argument("--top", type=int, default=10)
    p.set_defaults(func=cmd_history)

    p = sub.add_parser(
        "track", help="re-price tracked books + snapshot history (feeds wob history/alerts)"
    )
    p.add_argument("--top", type=int, default=30, help="how many wob deals to re-price")
    p.set_defaults(func=cmd_track)

    p = sub.add_parser("app", help="open the web dashboard (data refreshed live)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--open", action="store_true", help="open the browser automatically")
    p.set_defaults(func=cmd_app)

    p = sub.add_parser("wos", help="rank the shelf by Wob Opportunity Score")
    p.add_argument("--top", type=int, default=10)
    p.add_argument(
        "--interests", default="", help="comma list, e.g. 'reinforcement learning, bayesian'"
    )
    p.add_argument("--authors", default="", help="comma list of favored authors")
    p.add_argument("--budget", type=float, default=0, help="max landed cost in dollars (0 = none)")
    p.add_argument("--min-condition", default="GOOD")
    p.set_defaults(func=cmd_wos)

    p = sub.add_parser("watch", help="watchlist: alert when a book meets your terms")
    pw = p.add_subparsers(dest="sub", required=True)
    pa = pw.add_parser("add", help="watch an ISBN")
    pa.add_argument("--isbn", required=True)
    pa.add_argument("--min-condition", default="GOOD")
    pa.add_argument("--target", type=float, default=0, help="top price in dollars (0 = any)")
    pw.add_parser("list")
    pr = pw.add_parser("remove")
    pr.add_argument("identity", help="watch id or ISBN")
    pc = pw.add_parser("check", help="match against the scanned shelf")
    pc.add_argument(
        "--notify",
        action="store_true",
        help="desktop ping for NEW qualifying hits since last check",
    )
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser(
        "js-plan", help="print in-browser add-to-cart JS snippets for the top N deals"
    )
    p.add_argument("--top", type=int, default=12)
    p.set_defaults(func=cmd_js_plan)

    p = sub.add_parser("viz", help="charts + IPython shell over the deals data")
    p.add_argument("--png", action="store_true", help="write charts only, no shell")
    p.add_argument("--top", type=int, default=15)
    p.set_defaults(func=cmd_viz)

    p = sub.add_parser("schedule", help="manage recurring keyword scans")
    sp = p.add_subparsers(dest="sched_cmd", required=True)
    pa = sp.add_parser("add", help="schedule a recurring scan")
    pa.add_argument("name")
    pa.add_argument("--keywords", required=True)
    pa.add_argument("--every", type=float, required=True, help="interval in hours")
    pa.add_argument("--sites", default="wob,tb")
    pa.add_argument("--min-off", type=float, default=0.70)
    pa.add_argument("--max-hits", type=int, default=400)
    pa.add_argument("--pages", type=int, default=1)
    pa.set_defaults(func=cmd_schedule_add)
    pl = sp.add_parser("list", help="list installed schedules")
    pl.set_defaults(func=cmd_schedule_list)
    pr = sp.add_parser("remove", help="remove a schedule")
    pr.add_argument("name")
    pr.set_defaults(func=cmd_schedule_remove)
    pn = sp.add_parser("now", help="run a scheduled job immediately")
    pn.add_argument("name")
    pn.set_defaults(func=cmd_schedule_now)

    args = ap.parse_args()
    args.func(args)


def cmd_schedule_add(args):
    schedule_add(
        args.name,
        args.keywords,
        args.every,
        args.sites,
        args.min_off,
        args.max_hits,
        args.pages,
    )


def cmd_schedule_list(args):
    schedule_list()


def cmd_schedule_remove(args):
    schedule_remove(args.name)


def cmd_schedule_now(args):
    schedule_now(args.name)


if __name__ == "__main__":
    main()
