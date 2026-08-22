# wob — ROADMAP

wob is a small book-intelligence engine: it finds cheaper copies of books across the
web, resolves the right title/edition, and recommends books users will value. This
roadmap tracks its evolution into a trustworthy, measurable open-source engine — and
where it deliberately stays small.

The product answers three questions:

1. Is this the correct book and edition?
2. Is this listing genuinely a good deal?
3. Is this book valuable and relevant enough for me to buy?

North star: the **Wob Opportunity Score (WOS)** — a versioned, explainable score of
personal relevance, discount, condition, scarcity, seller trust, utility, and landed
cost. Long term: a personal book-buying agent that monitors the secondary market and
(only within explicit policies) acts. Default operating mode is `recommend_only`;
purchasing is gated behind explicit authorization in every mode.

## Current-state milestone matrix (audit 2026-08-23)

Legend: ✅ implemented · ◐ partial · ❌ missing · ⛔ blocked · ⏸ deferred

| M | Milestone | State |
|---|-----------|-------|
| 0 | Reproducible foundation | ◐ progress — typed entities (13, versioned), typed config w/ env validation, structured logging (log.py), 27 fixture tests, CI (tests + lint + harness), pyproject. Left: wire session.py→config, repo-wide lint debt, benchmark runner (eval.py) |
| 1 | Canonical book + offer pipeline | ◐ ISBN normalize (isbnlib), dedupe, snapshots, connector registry, retries exist; landed cost, currency normalization, full provenance missing |
| 2 | Book & edition entity resolution | ◐ baseline shipped — deterministic resolver R1-R6 w/ abstention, 24-pair labeled set, per-class eval (1.0 baseline). Left: dataset growth to 100+ pairs, embeddings only if they beat the baseline |
| 3 | Deal intelligence + WOS v1 | ◐ pct_off, history, alerts, condition picker; no fair-value model, seller trust, scarcity, or WOS formula |
| 4 | Personalized recommendations | ◐ hybrid similarity + course co-membership + discount boost with scores; no cold-start profile, interaction signals, or offline eval metrics |
| 5 | Reading-list & semester optimization | ◐ paste/drop parse, ISBN/title match, OL heal; no required/optional class, substitution logic, or basket optimizer |
| 6 | Monitoring, alerts & agentic safeguards | ◐ track/history/alerts/throttle exist; purchase modes/policy entities absent (purchasing ⛔ blocked — no executor exists; never add one without explicit authorization) |
| 7 | Adaptive personalization | ❌ intentionally deferred (no interaction data yet) |
| 8 | Institutional & market intelligence | ❌ deferred (post-consumer validation) |
| 9 | Production ML operations | ❌ deferred (usage does not justify it; eval harness is the seed) |

## Order of work (current)

1. **Milestone 0**: pyproject/typed config + schema validation (BookWork…OpportunityScore
   entities), stdlib fixtures + pytest-less unit tests (or lean pytest), CI for
   tests/lint/type-check alongside the existing npm publish workflow. Nothing breaks:
   the working CLI/dashboard/harness must stay green.
2. **Milestone 1**: provenance fields + landed cost + currency normalization + connector
   health — deterministic work that every later model reads.
3. **Milestone 2**: labeled match dataset + calibrated resolver with abstention
   (exact > fuzzy; embeddings only where baseline loses).
4. **Milestone 3**: WOS v1 scoring function with explanations + periodic re-eval.
5. M4→M6 as usage justifies; M7–M9 stay deferred until there is real user-interaction
   data or institutional demand.

See `ML_OBJECTIVES.md`, `ARCHITECTURE.md`, `MODEL_EVALUATION.md`.