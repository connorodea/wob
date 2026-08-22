# wob — ARCHITECTURE

Single Python package, 3.13, no web framework, no database server. The engine is a
local CLI + dashboard with append-only JSONL state. Boundaries below are the contract
for the Milestone 0→3 work.

## Layers (current + target)

```
┌─────────────────────────────────────────────────────────────┐
│ Interfaces: CLI (wob/* cli.py + theme) · web (webapp.py)    │
├─────────────────────────────────────────────────────────────┤
│ Intelligence (product logic, deterministic first)           │
│  identity (isbnutil) · curated · picker · coursepacks       │
│  recommend · alerts · history/track                         │
│  ─ future: resolver (M2) · scoring/WOS (M3) · policies (M6) │
├─────────────────────────────────────────────────────────────┤
│ Domain entities: BookWork · BookEdition · BookIdentifier    │
│  BookOffer · Seller · ConditionAssessment · UserProfile     │
│  ReadingList · Recommendation · Watchlist · PurchasePolicy  │
│  OpportunityScore · PredictionProvenance                    │
│  (M0: typed, schema-validated, versioned)                   │
├─────────────────────────────────────────────────────────────┤
│ Collection: connectors (wob/providers/*) + site modules     │
│  (wob search/products/site_thriftbooks)                     │
│  contract: NAME, ENABLED, lookup(isbn13[,keyword]),         │
│  search(term) — no vendor types leak into core              │
├─────────────────────────────────────────────────────────────┤
│ Persistence: append-only JSONL (deals, history) + state,    │
│  csv export, provider_cache (24h). DATA_DIR relocates to    │
│  ~/.local/share/wob/data when the package dir is read-only. │
└─────────────────────────────────────────────────────────────┘
```

## Modules today

| Module | Role |
|---|---|
| `cli.py` | argparse surface; scan lock (pidfile); all commands |
| `session.py` | requests session + cookie jar; retries; GET-only ScrapingBee fallback |
| `search.py` | WoB discovery (public Algolia); meta mapping |
| `products.py` | WoB pricing via Shopify `.js`; NEW-variant or list-price reference; per-variant deal candidate |
| `site_thriftbooks.py` | TB search API + fragile `tb-hiddenText` page parse; canonical condition mapping |
| `picker.py` | condition tie-break (≤$1.50 or 15% window) |
| `curated.py` | 192-title canonical learning shelf (tokens for matching + Q tier) |
| `coursepacks.py` | 35 course catalogs referencing curated tokens |
| `recommend.py` | content similarity + co-course + discount boost (baseline recs) |
| `deals.py` | JSONL append/dedupe (isbn13-or-product_id), CSV rebuild, history snapshots, DATA_DIR relocation |
| `alerts.py` | drop/scream detection; dedupe state; macOS notify |
| `providers/` | openlibrary (metadata), googlebooks (retail anchor), googleshopping/amazon (DataForSEO, title-anchored, cached, paid-aware), ebay (key-gated), conditions maps |
| `webapp.py` | stdlib HTTP server; /api/* endpoints incl. pricelist; live dashboard |
| `theme.py` | terminal styling (auto-off when piped) |
| `viz.py` | pandas summaries + PNG charts |
| `schedule.py` | launchd agents for recurring scans |

## Platform contracts

- Python 3.13 (venv `.venv` local, `~/.wob-venv` for npm installs). Stdlib + requests,
  isbnlib, pandas, matplotlib, ipython.
- npm package `wob-cli`: Node bin delegating to `~/.wob-venv` python (`bin/wob.js` +
  `scripts/install.js`). GitHub Actions publishes on version change (`publish-npm.yml`).
- Verification: custom harness (jsonl integrity, dedupe, csv sync, state shape, CLI
  smoke, scan-seen simulation, empty-viz) — the seed of the formal test suite (M0).

## Determinism vs ML (current truth)

Everything shipped so far is deterministic: ISBN normalization, token matching,
percent-off math, similarity scores. No model weights, no embeddings, no "AI" beyond
the name in the docs that call it home. ML arrives only at documented objectives in
`ML_OBJECTIVES.md`, each with baseline + eval + fallback.

## Provenance (M1 target)

Every normalized record keeps: source URL, connector name, retrieval timestamp,
raw-evidence reference (e.g. original variant barcode/sku), and the normalization
path. Today: partial (barcode/sku/isbn10/url exist; retrieval time and raw payload
reference are missing).