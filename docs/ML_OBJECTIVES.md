# wob — ML Objectives

What wob currently calls "matching" and "recommending" is deterministic logic, not
machine learning — and that is correct. Every ML-capable moment is listed here with
its baseline, dataset, evaluation, confidence, and fallback. Nothing here ships without
a measured win over the baseline.

## Doctrine

- Deterministic logic > classical ML > embeddings > LLMs > RL. Escalate only with
  evidence from the previous tier.
- Models must abstain when confidence is insufficient; abstention is a first-class
  output, not an error.
- Every prediction carries provenance: inputs, model id, version, threshold, output.
- No placeholder models, no mocked behavior, no "ML" labels on rules.

## Objective 1 — Edition/entity resolution (Milestone 2)

**Baseline**: exact ISBN match; weight-ordered token overlap on normalized
title/author; active today (crude) as `_match_title` + `match_quality`.

**Dataset**: hand-labeled pairs — exact / format-variant / different-edition /
international / instructor / bundled / similar-title / misspelled / incomplete / false
positive. Stored as versioned fixtures (JSONL) under `tests/fixtures/`.

**Model path**: transparent weighted features (shared ISBN count, normalized token
Jaccard, subtitle/punctuation folding, publication-year delta, format clue) →
pruned logistic regression only if features are shown to underserve the ambiguous
tail, with per-pair confidence. Semantic embeddings are a later option for
author/title paraphrase, gated by the same eval.

**Output**: classification ∈ {exact, compatible, incompatible, uncertain} +
confidence + explanation + evidence ids.

**Eval/metrics**: precision, recall, F1, confusion matrix, calibration error,
abstention-rate-vs-error tradeoff. Release bar: ≥98% precision on non-abstained
exact matches; ambiguity is always marked `uncertain`, never silently exact.

**Fallback**: if any model degrades, the deterministic baseline serves as rollback
(cold-swap by model id in config).

## Objective 2 — Fair value + Wob Opportunity Score v1 (Milestone 3)

**Baseline**: today's ranking = `pct_off` vs store-NEW or list price, cheapest-first.

**WOS v1**: a transparent, versioned scoring function:

```
WOS = f(relevance, discount, condition, scarcity, seller_trust, utility, landed_cost)
```

Deterministic per feature with weights in a versioned constants file; every score
carries a feature-level explanation string. Fair-price = edition+condition-aware
quantile of our own historical offers (with uncertainty interval). Price is NEVER
sufficient evidence of value alone.

**Eval**: ranked lists scored against manually labeled deal-quality examples;
compare WOS against lowest-price ranking (NDCG@K, top-K precision). Anomalies are
classified data-error vs probable-deal.

**Future (M7+, data-gated)**: learning-to-rank / contextual bandits, only when
user interactions exist. Personalization models never touch safety policy.

## Objective 3 — Recommendations (Milestone 4)

**Baseline today**: curated-title phrase similarity + course-pack co-membership +
discount boost (`wob/recommend.py`) — a content-based scorer with good precision and
deliberately zero ML.

**Additions in order**: semantic interest profile (user-picked seeds + edited),
book embeddings for topical adjacency, collaborative filtering when interaction
volume justifies it, diversity/serendipity controls, explanations like
"extends a subject you are studying" / "competing viewpoint".

**Eval**: offline Precision@K / Recall@K / NDCG@K / coverage / novelty / diversity
against popularity and content-only baselines; later, save/accept-rate online
signals. Sensitive preference data is opt-in and documented.

## Objective 4 — Reading lists (Milestone 5)

ML only for uncertain metadata extraction (fuzzy structure w/ per-field confidence +
flags) and compatibility prediction (older edition acceptable?) and resale value.
Basket optimization is deterministic OR (it is NOT labeled ML).

## Objective 5 — Agentic purchasing (Milestone 6, gated)

Modes: `observe_only` < `recommend_only` (default) < `confirmation_required` <
`autonomous_within_policy`. Any purchase executor requires explicit authorization +
spending controls + dry-run + idempotency + audit logs. Safety violations have a
hard zero target. No purchase code exists today, and none is added without the
policy layer first.