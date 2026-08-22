"""OpenLibrary provider: metadata, covers, and edition ISBNs (no prices)."""

import json
from urllib.parse import urlencode

from ..session import fetch, polite_wait

NAME = "openlibrary"
ENABLED = True
BASE = "https://openlibrary.org"


def parse_ol_books(payload):
    books = []
    for book in payload.values():
        if not isinstance(book, dict):
            continue
        authors = [
            a["name"] for a in book.get("authors", [])
            if isinstance(a, dict) and a.get("name")
        ]
        publishers = [
            p["name"] for p in book.get("publishers", [])
            if isinstance(p, dict) and p.get("name")
        ]
        identifiers = book.get("identifiers") or {}
        isbn13 = identifiers.get("isbn_13") or []
        if isinstance(isbn13, str):
            isbn13 = [isbn13]
        cover = book.get("cover") or {}
        cover_url = cover.get("medium", "") if isinstance(cover, dict) else ""
        books.append({
            "title": book.get("title", ""),
            "subtitle": book.get("subtitle", ""),
            "authors": authors,
            "publishers": publishers,
            "publish_date": book.get("publish_date", ""),
            "isbn13": list(isbn13),
            "cover_url": cover_url,
        })
    return books


def parse_ol_search(payload):
    out = []
    for doc in (payload.get("docs") or []):
        if not isinstance(doc, dict):
            continue
        out.append({
            "olid": str(doc.get("key", "")).split("/")[-1] or "",
            "title": doc.get("title", ""),
            "author_names": doc.get("author_name", []) or [],
            "first_publish_year": doc.get("first_publish_year"),
            "isbn": doc.get("isbn", []) or [],
            "cover_i": doc.get("cover_i"),
        })
    return out


def lookup(isbn13):
    """Metadata for one ISBN. Returns a metadata quote dict (price None)."""
    r = fetch(
        f"{BASE}/api/books?bibkeys=ISBN:{isbn13}&jscmd=data&format=json",
        headers={"Accept": "application/json"},
    )
    books = parse_ol_books(json.loads(r.text or "{}"))
    polite_wait()
    if not books:
        return None
    b = books[0]
    return {
        "site": NAME,
        "title": (b["title"] + (": " + b["subtitle"] if b["subtitle"] else "")),
        "condition": "METADATA",
        "price": None,
        "currency": "USD",
        "url": f"{BASE}/isbn/{isbn13}",
        "source": "metadata",
        "meta": b,
    }


def search(term, limit=5):
    """Title/author search -> metadata hits."""
    r = fetch(
        f"{BASE}/search.json?{urlencode({'q': term, 'fields': 'key,title,author_name,first_publish_year,isbn,cover_i', 'limit': limit})}",
        headers={"Accept": "application/json"},
    )
    docs = parse_ol_search(json.loads(r.text or "{}"))
    polite_wait()
    return [
        {
            "site": NAME,
            "title": d["title"],
            "condition": "METADATA",
            "price": None,
            "currency": "USD",
            "url": f"{BASE}{'/works/' if not d['olid'] else '/works/'}{d['olid']}" if d["olid"] else BASE,
            "source": "metadata",
            "meta": d,
        }
        for d in docs
    ]
