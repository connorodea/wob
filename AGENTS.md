# WorldofBooks (`wob`) — agent guide

Cross-web used-book deal engine for learning books: worldofbooks.com (Algolia + Shopify
`.js`), thriftbooks.com (search API + HTML parse), plus Google Books / OpenLibrary /
Google Shopping / eBay providers, recommendations, WOS scoring, and a web dashboard.
Deal math, commands, and the cart cookie transplant are in README.md — this file carries
what an agent would otherwise miss.

## Traps first

- **Git repo: PUBLIC `connorodea/wob`, Apache-2.0.** Branch → PR → merge only; never push
  to main. **Merge only after CI is verifiably green** (`gh run watch --exit-status` first —
  replacing a gate check with assume-green already bit us once, PR #12).
- **Tests exist now.** `python -m unittest discover -s tests` (103 tests, all offline),
  `scripts/wob_verify.py` (7 data-integrity checks), `scripts/eval.py` (benchmark runner +
  append-only record at `docs/evals/benchmark-history.jsonl`). CI runs unit + ruff
  (check + format) + the harness.
- `data/` is committed (harvest is valuable, files small) except `.scan.lock`,
  `*.bak-*`, `provider_cache.json`; the npm tarball `*.tgz` is ignored.
- **`wob viz` (without `--png`) blocks in an IPython shell.** Non-interactive runs must use
  `wob viz --png`.
- **Networking is live and rate-limited** (0.25–0.6s polite waits). Keep test scans small
  (`--term`, low `--pages`/`--max-hits`). Paid providers (`googleshopping`, `amazon`) are
  NOT in default `--sites`; each uncached lookup costs ~$0.002, cached 24h.
- `data/` is the resumable state: `deals.jsonl` append-only, `state.json` seen-set
  (bare ISBN13-or-product-id for wob, `tb:<idWork>` for tb), `deals.csv` rebuilt from the
  JSONL. Ids are marked seen only after fetch succeeds (Ctrl-C safe). Never hand-edit
  `deals.jsonl`/`state.json`.

## Run / verify

- Shim `~/.local/bin/wob` → repo path + `.venv/bin/python3.13`. Equivalent:
  `PYTHONPATH=. .venv/bin/python3.13 -m wob`. Python 3.13 specifically.
- Quick checks: `wob deals --top 5`, `wob viz --png`, `wob coursepack list`,
  `wob app --port 8765` (dashboard, serves static files live per request).
- One-off scan: `wob scan --term "some term" --sites wob --pages 1 --max-hits 50`.

## Environment / config (outside the repo)

- Creds in `~/.config/wob/.env` (WOB_EMAIL/WOB_PASSWORD + optional SCRAPINGBEE_API_KEY,
  EBAY_APP_ID/EBAY_ACCESS_TOKEN; DataForSEO login/password live in
  `~/.claude/skills/seo/.env`). Never commit or print.
- Loaded through `wob/config.py` (`load_config(strict_creds=...)`) — the single validation
  path after M0. `wob login` is the strict consumer.
- Session cookie jar: `~/.config/wob/jar.txt` (MozillaCookieJar).
- ScrapingBee fallback is GET-only (session.py): 5xx retry ×3; 429/430/403 GET fallback;
  POSTs cannot be replayed → RuntimeError. Other 4xx raise immediately.
- Service-account key `~/.config/wob/gsheets-sa.json` exists but is unused: the Google
  Sheets tracker was cancelled — the repo (`docs/ROADMAP.md`) is the tracker. Sheets API
  refuses service accounts for consumer accounts anyway.

## Intelligence layer (the ML-adjacent modules — all deterministic, all baseline-first)

- `entities.py` — 13 versioned dataclasses (BookWork…PredictionProvenance), `validate()` /
  `to_dict()` / `from_dict()`; `SCHEMA_VERSION = "entities/1.0"`; canonical condition +
  purchase-mode vocabularies. Every new persistent field needs a schema story.
- `normalize.py` — pure title/author/publisher/format/language/date/currency
  normalization. Titles KEEP subtitles (colon-strip destroyed identifying words — the
  resolver calibration proved it).
- `resolver.py` — M2 baseline: R1/R2 shared ISBN = exact; R3 differing ISBNs fall back to
  work identity (editions share no ISBN); distinctive-token coverage + author gate →
  compatible/uncertain/incompatible. Never relabel as exact on ambiguity. Labeled eval:
  `tests/fixtures/matching/*.jsonl` (59 pairs, baseline 1.0 all classes — an embedding
  model must beat this before replacing any rule).
- `pricing.py` — landed cost (strict int cents), discount (None when reference can't
  anchor), cheapest-by-landed.
- `fairprice.py` — median/p25/p75 per (identity, condition) with abstention below 3
  offers; `deal_signal` classifies vs market quartiles.
- `scoring.py` — `wos_v1(...)` transparent weighted score (version `wos/1.0`,
  feature-level explanation) + `compute_deal_scores(rows)`. `woseval.py` compares WOS vs
  lowest-price on `tests/fixtures/deal_quality/*.jsonl` (WOS NDCG@8 0.995 vs 0.486).
- `profile.py` — M4: `build_profile` → UserProfile; `affinity()` = interest/author token
  overlap with readable reasons. All deterministic; embeddings/bandits are future work
  that must beat recorded baselines.
- `recommend.py` (seed-based recs), `coursepacks.py` (40 catalogs), `curated.py` (192
  titles, `Q` tier), `alerts.py` + `track`/`history` (price drops), `webapp.py` +
  `webapp_static/index.html` (stdlib server + vanilla SPA; palette = booksnob black/
  white/baby-blue/teal; logo asset `booksnob.png`).
- `theme.py` — all CLI color/formatting (auto-off when piped; `WOB_COLOR=1` forces,
  `NO_COLOR` kills). Never hardcode ANSI in commands — use `theme as T`.

## Subagent / parallel-lane policy (Connor's directive, 2026-08-22)

- **ALL agents run `deepseek/deepseek-v4-flash-0731` via OpenRouter** — main session,
  subagent launches (Task tool), and the `llm` CLI fan-out lane. Applied idempotently by
  the `deepseek-v4-flash` skill (`~/.claude/skills/deepseek-v4-flash/scripts/switch.sh`,
  `verify.sh`). Model id is the 0731 snapshot, NOT the rolling `deepseek-v4-flash` alias.
- **No token caps on llm calls** (Connor's ruling, 2026-08-22) — do not add `-o
  max_tokens`, and remove caps wherever seen.
- Flash returns empty completions ~half the time on some prompts — retry 3–4× with a
  byte-size check, hand-write the survivors; don't burn credits re-prompting endlessly.
- `$DEEPSEEK_AGENT_MODEL` and `$OPENROUTER_API_KEY` live in `~/.zshrc`. Claude Code routes
  via `ANTHROPIC_BASE_URL=https://openrouter.ai/api` (no `/v1`) + `ANTHROPIC_AUTH_TOKEN`.

## Site-collector layer (original scanner)

- `search.py` (WoB Algolia, 1000-hit cap), `products.py` (Shopify `.js`; NEW-variant or
  list-price reference; per-variant candidates), `picker.py` ($1.50/15% tie-break),
  `site_thriftbooks.py` (**fragile** `tb-hiddenText` regex — tb count → 0 means check the
  parser first), `deals.py` (append/dedupe identity `_identity_key` = isbn13-or-product_id
  for wob, product_id for tb; `_schema` stamped on new records), `cart.py` (Shopify cart
  writes with 429 backoff), `schedule.py` (launchd), `providers/` (registry + health()).

## Conventions

- Money: cents in JSON, dollars in deal records; canonical condition set everywhere;
  `--min-off` default 0.70; `pct_off = 1 − used/new`; `Q` is additive metadata.
- npm package `wob-cli` at repo root (`package.json`, `bin/wob.js`, `scripts/install.js`).
  Clear `__pycache__` before `npm pack`; publish flow requires a write-scoped granular npm
  token (classic tokens 403 for new packages).
- `DATA_DIR` relocates to `~/.local/share/wob/data` when the package dir is read-only.