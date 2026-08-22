# World of Books deal scanner

Finds used ML/AI/neural-network books on worldofbooks.com **and
thriftbooks.com** that are ~70%+ off the new copy (or list) price, scores
"great books to learn from" against a curated list, and can add the winners to
your cart.

## How deals are measured

Two sites, one deal rule:

```
pct_off = 1 - (best available used-copy price / new-copy reference price)
```

- **WoB (wob)**: discovery via the theme's public Algolia index
  (`shopify_products_us`: author, ISBN, available conditions, list price).
  Exact per-condition prices from Shopify `/products/<handle>.js`.
  Reference = cheapest NEW variant of the same title.
- **ThriftBooks (tb)**: discovery via the public
  `POST /api/browse/Search` endpoint (50 works/page, works across pages).
  Exact per-condition prices parsed from product-page condition buttons.
  Reference = the "New" row price when TB stocks it, else the publisher
  list price.

Condition tie-break (your rule): when a cheaper copy sits within ~$1.50 / ~15%
of a better-condition copy, the better condition wins.

Quality (`wob/curated.py`) is a hand-curated list of ~170 canonical learning
books (Bishop, Goodfellow, Géron, Sutton & Barto, Russell & Norvig, ...)
matched on title + URL handle — deals marked `Q` are the "great books to learn
from" tier.

## Install

```
npm i -g wob-cli            # the full bootstrap: creates ~/.wob-venv, needs python3.13
```

or, from source:

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The `wob` shim at `~/.local/bin/wob` points at this venv. On installed
copies, scan data lives at `~/.local/share/wob/data` (override with
`WOB_DATA_DIR`).

Credentials live in `~/.config/wob/.env` (WOB_EMAIL / WOB_PASSWORD), never in the repo.

## Commands

```
wob login                 # log the API session into your WoB account
wob scan                  # all keywords, both sites (wob: 400 hits/kw, tb: 50/kw)
wob scan --term "operating systems"      # one-off, ANY search term
wob scan --sites wob --pages 3 --max-hits 1000 --min-off 0.8
wob scan --sites tb --pages 4
wob scan --fresh          # re-queue state-only items; existing deals stay skipped
wob deals                  # quality-first sorted list
wob deals --quality        # curated great-book titles only
wob viz                    # IPython shell + pandas `df` over the deals
wob viz --png              # write the 3 charts only (data/viz_*.png)
wob search --isbn 9781491901427        # cross-web price compare by ISBN
wob search --barcode 9781491901427     # same, barcode in
wob search --term "sutton reinforcement" --limit 3   # metadata search
wob search --isbn 978x --sites googlebooks,openlibrary --json
wob cart --show            # API-session cart
wob cart --add 12          # add top 12 to the API session's cart
wob cart --clear           # clear the API session cart
wob js-plan --top 12       # in-browser add-to-cart JS snippets (top N, wob-only)
```

Any search term works — the curated `Q` tier only lights up for known learning
titles; everything else is still price-filtered.

## Cross-web search (`wob search`)

One ISBN in → best prices out, provider by provider:

- **googlebooks** — new-copy retail/list price (the reference anchor) + buy link
- **openlibrary** — metadata, covers, edition ISBNs (no prices)
- **googleshopping** — Google Shopping listings via your DataForSEO account
  (~$0.002/uncached query, cached 24h; add `googleshopping` to `--sites`.
  Queries are title-anchored — bare-ISBN shopping searches match the wrong book)
- **ebay** — used marketplace listings; enabled once
  `EBAY_APP_ID` + `EBAY_ACCESS_TOKEN` are in `~/.config/wob/.env`
- **local:** — your already-scanned wob/tb deals matching that ISBN

Results sort by price; `ref%` is the discount vs the new retail anchor.
ISBN normalization (10↔13, EAN/barcode) is handled by `isbnlib`.

## Scheduled keyword sets (launchd)

```
wob schedule add ml --keywords keywords.txt --every 12 --sites wob,tb
wob schedule add woodworking --keywords sets/example-topic.txt --every 24
wob schedule list
wob schedule now ml          # run one immediately
wob schedule remove woodworking
```

- Keyword sets are plain text files, one term per line (`sets/` is the
  convention; `#` lines ignored).
- Schedules are launchd agents (`~/Library/LaunchAgents/`), survive reboots,
  run silently; logs land in `data/logs/<name>.log` and `<name>.err.log`.
  `--every` minimum is 0.25h (15 min).
- A `.scan.lock` in `data/` stops overlapping runs (a second run exits
  immediately).

## Adding to YOUR cart (WoB only)

Shopify carts are per-browser-cookie, and Chrome 137+ no longer allows remote
debugging on your normal profile — so browser automation can't reach the cart
open in your Chrome. The workaround is a 30-second one-way cookie transplant:

1. `wob login && wob cart --add <N>` — fills an authenticated API cart.
2. `wob cart --cookie` — prints the `cart` cookie value.
3. In your Chrome, on worldofbooks.com, paste it via the
   [Cookie-Editor](https://cookie-editor.com) extension (name: `cart`,
   domain: `www.worldofbooks.com`), or run it in the DevTools console:
   `document.cookie="cart=<value>; path=/; domain=.worldofbooks.com"`.
4. Reload `/cart` — your browser now holds that cart and you check out
   normally with your own account.

ThriftBooks has no equivalent open cart API used here — its deals export as
URLs you open normally.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Open source, community welcome.

## Boring details

- Search: Algolia `shopify_products_us` via the theme's public key, 1000
  hits/request. Exact pricing: Shopify `/products/<handle>.js`.
- Requests go direct first; GET requests on 429/430/403 fail over to
  ScrapingBee (SCRAPINGBEE_API_KEY in ~/.config/wob/.env). POSTs (Algolia,
  TB search, login) can't be replayed there, so blocked POSTs raise instead.
- Resumable: `data/deals.jsonl` is append-only, `data/state.json` tracks
  every scanned item, so re-runs only fetch new products. Interrupting a
  scan (Ctrl-C) is safe — items only count as seen after their fetch
  succeeds. Delete `data/` to start over.
- Keywords: edit `keywords.txt`, one query per line. Curated quality list:
  `wob/curated.py`.
- Visualization: `wob viz` opens IPython with a pandas `df` of all deals;
  `wob viz --png` writes PNG charts (discount histogram, top deals, by site).