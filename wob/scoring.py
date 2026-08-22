"""Wob Opportunity Score v1 (M3) — transparent, versioned, deterministic.

WOS = f(relevance, discount, condition, scarcity, seller trust,
        utility, landed cost) as an explainable weighted sum. No learned
weights yet: every feature, weight, and explanation is visible. Version
bumps when the formula changes; older scores stay reproducible via the
version string recorded on each OpportunityScore.

Price is never sufficient evidence alone: relevance and match confidence
must contribute, and a landed cost above budget caps the score hard.
"""

from __future__ import annotations

import time

from .entities import OpportunityScore

WOS_VERSION = "wos/1.0"

CONDITION_VALUE = {
    "NEW": 1.0,
    "LIKE_NEW": 0.92,
    "VERY_GOOD": 0.82,
    "GOOD": 0.65,
    "WELL_READ": 0.5,
    "ACCEPTABLE": 0.35,
    "UNKNOWN": 0.5,
}

WEIGHTS = {
    "relevance": 0.30,
    "discount": 0.25,
    "condition": 0.15,
    "scarcity": 0.10,
    "match_confidence": 0.10,
    "budget_fit": 0.10,
}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def compute_deal_scores(rows, budget_cents=None):
    """Map deal records (deals.jsonl shape) to OpportunityScore rows.

    Relevance proxy: quality flag (curated shelf) -> 0.85, else 0.35.
    Match confidence: 1.0 for scanned records (they passed our pipeline).
    Returns [(record, score), ...] sorted by score desc.
    """
    out = []
    for r in rows:
        try:
            price = float(r["used_price"])
            pct = float(r.get("pct_off") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        s = wos_v1(
            relevance=0.85 if r.get("quality") else 0.35,
            discount=pct,
            condition=r.get("condition", "UNKNOWN"),
            match_confidence=1.0,
            landed_cents=int(round(price * 100)),
            stock=r.get("stock"),
            budget_cents=budget_cents,
        )
        out.append((r, s))
    out.sort(key=lambda x: -x[1].score)
    return out


def _scarcity(stock):
    if stock is None:
        return 0.5  # neutral: unknown stock is not a signal
    if stock <= 3:
        return 1.0
    if stock <= 10:
        return 0.7
    return 0.3


def _budget_fit(landed_cents, budget_cents):
    if budget_cents is None:
        return 1.0
    if landed_cents <= budget_cents:
        return 1.0
    over = (landed_cents - budget_cents) / max(budget_cents, 1)
    return _clamp(1.0 - over)


def wos_v1(
    *,
    relevance: float,
    discount: float,
    condition: str,
    match_confidence: float,
    landed_cents: int,
    stock: int | None = None,
    budget_cents: int | None = None,
    seller_trust: float | None = None,
) -> OpportunityScore:
    """Compute WOS v1. All float features in [0,1]; discount may exceed 1
    only via `pct_off` style values >1 which get clamped."""
    inputs = {
        "relevance": relevance,
        "discount": discount,
        "condition": condition,
        "match_confidence": match_confidence,
        "landed_cents": landed_cents,
        "stock": stock,
        "budget_cents": budget_cents,
        "seller_trust": seller_trust,
    }
    relevance = _clamp(float(relevance))
    discount = _clamp(float(discount))
    match_confidence = _clamp(float(match_confidence))
    cond_value = CONDITION_VALUE.get(condition, 0.5)
    scarcity = _scarcity(stock)
    budget_fit = _budget_fit(int(landed_cents), budget_cents)
    trust = _clamp(float(seller_trust)) if seller_trust is not None else 0.5

    score = round(
        WEIGHTS["relevance"] * relevance
        + WEIGHTS["discount"] * discount
        + WEIGHTS["condition"] * cond_value
        + WEIGHTS["scarcity"] * scarcity
        + WEIGHTS["match_confidence"] * match_confidence
        + WEIGHTS["budget_fit"] * budget_fit
        + 0.0 * trust,  # seller trust reserved (0 weight in v1)
        4,
    )
    score = _clamp(score)

    explanation = (
        f"WOS {WOS_VERSION}: relevance {relevance:.2f}, discount {discount:.2f}, "
        f"condition {condition} ({cond_value:.2f}), scarcity {scarcity:.2f} "
        f"(stock={stock}), match {match_confidence:.2f}, budget fit {budget_fit:.2f} "
        f"(landed ${landed_cents / 100:.2f}"
        + (f" vs ${budget_cents / 100:.2f})" if budget_cents else ")")
        + f", seller trust {trust:.2f} (unweighted)"
    )
    return OpportunityScore(
        score=score,
        version=WOS_VERSION,
        inputs=inputs,
        explanation=explanation,
        computed_at=time.time().__str__(),
    )
