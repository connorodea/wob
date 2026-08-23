"""Fair-price estimation from our own offer history (M3).

Deterministic quantiles over historical offers per (identity, condition).
When too few observations exist the estimator abstains (returns
confident=False) instead of inventing a number. This replaces the naive
'store NEW price' reference with an actual secondary-market signal.

No ML: this is a histogram with honesty.
"""

from __future__ import annotations

MIN_N = 3

CONDITION_ORDER = [
    "ACCEPTABLE",
    "WELL_READ",
    "GOOD",
    "VERY_GOOD",
    "LIKE_NEW",
    "NEW",
]


def _quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def fair_price_cents(offers, condition, min_n=MIN_N):
    """offers: iterable of dicts with 'condition' + 'price_cents'.

    Returns {median, p25, p75, n, confident, condition} — confident is
    False when fewer than min_n offers exist for that condition.
    """
    prices = sorted(
        o["price_cents"]
        for o in offers
        if o.get("condition") == condition and isinstance(o.get("price_cents"), int)
    )
    n = len(prices)
    if n < min_n:
        return {
            "median": None,
            "p25": None,
            "p75": None,
            "n": n,
            "confident": False,
            "condition": condition,
        }
    return {
        "median": round(_quantile(prices, 0.5)),
        "p25": round(_quantile(prices, 0.25)),
        "p75": round(_quantile(prices, 0.75)),
        "n": n,
        "confident": True,
        "condition": condition,
    }


def deal_signal(price_cents, fair):
    """Classify a price against the fair-price quantiles.

    Returns ('deal'|'strong_deal'|'fair'|'expensive'|'no_data', reason).
    """
    if not fair or not fair.get("confident"):
        return "no_data", "insufficient offer history for this condition"
    if price_cents <= fair["p25"]:
        if fair["n"] >= 10 and price_cents <= fair["p25"] * 0.6:
            return "strong_deal", "40%+ below the low quartile of market offers"
        return "deal", "below the low quartile of market offers"
    if price_cents <= fair["median"]:
        return "fair", "at or below the market median"
    return "expensive", "above the market median"


def nearest_condition(condition):
    """Nearest higher-quality condition for widening searches."""
    try:
        i = CONDITION_ORDER.index(condition)
    except ValueError:
        return None
    return CONDITION_ORDER[i + 1] if i + 1 < len(CONDITION_ORDER) else None
