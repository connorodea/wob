# WorldofBooks (`wob`) — agent guide

Used-book deal scanner: finds ML/AI learning books on worldofbooks.com (Algolia + Shopify
`.js`) and thriftbooks.com (public search API + HTML parsing) at ≥70% off the new-copy price.
Deal math, commands, and the cart cookie transplant are documented in README.md — this file
only carries what an agent would otherwise miss.

## Traps first

- **Not a git repo.** No commits, branches, or PRs. Don't run git commands or attempt a git
  workflow here.
- **No tests, no lint, no typecheck.** "Verification" means running the CLI and inspecting
  `data/` output. Don't look for a test suite.
- **`wob viz` (without `--png`) drops into an interactive IPython shell and blocks.** Non-
  interactive runs must use `wob viz --png`. Same for anything that embeds IPython.
- **Networking is live and rate-limited.** Every scan hits real public endpoints (Algolia,
  Shopify, ThriftBooks) with 0.25–0.6s polite waits. Keep scans small (`--term`, low
  `--pages`/`--max-hits`) when testing; don't re-run full scans casually.
- **`data/` is the resumable state.** `deals.jsonl` is append-only, `state.json` holds the
  seen-ID set (`{"seen": [...]}`: bare ISBN13-or-product-id for wob, `tb:<idWork>` for tb),
  `deals.csv` is rebuilt from the JSONL. Deleting `data/` wipes scan history. Scans are
  walk-away safe: ids are marked seen only after their fetch succeeds, so Ctrl-C never
  loses items. Never hand-edit `deals.jsonl`/`state.json` casually — a new field or bad
  line affects `rebuild_csv` and dedupe.

## Run / verify

- Entry point is the shim `~/.local/bin/wob` — it hardcodes the repo path and
  `$HOME/Developer/WorldofBooks/.venv/bin/python3.13`. From the repo root:
  `PYTHONPATH=. .venv/bin/python3.13 -m wob` is equivalent.
- **Python is 3.13 specifically** (shim hardcodes `python3.13` in the venv path). Create the
  venv with `python3.13 -m venv .venv`.
- Quick non-destructive checks: `wob deals --top 5`, `wob viz --png`, `wob schedule list`,
  `wob cart --show`.
- A one-off test scan: `wob scan --term "some term" --sites wob --pages 1 --max-hits 50`.

## Environment / config (outside the repo)

- Credentials: `~/.config/wob/.env` → `WOB_EMAIL`, `WOB_PASSWORD`, plus optional
  `SCRAPINGBEE_API_KEY`. Never commit or print these.
- Session cookie jar: `~/.config/wob/jar.txt` (MozillaCookieJar, saved after login/cart-add).
  `wob login` raises `KeyError` if the `.env` keys are missing — that's the diagnosis when
  login dies immediately.
- ScrapingBee is only a fallback for **GET** requests: `session.fetch` retries 5xx up to 3×,
  then on 429/430/403 a GET fails over to ScrapingBee. Other 4xx (e.g. 404) raise
  immediately. POSTs (Algolia, TB search, login, cart writes) can't be replayed by
  ScrapingBee, so blocked POSTs raise `RuntimeError`. Without the key, blocked GETs raise.

## Module map (`wob/`)

- `cli.py` — argparse subcommands; owns the `.scan.lock` pidfile (PID-liveness checked via
  `os.kill(pid, 0)`, so stale locks self-clear; a live lock makes a second scan exit with
  "another scan is already running").
- `session.py` — requests session, cookie jar, `fetch` retry/fallback, `login`, `polite_wait`.
- `search.py` — WoB discovery via the theme's public Algolia index (`shopify_products_us`),
  max 1000 hits/request.
- `products.py` — exact pricing from Shopify `/products/<handle>.js`; reference price =
  cheapest `option2 == "NEW"` variant. Deal URL is `...?variant=<variant_id>`.
