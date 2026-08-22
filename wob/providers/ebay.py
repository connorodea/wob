"""eBay Browse API provider. Disabled until EBAY_APP_ID / EBAY_ACCESS_TOKEN
exist in ~/.config/wob/.env."""

import json
import os

from ..session import load_env, polite_wait
from .conditions import ebay_condition_map

NAME = "ebay"
API = "https://api.ebay.com/buy/browse/v1/item_summary/search"

_env = load_env()
_APP_ID = _env.get("EBAY_APP_ID") or os.environ.get("EBAY_APP_ID")
_TOKEN = _env.get("EBAY_ACCESS_TOKEN") or os.environ.get("EBAY_ACCESS_TOKEN")
ENABLED = bool(_APP_ID and _TOKEN)


def ebay_find_query(isbn13, limit=10):
    return {
        "q": isbn13,
        "limit": min(limit, 200),
        "filter": "conditions:{NEW|LIKE_NEW|VERY_GOOD|GOOD|ACCEPTABLE}",
        "sort": "price",
    }


def parse_ebay_search(payload):
    if not isinstance(payload, dict):
        return []
    items = payload.get("itemSummaries") or []
    if not isinstance(items, list):
        return []
    cond_map = ebay_condition_map()
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        price_obj = item.get("price")
        price = None
        currency = "USD"
        if isinstance(price_obj, dict):
            try:
                price = float(price_obj.get("value"))
            except (TypeError, ValueError):
                price = None
            currency = price_obj.get("currency", "USD")
        ship = None
        for so in (item.get("shippingOptions") or []):
            if isinstance(so, dict) and so.get("shippingCostType") in ("FREE", None):
                pass
            if isinstance(so, dict) and isinstance(so.get("shippingCost"), dict):
                try:
                    ship = float(so["shippingCost"].get("value"))
                except (TypeError, ValueError):
                    ship = None
                if ship == 0:
                    ship = None
                break
        out.append({
            "item_id": item.get("itemId", ""),
            "title": item.get("title", ""),
            "price": price,
            "currency": currency,
            "condition": cond_map(item.get("condition")),
            "item_url": item.get("itemWebUrl", ""),
            "shipping_cost": ship,
        })
    return out


def lookup(isbn13, limit=10):
    if not ENABLED:
        return None
    import requests as _requests

    r = _requests.post(
        API,
        json=ebay_find_query(isbn13, limit),
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ebay lookup HTTP {r.status_code}")
    polite_wait()
    results = []
    for it in parse_ebay_search(r.json()):
        if it["price"] is None:
            continue
        results.append({
            "site": NAME,
            "title": it["title"],
            "condition": it["condition"],
            "price": it["price"],
            "currency": it["currency"],
            "url": it["item_url"],
            "source": "marketplace",
            "meta": {"item_id": it["item_id"], "shipping_cost": it["shipping_cost"]},
        })
    return results if results else None


def search(term, limit=10):
    if not ENABLED:
        return []
    import requests as _requests

    r = _requests.post(
        API,
        json={"q": term, "limit": min(limit, 200), "sort": "price"},
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ebay search HTTP {r.status_code}")
    polite_wait()
    return [
        {
            "site": NAME,
            "title": it["title"],
            "condition": it["condition"],
            "price": it["price"],
            "currency": it["currency"],
            "url": it["item_url"],
            "source": "marketplace",
            "meta": {"item_id": it["item_id"], "shipping_cost": it["shipping_cost"]},
        }
        for it in parse_ebay_search(r.json())
        if it["price"] is not None
    ]
