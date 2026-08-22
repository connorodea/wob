import csv
import json
import os
import pathlib

from .curated import match_quality


def _data_dir():
    env = os.environ.get("WOB_DATA_DIR")
    if env:
        return pathlib.Path(env)
    default = pathlib.Path(__file__).resolve().parent.parent / "data"
    if (default.parent).exists() and os.access(default.parent, os.W_OK) or default.exists():
        return default
    # npm/managed install: package dir may be read-only — use the user dir
    return pathlib.Path.home() / ".local" / "share" / "wob" / "data"


DATA_DIR = _data_dir()
DEALS_JSONL = DATA_DIR / "deals.jsonl"
DEALS_CSV = DATA_DIR / "deals.csv"
STATE_JSON = DATA_DIR / "state.json"

CSV_COLS = [
    "product_id", "site", "title", "author", "handle", "variant_id", "condition",
    "source", "country", "format", "used_price", "new_price", "ref_source",
    "pct_off", "quality", "isbn13", "isbn10", "barcode", "upc", "sku", "stock",
    "publisher", "list_price_us", "rrp", "url",
]

HISTORY_JSONL = DATA_DIR / "history.jsonl"


def snapshot_history(records):
    """Append a (identity, price) row per record for price-change tracking."""
    for r in records:
        key = r.get("isbn13") or r.get("barcode") or r.get("product_id")
        if not key:
            continue
        HISTORY_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "identity": key,
                "site": r.get("site", "wob"),
                "condition": r.get("condition", ""),
                "used_price": r.get("used_price"),
                "new_price": r.get("new_price"),
                "pct_off": r.get("pct_off"),
            }) + "\n")


def load_history():
    if not HISTORY_JSONL.exists():
        return {}
    out = {}
    for line in HISTORY_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.setdefault(r["identity"], []).append(r)
    return out


def ensure_checked_fields(rec):
    if "quality" not in rec:
        rec["quality"] = bool(
            match_quality(rec.get("title", ""), rec.get("handle", ""))
        )
    if not rec.get("site"):
        rec["site"] = "wob"
    return rec


def _identity_key(rec):
    site = rec.get("site") or "wob"
    if site == "wob":
        isbn = rec.get("isbn13")
        if isinstance(isbn, str) and isbn.strip():
            key = isbn
        else:
            key = rec.get("product_id")
    else:
        key = rec.get("product_id")
    return site, key


def existing_ids():
    if not DEALS_JSONL.exists():
        return set()
    ids = set()
    for line in DEALS_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            site, key = _identity_key(rec)
            if site == "wob":
                ids.add(key)
        except json.JSONDecodeError:
            continue
    return ids


def existing_keys():
    keys = set()
    if not DEALS_JSONL.exists():
        return keys
    for line in DEALS_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            keys.add(_identity_key(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return keys


def append_deals(records):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    keys = existing_keys()
    wrote = 0
    with open(DEALS_JSONL, "a", encoding="utf-8") as f:
        for rec in records:
            k = _identity_key(rec)
            if k in keys:
                continue
            keys.add(k)
            f.write(json.dumps(rec) + "\n")
            wrote += 1
    if wrote:
        rebuild_csv()
        snapshot_history(records)
    return wrote


def rebuild_csv():
    if not DEALS_JSONL.exists():
        return
    rows = [
        ensure_checked_fields(json.loads(l))
        for l in DEALS_JSONL.read_text().splitlines()
        if l.strip()
    ]
    rows.sort(key=lambda r: (-r["quality"], -r["pct_off"]))
    with open(DEALS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_deals(sorted_desc=True):
    if not DEALS_JSONL.exists():
        return []
    rows = [
        ensure_checked_fields(json.loads(l))
        for l in DEALS_JSONL.read_text().splitlines()
        if l.strip()
    ]
    if sorted_desc:
        rows.sort(key=lambda r: (-r.get("quality", False), -r.get("pct_off", 0)))
    return rows


def load_scan_state():
    if not STATE_JSON.exists():
        return set()
    try:
        return set(json.loads(STATE_JSON.read_text()).get("seen", []))
    except json.JSONDecodeError:
        return set()


def save_scan_state(seen):
    STATE_JSON.write_text(json.dumps({"seen": sorted(seen)}))