- `picker.py` — condition tie-break: among candidates within $1.50 or 15% of the cheapest,
  best condition wins (priority map NEW > LIKE_NEW > VERY_GOOD > GOOD > WELL_READ >
  ACCEPTABLE).
- `site_thriftbooks.py` — `POST /api/browse/Search` (50/page) + **fragile regex parsing** of
  `tb-hiddenText` divs in `_parse_page`. If TB changes markup it silently yields no blocks
  and no deals — treat tb deal count dropping to zero as a parser issue first.
- `deals.py` — JSONL append (dedupe on `(site, isbn13-or-product_id)` for wob, `product_id`
  for tb), CSV rebuild, scan state.
- `curated.py` — ~90-title "great books to learn from" list; `match_quality` normalizes
  title+handle to tokens and AND-matches author-title keyword tuples. Deals with `quality`
  true are the `Q` tier.
- `cart.py` — WoB Shopify cart API only (tb deals have no `variant_id`; `cart --add` filters
  `site == "wob"`). Adds sleep 4s between items; 429 backs off exponentially.
  `clear_session_cart` POSTs `/cart/change.js` per line item (same backoff, raises if
  still blocked, skips items without a `key`).
- `schedule.py` — launchd agents `com.connorodea.wob-scan.<name>` in
  `~/Library/LaunchAgents/`; logs to `data/logs/<name>.log` / `<name>.err.log`.
- `viz.py` — pandas DF over deals, 3 PNGs in `data/`, then IPython unless `--png`.
- `theme.py` — all CLI color/formatting (frames, badges, score bars). Auto-disabled when
  stdout isn't a TTY; force with `WOB_COLOR=1`, kill with `NO_COLOR`. Never hardcode
  ANSI in command code — go through `theme` (import as `T`).
- `recommend.py` — taste adjacency: curated title-phrase similarity + course-pack
  co-membership, discounted-price boost. `coursepacks.py` — 35 built-in course catalogs,
  each references curated token tuples.
- `alerts.py` — `wob alerts`: price drops (from history) + sub-$10 Q-tier screams;
  `--notify` dedupes against `data/alerts_state.json` and fires a desktop ping.
  `wob track` re-prices tracked wob books and appends history snapshots (only wob rows —
  tb rows skip). `wob history` reads `data/history.jsonl` and lists drops.
- **npm packaging lives at the repo root** (`package.json`, `bin/wob.js`,
  `scripts/install.js`, `LICENSE`, `.npmignore`). The package ships `wob/` and bootstraps
  `~/.wob-venv` on postinstall. Debris never ships: keep `files` whitelist + clear
  `__pycache__` before `npm pack`.
- **Data-dir relocation**: `deals.py` moves `DATA_DIR` to `~/.local/share/wob/data` when
  the package dir isn't writable (or `WOB_DATA_DIR`). Never assume `data/` sits next to
  the package.
- `isbnutil.py` — ISBN/barcode normalization (10↔13, EAN-13 checksum) via `isbnlib`.
- `providers/` — cross-web search registry: each module exposes `NAME`, `ENABLED`,
  `lookup(isbn13) -> dict`, optional `search(term)`. `googlebooks` = retail anchor,
  `openlibrary` = metadata/editions (no prices), `googleshopping` = Google Shopping
  via DataForSEO Merchant API (uses seo-skill creds, paid per task_post ~$0.002,
  cached 24h in `data/provider_cache.json`, title-anchored keyword required),
  `ebay` = marketplace (needs `EBAY_APP_ID`+`EBAY_ACCESS_TOKEN` in
  `~/.config/wob/.env`). `conditions.py` maps each marketplace's vocabulary to the
  canonical condition set.

## Conventions specific to this repo

- All money in cents in JSON (Shopify), converted to dollars (÷100) in deal records.
- Condition strings are a canonical set shared by both sites (`NEW`, `LIKE_NEW`, ...).
- `--min-off` default 0.70 everywhere; deal floor shown in `viz_discount_hist.png`.
- Both sites' records add `pct_off = 1 − used/new`; `Q`/quality is additive metadata, never
  part of the price filter.