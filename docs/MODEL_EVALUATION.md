# wob — MODEL EVALUATION

How every predictive addition is judged, and how we keep the deterministic baseline
honest. Rules first, current harness second, future targets third.

## Rules

1. Every model change ships with: baseline, dataset, eval method, confidence output,
   and a rollback path (the prior model or the deterministic rule).
2. Ablation is required before promotion: a ML component must beat the deterministic
   baseline on a held-out set it was not tuned on.
3. No live-website requests in core CI. Connector tests use recorded/synthetic
   fixtures; live connectors get a flagged manual gate.
4. Scores are explanations: every WOS / recommendation / resolution must render a
   human-readable reason; a score without an explanation is a bug.
5. Price is never sufficient evidence of value — eval sets must include
   cheap-but-bad and expensive-but-right cases.

## Current harness (`scripts/wob_verify.py`, 7 checks)

Deterministic integrity only — what exists today:

| Check | What it asserts |
|---|---|
| jsonl integrity | every deals.jsonl line parses |
| dedupe | canonical identity keys unique |
| csv sync | CSV row count == JSONL; header == CSV_COLS; row spot-checks |
| state.json | `seen` shape histogram |
| cli smoke | `deals`, `viz --png`, `schedule list`, `js-plan` exit 0 |
| scan-seen simulation | mocked fetch: success→seen, exception→retryable, honest counts |
| empty viz | no-data path exits clean |

Run: `.venv/bin/python3.13 scripts/wob_verify.py` (data-local; no network).

## Measurement framework (targets by milestone)

### Matching (M2)
- exact-edition precision (release bar ≥98% where not abstained)
- compatible-edition precision · recall · abstention rate
- calibration error · false-substitution rate (target: 0 silent substitutions)

### Deal intelligence (M3)
- fair-price prediction error (MAE/MAPE + uncertainty interval coverage)
- anomaly precision · top-K deal-ranking precision (WOS vs lowest-price baseline)
- savings as landed cost, not sticker price · seller-risk false-negative rate

### Recommendations (M4)
- Precision@K · Recall@K · NDCG@K · coverage · novelty · diversity
- vs popularity-only and content-only baselines · online: save rate, accept rate

### Reading lists (M5)
- extraction accuracy · required-vs-optional classification
- edition-substitution precision · basket savings · constraint-violation rate (0)

### Agent behavior (M6)
- alert acceptance rate · notification fatigue
- policy-violation, duplicate-purchase, unauthorized-purchase counts — **hard zero**

## Dataset & experiment bookkeeping

- Labeled fixtures live under `tests/fixtures/` versioned by commit (M0/M2).
- Every eval run records: model id, dataset commit, metrics, and produced files to
  `docs/evals/<date>-<model>.md`. No metric enters a doc or spreadsheet without the
  run log that produced it.

## Evaluation harness (M0 deliverable)

Seed = current 7-check harness promoted into the test suite plus:
- schema validation tests for domain entities
- golden-data tests for normalization (ISBN, titles, currencies) written for M1
- fixture-driven connector contract tests
- regression benchmark runner (`scripts/eval.py <suite>`) with a versioned results file