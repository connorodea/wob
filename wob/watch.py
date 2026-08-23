"""M6 opener: persistent watchlist with deterministic matching against
the scanned shelf. No network in the module itself — `check` reads local
deals/history only. Every entry is a validated Watchlist entity
(schema-versioned through entities.py)."""

from __future__ import annotations

import json

from .deals import DATA_DIR
from .entities import Watchlist
from .fairprice import deal_signal, fair_price_cents
from .isbnutil import to13

WATCH_FILE = DATA_DIR / "watchlist.jsonl"


def load_all() -> list[Watchlist]:
    if not WATCH_FILE.exists():
        return []
    out = []
    for line in WATCH_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = Watchlist.from_dict(json.loads(line))
            e.validate()
            out.append(e)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue  # tolerate a corrupt line; never crash the pipeline
    return out


def _save(entries):
    WATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCH_FILE.write_text("".join(json.dumps(e.to_dict()) + "\n" for e in entries))


def add(user_id, isbn, min_condition="GOOD", target_price_cents=None, budget_cents=None, name=""):
    i13 = to13(isbn)
    if not i13:
        raise ValueError(f"not a recognizable ISBN: {isbn!r}")
    entries = load_all()
    if any(e.edition_id == i13 and e.active for e in entries):
        return None  # already watched
    e = Watchlist(
        watch_id=f"w{len(entries) + 1:05d}",
        user_id=user_id,
        edition_id=i13,
        target_price_cents=target_price_cents,
        min_condition=min_condition,
        active=True,
    )
    e.validate()
    entries.append(e)
    _save(entries)
    return e


def remove(identity):
    i13 = to13(identity) if identity else None
    entries = load_all()
    kept = []
    removed = 0
    for e in entries:
        if (identity == e.watch_id) or (i13 and i13 == e.edition_id):
            removed += 1
            continue
        kept.append(e)
    _save(kept)
    return removed


def check(rows, watch_entries=None):
    """Match active watches against deal rows; report hits + policy state."""
    entries = watch_entries if watch_entries is not None else load_all()
    by_isbn = {}
    for r in rows:
        i13 = to13(r.get("isbn13") or r.get("barcode"))
        if i13:
            by_isbn.setdefault(i13, []).append(r)

    hits = []
    for e in entries:
        if not e.active:
            continue
        candidates = sorted(by_isbn.get(e.edition_id, []), key=lambda r: r["used_price"])
        chose = None
        for c in candidates:
            if c.get("condition", "UNKNOWN") == "UNKNOWN":
                continue
            if c["condition"] in {"NEW", "LIKE_NEW", "VERY_GOOD", "GOOD", "WELL_READ"}:
                chose = c
                break
        if not chose:
            hits.append(
                {
                    "watch_id": e.watch_id,
                    "isbn": e.edition_id,
                    "found": False,
                    "price": None,
                    "condition": None,
                    "reason": "no qualifying copy on the shelf",
                }
            )
            continue
        price_cents = int(round(float(chose["used_price"]) * 100))
        signal, why = deal_signal(
            price_cents,
            fair_price_cents(
                candidates,
                chose.get("condition"),
            ),
        )
        hits.append(
            {
                "watch_id": e.watch_id,
                "isbn": e.edition_id,
                "found": True,
                "price": chose["used_price"],
                "condition": chose["condition"],
                "url": chose.get("url", ""),
                "signal": signal,
                "reason": why,
                "within_budget": (
                    e.target_price_cents is None or price_cents <= e.target_price_cents
                ),
            }
        )
    return hits
