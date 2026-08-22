"""Google Books provider: new-copy retail/list price anchor + buy link."""

import json

from ..session import fetch, polite_wait

NAME = "googlebooks"
ENABLED = True
API = "https://www.googleapis.com/books/v1/volumes"


def gb_isbn_query(isbn13):
    return f"{API}?q=isbn:{isbn13}&country=US"


def parse_gb_volume(payload):
    vi = payload.get("volumeInfo", {}) or {}
    si = payload.get("saleInfo", {}) or {}
    ai = payload.get("accessInfo", {}) or {}

    def _amount(block):
        if not isinstance(block, dict):
            return None
        amount = block.get("amount")
        return float(amount) if isinstance(amount, (int, float)) else None

    thumbnail = ""
    links = vi.get("imageLinks") or {}
    if isinstance(links, dict):
        thumbnail = links.get("thumbnail") or ""

    buy_link = ""
    if isinstance(si.get("buyLink"), str):
        buy_link = si["buyLink"]
    elif isinstance(ai.get("webReaderLink"), str):
        buy_link = ai["webReaderLink"]

    return {
        "title": vi.get("title", ""),
        "subtitle": vi.get("subtitle", ""),
        "authors": vi.get("authors", []) or [],
        "published_date": vi.get("publishedDate", ""),
        "page_count": vi.get("pageCount", 0),
        "categories": vi.get("categories", []) or [],
        "thumbnail": thumbnail,
        "retail_price": _amount(si.get("retailPrice")),
        "retail_currency": (si.get("retailPrice") or {}).get("currencyCode", "USD"),
        "list_price": _amount(si.get("listPrice")),
        "buy_link": buy_link,
    }


def lookup(isbn13):
    r = fetch(gb_isbn_query(isbn13), headers={"Accept": "application/json"})
    data = json.loads(r.text or "{}")
    polite_wait()
    items = data.get("items") or []
    if not items:
        return None
    v = parse_gb_volume(items[0])
    price = v["retail_price"] if v["retail_price"] else v["list_price"]
    return {
        "site": NAME,
        "title": v["title"] + (": " + v["subtitle"] if v["subtitle"] else ""),
        "condition": "NEW",
        "price": price,
        "currency": v["retail_currency"],
        "url": v["buy_link"] or f"https://books.google.com/books?vid=ISBN{isbn13}",
        "source": "retail",
        "meta": v,
    }
