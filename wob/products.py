import json

from .curated import match_quality
from .picker import pick_best
from .session import BASE, fetch


def fetch_product(handle):
    r = fetch(f"{BASE}/products/{handle}.js")
    return json.loads(r.text)


def new_reference_price(product):
    prices = [v["price"] for v in product.get("variants", []) if v.get("option2") == "NEW" and v["price"] > 0]
    return min(prices) / 100.0 if prices else None


def list_ref_fallback(meta):
    """When a store stocks no NEW copy, anchor to the publisher list price."""
    for key in ("listPriceUs", "rrp", "listPrice"):
        v = (meta or {}).get(key)
        if v:
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            if f > 0:
                return f
    return None


def deal_candidates(product, min_off, ref):
    if ref is None:
        return None, []
    candidates = []
    for v in product.get("variants", []):
        price = v["price"]
        cond = v.get("option2") or ""
        if not v.get("available") or price <= 0 or cond == "NEW":
            continue
        used = price / 100.0
        pct_off = 1.0 - used / ref
        if pct_off >= min_off:
            candidates.append(
                {
                    "variant_id": v["id"],
                    "condition": cond,
                    "source": v.get("option3") or "",
                    "country": v.get("option1") or "",
                    "used_price": round(used, 2),
                    "pct_off": round(pct_off, 4),
                    "barcode": v.get("barcode") or "",
            }
        )
    return ref, candidates


def best_deal(product, min_off, meta=None):
    meta = meta or {}
    ref = new_reference_price(product)
    ref_source = "store_new"
    if ref is None:
        ref = list_ref_fallback(meta)
        ref_source = "list_price"
    if ref is None:
        return None
    _, candidates = deal_candidates(product, min_off, ref)
    if not candidates:
        return None
    best = pick_best(candidates)
    sku = ""
    for v in product.get("variants", []):
        if str(v.get("id")) == str(best["variant_id"]):
            sku = v.get("sku") or ""
            break
    return {
        "site": "wob",
        "product_id": str(product["id"]),
        "title": product.get("title") or meta.get("shortTitle") or "",
        "handle": product.get("handle") or "",
        "variant_id": best["variant_id"],
        "condition": best["condition"],
        "source": best["source"],
        "country": best["country"],
        "used_price": best["used_price"],
        "new_price": round(ref, 2),
        "ref_source": ref_source,
        "pct_off": best["pct_off"],
        "barcode": best["barcode"] or "",
        "sku": sku,
        "stock": meta.get("quantity"),
        "isbn10": meta.get("isbn10", "") or "",
        "upc": "",
        "author": meta.get("author", ""),
        "isbn13": meta.get("isbn13", ""),
        "publisher": meta.get("publisher", ""),
        "list_price_us": meta.get("listPriceUs"),
        "rrp": meta.get("rrp"),
        "url": f"{BASE}/products/{product['handle']}?variant={best['variant_id']}",
        "quality": match_quality(product.get("title", ""), product.get("handle", "")),
    }