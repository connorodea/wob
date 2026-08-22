"""Google Shopping provider via the DataForSEO Merchant API.

Google Shopping has no public search API. DataForSEO serves the same SERP
(paid per task_post; task_get is free within 30 days). Credentials are
reused from ~/.claude/skills/seo/.env, env vars, or the wob .env.

Bare-ISBN keyword searches match the WRONG product on Google Shopping
(relevance fuzz), so lookups must be anchored to a title keyword. `lookup`
requires `keyword` unless a cached result exists. Not in the default
--sites list: each uncached lookup costs a small per-task fee (~$0.002).
"""

import base64
import json
import os
import pathlib
import time

import requests

from ..deals import DATA_DIR
from ..session import polite_wait

NAME = "googleshopping"
API_POST = "https://api.dataforseo.com/v3/merchant/google/products/task_post"
API_GET = "https://api.dataforseo.com/v3/merchant/google/products/task_get"
CACHE_FILE = DATA_DIR / "provider_cache.json"
CACHE_TTL = 24 * 3600


def _load_creds():
    env = os.environ.copy()
    for p in (
        pathlib.Path.home() / ".claude" / "skills" / "seo" / ".env",
        pathlib.Path.home() / ".config" / "wob" / ".env",
    ):
        if p.is_file():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env.get("DATAFORSEO_LOGIN", ""), env.get("DATAFORSEO_PASSWORD", "")


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
    quotes = []
    for it in items:
        price = it.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            continue
        quotes.append({
            "site": NAME,
            "title": it.get("title", ""),
            "condition": "UNKNOWN",
            "price": float(price),
            "currency": it.get("currency") or "USD",
            "url": it.get("url") or it.get("shopping_url") or "",
            "source": "shopping",
            "meta": {
                "seller": it.get("seller") or "",
                "old_price": it.get("old_price"),
                "rating": (it.get("product_rating") or {}).get("value") if isinstance(it.get("product_rating"), dict) else None,
                "reviews_count": it.get("reviews_count"),
            },
        })
    return quotes


def lookup(isbn13, keyword=None):
    """Shopping quotes for an ISBN. keyword (title [+ author]) is required
    for uncached lookups; bare-ISBN shopping queries mis-match products."""
    if not ENABLED:
        return None
    cache_key = f"{isbn13}|{keyword or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    if not keyword:
        return None

    r = requests.post(
        API_POST,
        json=[{
            "keyword": keyword,
            "location_name": "United States",
            "language_name": "English",
            "depth": 60,
        }],
        headers=_auth(),
        timeout=90,
    )
    polite_wait(0.5, 1.0)
    task_id = None
    if r.status_code == 200:
        for t in r.json().get("tasks") or []:
            if t.get("status_code") in (20000, 20100) and t.get("id"):
                task_id = t["id"]
    if not task_id:
        return None

    items = []
    for _ in range(10):
        polite_wait(2.5, 3.5)
        rg = requests.get(f"{API_GET}/advanced/{task_id}", headers=_auth(), timeout=60)
        if rg.status_code != 200:
            continue
        for t in rg.json().get("tasks") or []:
            for res in t.get("result") or []:
                items = res.get("items") or []
                if items:
                    break
            if items:
                break
        if items:
            break
    if not items:
        return None
    quotes = _wrap_items(items)
    if quotes:
        _cache_put(cache_key, quotes)
    return quotes or None