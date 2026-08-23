"""M3: evaluate WOS ranking against the lowest-price baseline (offline).

Ranking metric: NDCG@K with binary relevance (good=2, not=0) plus
top-K precision — did the ranker put good deals first? The labeled set
is hand-judged; every row has a `good` boolean and the features WOS reads.
"""

from __future__ import annotations

import json
import math
import pathlib

from .scoring import wos_v1

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "deal_quality"


def load_rows():
    rows = []
    for f in sorted(FIXTURES.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _ndcg(ranked, k):
    gains = [2.0 if r["good"] else 0.0 for r in ranked[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def _precision_at_k(ranked, k):
    if not ranked[:k]:
        return 0.0
    return sum(1 for r in ranked[:k] if r["good"]) / len(ranked[:k])


def _score(rows, budget_cents):
    scored = []
    for r in rows:
        s = wos_v1(
            relevance=0.85 if r.get("quality") else 0.35,
            discount=float(r.get("pct_off", 0)),
            condition=r.get("condition", "UNKNOWN"),
            match_confidence=1.0,
            landed_cents=int(round(float(r["used_price"]) * 100)),
            stock=r.get("stock"),
            budget_cents=budget_cents,
        )
        scored.append((r, s.score))
    return scored


def evaluate(rows=None, budget_cents=None, k=10):
    rows = rows if rows is not None else load_rows()
    wos_rank = [r for r, _ in sorted(_score(rows, budget_cents), key=lambda x: -x[1])]
    price_rank = sorted(rows, key=lambda r: r["used_price"])
    return {
        "n": len(rows),
        "k": k,
        "wos": {
            "ndcg": round(_ndcg(wos_rank, k), 4),
            "precision": round(_precision_at_k(wos_rank, k), 4),
        },
        "lowest_price": {
            "ndcg": round(_ndcg(price_rank, k), 4),
            "precision": round(_precision_at_k(price_rank, k), 4),
        },
    }
