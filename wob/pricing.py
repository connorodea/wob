"""Deterministic pricing math (Milestone 1).

Landed cost = listed price + shipping + known fees, always in integer
cents of a single currency. Discount is computed against a reference;
when the reference is missing or non-positive the result is None — a
missing reference is never treated as a deal.
"""

from __future__ import annotations


def landed_cost_usd_cents(
    price_cents: int, shipping_cents: int = 0, tax_cents: int = 0, fee_cents: int = 0
) -> int:
    """Total out-the-door cost in USD cents.

    Raises ValueError on any negative or non-integer input — silently
    summing garbage costs is how bad purchases happen.
    """
    parts = {
        "price": price_cents,
        "shipping": shipping_cents,
        "tax": tax_cents,
        "fee": fee_cents,
    }
    for name, v in parts.items():
        if not isinstance(v, int):
            raise ValueError(f"landed_cost: {name} must be int cents, got {type(v)}")
        if v < 0:
            raise ValueError(f"landed_cost: {name} must be >= 0, got {v}")
    return sum(parts.values())


def discount_pct(price_cents: int, reference_cents: int) -> float | None:
    """1 - price/reference, or None when the reference cannot anchor a deal.

    price > reference gives a negative discount (overpriced); that is
    returned as-is so callers can rank it, but it will never pass a
    positive threshold.
    """
    if not isinstance(price_cents, int) or not isinstance(reference_cents, int):
        raise ValueError("discount_pct: both args must be int cents")
    if price_cents < 0 or reference_cents <= 0:
        return None
    return round(1.0 - price_cents / reference_cents, 6)


def cheapest_landed(offers) -> dict | None:
    """Given offers with price_cents/shipping_cents/tax_cents/fee_cents,
    return the offer with the lowest landed cost (ties -> first in list)."""
    best = None
    for o in offers:
        try:
            landed = landed_cost_usd_cents(
                int(o["price_cents"]),
                int(o.get("shipping_cents", 0)),
                int(o.get("tax_cents", 0)),
                int(o.get("fee_cents", 0)),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or landed < best["_landed"]:
            candidate = dict(o)
            candidate["_landed"] = landed
            best = candidate
    return best
