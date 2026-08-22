import json

from .session import BASE, fetch

ALGOLIA_APP = "AR33G9NJGJ"
ALGOLIA_KEY = "96c16938971ef89ae1d14e21494e2114"
ALGOLIA_INDEX = "shopify_products_us"
ALGOLIA_DSN = f"https://{ALGOLIA_APP}-dsn.algolia.net"


def algolia_query(query, page=0, hits_per_page=1000):
    r = fetch(
        f"{ALGOLIA_DSN}/1/indexes/{ALGOLIA_INDEX}/query",
        method="POST",
        data=json.dumps(
            {"query": query, "hitsPerPage": min(hits_per_page, 1000), "page": page}
        ),
        headers={
            "Content-Type": "application/json",
            "x-algolia-api-key": ALGOLIA_KEY,
            "x-algolia-application-id": ALGOLIA_APP,
        },
    )
    return json.loads(r.text)


def iter_search_results(query, max_pages, max_hits, on_progress=None):
    per_page = min(max_hits, 1000)
    page = 0
    yielded = 0
    while page < max_pages and yielded < max_hits:
        res = algolia_query(query, page=page, hits_per_page=per_page)
        hits = res.get("hits", [])
        for h in hits[: max_hits - yielded]:
            yield {
                "id": h.get("objectID") or h.get("isbn13") or "",
                "handle": h.get("productHandle") or "",
                "meta": {
                    "author": h.get("author") or "",
                    "shortTitle": h.get("shortTitle") or h.get("longTitle") or "",
                    "listPriceUs": h.get("listPriceUs"),
                    "rrp": h.get("rrp"),
                    "isbn13": h.get("isbn13") or "",
                    "isbn10": h.get("isbn10") or "",
                    "publisher": h.get("publisher") or "",
                    "yearPublished": h.get("yearPublished") or "",
                    "availableConditions": h.get("availableConditions") or [],
                    "inStock": h.get("inStock"),
                    "quantity": h.get("quantity"),
                    "bindingType": h.get("bindingType") or "",
                },
            }
        yielded += len(hits)
        if on_progress:
            on_progress(query, page, len(hits), res.get("nbHits"))
        if len(hits) < per_page:
            break
        page += 1