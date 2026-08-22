import json
import re
from urllib.parse import quote

from .curated import match_quality
from .isbnutil import to13
from .picker import pick_best
from .session import BASE as WOB_BASE, fetch, polite_wait

TB_BASE = "https://www.thriftbooks.com"

HIDDEN_RE = re.compile(r'tb-hiddenText">(.*?)</div>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
PRICE_RE = re.compile(r"\$([0-9]+(?:\.[0-9]{2})?)")
FORMAT_RE = re.compile(r"^(.+?)\s+\$[0-9.]+(?:\s*-\s*\$[0-9.]+)?$")


def _clean(text):
    t = TAG_RE.sub("", text)
    t = t.replace("<!--", "").replace("-->", "")
    return re.sub(r"\s+", " ", t).strip()


def search_results(query, max_pages, per_page=50):
    body = {
        "searchTerms": [query],
        "page": 1,
        "itemsPerPage": per_page,
        "sortBy": "mostPopular",
        "sortDirection": "desc",
        "isInStock": True,
        "isLargePrint": False,
        "blockDidYouMeanForward": False,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": f"{TB_BASE}/browse/?b.search={quote(query)}",
        "X-Requested-With": "XMLHttpRequest",
    }
    page = 1
    while page <= max_pages:
        body["page"] = page
        r = fetch(f"{TB_BASE}/api/browse/Search", method="POST", data=json.dumps(body), headers=headers)
        d = json.loads(r.text)
        works = d.get("works") or []
        for w in works:
            yield {
                "id": str(w.get("idWork") or ""),
                "url": f"{TB_BASE}/w/{w.get('workUrl') or ''}/{w.get('idWork')}/",
                "meta": {
                    "id": str(w.get("idWork") or ""),
                    "title": w.get("title") or "",
                    "authors": " ; ".join(
                        a.get("authorName", "") for a in (w.get("authors") or [])
                    ),
                    "lowPrice": w.get("lowPrice"),
                    "highPrice": w.get("highPrice"),
                    "listPrice": w.get("listPrice"),
                    "media": w.get("media") or "",
                    "availableCopies": w.get("availableCopies") or 0,
                    "buyNowPrice": w.get("buyNowPrice"),
                    "buyNowCondition": w.get("buyNowCondition") or "",
                    "isbn": w.get("iSBN") or "",
                },
            }
        if len(works) < per_page:
            break
        page += 1
        polite_wait()


TB_COND_MAP = {
    "New": "NEW",
    "Like New": "LIKE_NEW",
    "Very Good": "VERY_GOOD",
    "Good": "GOOD",
    "Acceptable": "ACCEPTABLE",
}


def _parse_page(html):
    rows = []
    seen = set()
    for m in HIDDEN_RE.finditer(html):
        t = _clean(m.group(1))
        if t and t not in seen:
            seen.add(t)
            rows.append(t)
    blocks = []
    current = None
    for t in rows:
        pm = PRICE_RE.search(t)
        if " - " in t and pm:
            name = t[: pm.start()].strip()
            if name not in ("Menu Button", "Search Button", "Scan a barcode"):
                current = {"format": name, "conditions": {}}
                blocks.append(current)
            continue
        if current is None:
            continue
        parts = t.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        cond, price_s = parts
        m2 = PRICE_RE.search(price_s)
        cond_key = TB_COND_MAP.get(cond)
        if m2 and cond_key:
            current["conditions"][cond_key] = float(m2.group(1))
        elif "Unavailable" in t and cond in TB_COND_MAP:
            current["conditions"][TB_COND_MAP[cond]] = None
    return blocks


def analyze(url, min_off, meta):
    html = fetch(url).text
    blocks = _parse_page(html)
    fallback_ref = meta.get("listPrice") or 0
    best_block = None
    best_pick = None
    for block in blocks:
        conds = block["conditions"]
        new_ref = conds.get("NEW")
        has_new = bool(new_ref)
        if not new_ref and fallback_ref > 0:
            new_ref = fallback_ref
        if not new_ref:
            continue
        candidates = []
        for cond, price in conds.items():
            if cond == "NEW" or price is None or price <= 0:
                continue
            pct_off = 1.0 - price / new_ref
            if pct_off >= min_off:
                candidates.append(
                    {
                        "condition": cond,
                        "used_price": round(price, 2),
                        "pct_off": round(pct_off, 4),
                    }
                )
        pick = pick_best(candidates)
        if pick and (best_pick is None or pick["pct_off"] > best_pick["pct_off"]):
            best_pick = pick
            best_block = {"format": block["format"], "new_ref": new_ref, "has_new": has_new}
    if not best_pick:
        return None
    slug = meta.get("url", url).split("/w/")[-1].strip("/")
    title = meta.get("title") or ""
    raw_isbn = meta.get("isbn", "") or ""
    isbn13 = to13(raw_isbn) or raw_isbn
    return {
        "site": "tb",
        "product_id": meta.get("id") or "",
        "title": title,
        "author": meta.get("authors", ""),
        "handle": slug,
        "variant_id": "",
        "condition": best_pick["condition"],
        "source": "",
        "country": "",
        "used_price": best_pick["used_price"],
        "new_price": round(best_block["new_ref"], 2),
        "ref_source": "store_new" if best_block["has_new"] else "list_price",
        "pct_off": best_pick["pct_off"],
        "barcode": isbn13,
        "sku": "",
        "stock": meta.get("availableCopies"),
        "isbn10": raw_isbn if raw_isbn and len(raw_isbn) == 10 else "",
        "upc": "",
        "isbn13": isbn13,
        "publisher": "",
        "list_price_us": meta.get("listPrice"),
        "rrp": None,
        "format": best_block["format"],
        "url": url,
        "quality": match_quality(title, slug + " " + meta.get("authors", "")),
    }