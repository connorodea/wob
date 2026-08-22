"""Amazon Marketplace provider via the DataForSEO Merchant API (live).

Same credential/caching pattern as googleshopping, but the Amazon Merchant
endpoint is a live round-trip (no task_post/poll). Each lookup costs a
small per-task fee (~$0.002); cached 24h per ISBN+keyword in
data/provider_cache.json. Not in the default --sites list.
"""

import base64
import json
import time

import requests

from ..deals import DATA_DIR
from ..session import polite_wait

NAME = "amazon"
API_LIVE = "https://api.dataforseo.com/v3/merchant/amazon/products/live/advanced"
CACHE_FILE = DATA_DIR / "provider_cache.json"
CACHE_TTL = 24 * 3600


def _load_creds():
    from ..config import load_config

    cfg = load_config()
    return cfg.dataforseo_login, cfg.dataforseo_password


_LOGIN, _PASSWORD = _load_creds()
ENABLED = bool(_LOGIN and _PASSWORD)


def _auth():
    raw = f"{_LOGIN}:{_PASSWORD}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode()}


def _cache_get(cache_key):
    if not CACHE_FILE.exists():
        return None
    try:
        cache = json.loads(CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    hit = cache.get(cache_key)
    if not hit or time.time() - hit.get("ts", 0) > CACHE_TTL:
        return None
    return hit.get("quotes")


def _cache_put(cache_key, quotes):
    cache = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            cache = {}
    cache[cache_key] = {"ts": time.time(), "quotes": quotes}
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache))


def _wrap_items(items):
    """Items follow docs' amazon_serp shape: price_from/price_to (float),
    data_asin, rating{value, votes_count, rating_max}, is_amazon_choice."""
    quotes = []
    for it in items:
        price = it.get("price_from")
        if price is None or (isinstance(price, (int, float)) and price <= 0):
            price = it.get("price_to")
        if not isinstance(price, (int, float)) or price <= 0:
            continue
        rating = it.get("rating") or {}
        quotes.append({
            "site": NAME,
            "title": it.get("title", ""),
            "condition": "UNKNOWN",
            "price": float(price),
            "currency": it.get("currency") or "USD",
            "url": it.get("url") or "",
            "source": "marketplace",
            "meta": {
                "seller": it.get("domain") or "amazon.com",
                "old_price": None,
                "asin": it.get("data_asin") or "",
                "rating": rating.get("value") if isinstance(rating, dict) else None,
                "votes": rating.get("votes_count") if isinstance(rating, dict) else None,
                "amazon_choice": bool(it.get("is_amazon_choice")),
            },
        })
    return quotes


def lookup(isbn13, keyword=None):
    """Amazon listings by product name (required; ISBN alone finds nothing)."""
    if not ENABLED or not keyword:
        return None
    kw = keyword.strip()
    cache_key = f"amazon|{isbn13}|{kw}"
    cached = _cache_get(cache_key)
    if cached is not None:
        polite_wait(0.1, 0.25)
        return cached

    r = requests.post(
        API_LIVE,
        json=[{
            "keyword": kw,
            "location_name": "United States",
            "language_code": "en",
            "depth": 60,
        }],
        headers=_auth(),
        timeout=90,
    )
    polite_wait(0.5, 1.0)
    if r.status_code == 200:
        items = []
        for t in r.json().get("tasks") or []:
            for res in t.get("result") or []:
                items = res.get("items") or []
                if items:
                    break
            if items:
                break
        if items:
            quotes = _wrap_items(items)
            if quotes:
                _cache_put(cache_key, quotes)
                return quotes
    return None