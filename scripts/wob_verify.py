#!/usr/bin/env python3.13
"""wob_verify — non-destructive verification harness for the `wob` CLI.

Runs against the REAL repo data (resolved relative to this file) without
modifying it (the only writes are the PNGs that `wob viz --png` itself
produces as its normal behavior, plus throwaway temp dirs removed at the end).

Stdlib only. Run with the repo's venv python (needed for matplotlib/pandas):

    .venv/bin/python3.13 scripts/wob_verify.py

Exit code 0 when every check passes, 1 otherwise.
"""

import contextlib
import csv
import io
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

REPO = pathlib.Path(__file__).resolve().parent.parent

# Make `import wob` work regardless of the harness' own location / cwd.
# (PYTHONPATH equivalent, set inside the script itself.)
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import wob.cli as cli                 # noqa: E402
import wob.deals as deals_mod         # noqa: E402
import wob.viz as viz                 # noqa: E402

random.seed(20260821)

RESULTS = []  # (number, name, ok, details)


def record(num, name, ok, details=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((num, name, ok))
    print(f"[{num}] {name:30s} ... {status}" + (f"  ({details})" if details else ""))


def fail_short(num, name, msg):
    record(num, name, False, msg)


def parse_jsonl(path):
    """Return (records, bad) where bad = [(lineno, error, excerpt)] for non-empty lines."""
    records, bad = [], []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except (json.JSONDecodeError, ValueError) as e:
            bad.append((lineno, str(e), line[:80]))
    return records, bad


# --------------------------------------------------------------------------- #
# 1. JSONL integrity
# --------------------------------------------------------------------------- #
def check1():
    p = deals_mod.DEALS_JSONL
    if not p.exists():
        fail_short(1, "jsonl integrity", f"missing {p}")
        return
    records, bad = parse_jsonl(p)
    if bad:
        shown = "; ".join(f"line {ln}: {exc} ({excerpt!r})" for ln, exc, excerpt in bad[:3])
        fail_short(
            1, "jsonl integrity",
            f"{len(records)} ok / {len(bad)} bad — {shown}"
            + (" (+more)" if len(bad) > 3 else ""),
        )
        return
    record(1, "jsonl integrity", True, f"{len(records)} non-empty lines, 0 bad")


# --------------------------------------------------------------------------- #
# 2. Dedupe on canonical (site, isbn13-or-product_id) keys
# --------------------------------------------------------------------------- #
def check2():
    p = deals_mod.DEALS_JSONL
    records, bad = parse_jsonl(p)
    if bad:
        fail_short(2, "dedupe", "skipped: jsonl has unparsable lines (check 1)")
        return
    from collections import Counter

    keys = Counter(deals_mod._identity_key(r) for r in records)
    collisions = {k: n for k, n in keys.items() if n > 1}
    if collisions:
        shown = "; ".join(f"{k!r} x{n}" for k, n in list(collisions.items())[:5])
        extra = sum(n - 1 for n in collisions.values())
        fail_short(
            2, "dedupe",
            f"{len(collisions)} colliding keys, {extra} duplicate records — {shown}"
            + (" (+more)" if len(collisions) > 5 else ""),
        )
        return
    record(2, "dedupe", True, f"{len(keys)} unique canonical keys")


# --------------------------------------------------------------------------- #
# 3. CSV sync + header + random row spot checks
# --------------------------------------------------------------------------- #
def check3():
    p, c = deals_mod.DEALS_JSONL, deals_mod.DEALS_CSV
    records, bad = parse_jsonl(p)
    if bad:
        fail_short(3, "csv sync", "skipped: jsonl has unparsable lines (check 1)")
        return
    if not c.exists():
        fail_short(3, "csv sync", f"missing {c}")
        return

    with open(c, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)

    if header != deals_mod.CSV_COLS:
        fail_short(3, "csv sync", f"header mismatch: csv={header} vs CSV_COLS={deals_mod.CSV_COLS}")
        return
    if len(rows) != len(records):
        fail_short(3, "csv sync", f"count mismatch: jsonl={len(records)} csv={len(rows)}")
        return

    # Index csv rows by (site, product_id) -> list of rows (dups possible if check 2 fails)
    index = {}
    for row in rows:
        site = row.get("site") or "wob"
        key = (site, str(row.get("product_id", "")))
        index.setdefault(key, []).append(row)

    sample = random.sample(records, min(5, len(records)))
    for rec in sample:
        site = rec.get("site") or "wob"
        key = (site, str(rec.get("product_id", "")))
        matches = index.get(key, [])
        hit = None
        for row in matches:
            try:
                same = (
                    row.get("title") == rec.get("title", "")
                    and abs(float(row["used_price"]) - float(rec["used_price"])) < 1e-6
                    and abs(float(row["new_price"]) - float(rec["new_price"])) < 1e-6
                    and abs(float(row["pct_off"]) - float(rec["pct_off"])) < 1e-6
                )
            except (KeyError, TypeError, ValueError):
                same = False
            if same:
                hit = row
                break
        if hit is None:
            fail_short(
                3, "csv sync",
                f"spot-check miss for {key!r} title={rec.get('title', '')[:60]!r} "
                f"(no matching csv row; {len(matches)} candidate row(s) for that key)",
            )
            return
    record(3, "csv sync", True,
           f"{len(rows)} csv rows == jsonl, header OK, {len(sample)}/5 random spot-checks matched")


# --------------------------------------------------------------------------- #
# 4. state.json shape + seen-entry histogram
# --------------------------------------------------------------------------- #
def check4():
    p = deals_mod.STATE_JSON
    if not p.exists():
        fail_short(4, "state.json", f"missing {p}")
        return
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        fail_short(4, "state.json", f"not valid json: {e}")
        return
    if not isinstance(data, dict) or "seen" not in data or not isinstance(data["seen"], list):
        fail_short(4, "state.json", "missing/odd 'seen' array")
        return

    seen = data["seen"]
    bare = tb = junk = 0
    for v in seen:
        if isinstance(v, str) and v.isdigit():
            bare += 1
        elif isinstance(v, str) and v.startswith("tb:"):
            tb += 1
        else:
            junk += 1
    record(4, "state.json", True,
           f"'seen' len={len(seen)} — numeric:{bare} tb-prefixed:{tb} junk/other:{junk}")


# --------------------------------------------------------------------------- #
# 5. CLI smoke via subprocess (read-only subcommands; viz only writes its PNGs)
# --------------------------------------------------------------------------- #
CLI_SMOKE = [
    ("deals", ["deals", "--top", "3"], "reads data/ only"),
    ("viz", ["viz", "--png"], "WRITES 3 PNGs into data/ (normal viz behavior)"),
    ("schedule", ["schedule", "list"], "launchctl print, read-only"),
    ("js-plan", ["js-plan", "--top", "2"], "prints cart JS, read-only"),
]


def check5():
    env = dict(os.environ)
    env["PYTHONPATH"] = "."
    all_ok = True
    for name, argv, note in CLI_SMOKE:
        if name == "viz":
            print(f"[5]   NOTE: `wob {argv[0]} --png` {note}")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "wob", *argv],
                cwd=str(REPO), env=env,
                capture_output=True, text=True, timeout=240,
            )
        except subprocess.TimeoutExpired:
            print(f"[5]   sub-check: wob {' '.join(argv):28s} TIMEOUT")
            all_ok = False
            continue
        ok = proc.returncode == 0
        all_ok &= ok
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        last = tail[-1].strip() if tail else ""
        print(f"[5]   sub-check: wob {' '.join(argv):28s} exit={proc.returncode}  last: {last[:60]}")
    record(5, "cli smoke", all_ok, "4 subcommands" if all_ok else "at least one subcommand failed")


# --------------------------------------------------------------------------- #
# 6. Scan-seen simulation (offline) — monkeypatched network fakes + temp DATA_DIR
# --------------------------------------------------------------------------- #
def fake_iter_search_results(query, max_pages, max_hits, on_progress=None):
    hits = [
        {
            "id": "P1",
            "handle": "p1-good-book",
            "meta": {
                "author": "Ann Author",
                "shortTitle": "The Good Book",
                "listPriceUs": None,
                "rrp": None,
                "isbn13": "",
                "publisher": "Sim Press",
                "yearPublished": "2024",
                "availableConditions": ["NEW", "GOOD"],
                "inStock": True,
            },
        },
        {
            "id": "P2",
            "handle": "p2-no-stock",
            "meta": {
                "availableConditions": ["NEW", "GOOD"],
                "inStock": False,  # structural skip: seen must NOT be marked
            },
        },
        {
            "id": "P3",
            "handle": "p3-boom",
            "meta": {
                "availableConditions": ["NEW", "GOOD"],
                "inStock": True,
            },  # fetch_product raises: seen must NOT be marked
        },
        {
            "id": "P4",
            "handle": "p4-new-only",
            "meta": {
                "availableConditions": ["NEW", "VERY_GOOD"],
                "inStock": True,
            },  # fetch OK, no used candidate: seen YES, deal NO
        },
    ]
    for h in hits:
        yield h


def fake_fetch_product(handle):
    if handle == "p3-boom":
        raise RuntimeError("simulated fetch failure")
    if handle == "p1-good-book":
        return {
            "id": "P1",
            "title": "The Good Book",
            "handle": "p1-good-book",
            "variants": [
                {"id": 1001, "option2": "NEW", "price": 3000, "available": True,
                 "option3": "", "option1": "US", "barcode": ""},
                {"id": 1002, "option2": "GOOD", "price": 600, "available": True,
                 "option3": "EXL", "option1": "US", "barcode": ""},
            ],
        }
    if handle == "p4-new-only":
        return {
            "id": "P4",
            "title": "New Only",
            "handle": "p4-new-only",
            "variants": [
                {"id": 2001, "option2": "NEW", "price": 3000, "available": True,
                 "option3": "", "option1": "US", "barcode": ""},
            ],
        }
    raise RuntimeError("unexpected handle: " + handle)


def fake_tb_search(query, max_pages, per_page=50):
    return [
        {
            "id": "444",
            "url": "https://www.thriftbooks.com/w/fake-tb-book/444/",
            "meta": {
                "id": "444",
                "title": "Fake TB Book",
                "authors": "Tim Author",
                "lowPrice": 5.0,
                "listPrice": 30.0,
                "availableCopies": 2,
                "isbn": "",
            },
        },
        {
            "id": "555",
            "url": "https://www.thriftbooks.com/w/fake-tb-boom/555/",
            "meta": {
                "id": "555",
                "title": "Fake TB Boom",
                "authors": "Tim Author",
                "listPrice": 30.0,
                "availableCopies": 1,
                "isbn": "",
            },
        },
        {
            "id": "666",
            "url": "https://www.thriftbooks.com/w/fake-tb-none/666/",
            "meta": {
                "id": "666",
                "title": "Fake TB None",
                "authors": "Tim Author",
                "listPrice": 30.0,
                "availableCopies": 0,
                "isbn": "",
            },
        },
    ]


def fake_tb_analyze(url, min_off, meta):
    if url.endswith("/555/"):
        raise RuntimeError("simulated tb analyze failure")
    return {
        "site": "tb",
        "product_id": meta.get("id", ""),
        "title": meta.get("title", ""),
        "author": meta.get("authors", ""),
        "handle": "fake-tb-book",
        "variant_id": "",
        "condition": "GOOD",
        "source": "",
        "country": "",
        "used_price": 5.0,
        "new_price": 30.0,
        "pct_off": 0.8333,
        "barcode": "",
        "isbn13": meta.get("isbn", ""),
        "publisher": "",
        "list_price_us": meta.get("listPrice"),
        "rrp": None,
        "format": "Paperback",
        "url": url,
        "quality": False,
    }


def check6():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="wob_verify_sim_", dir=str(pathlib.Path(__file__).parent)))
    try:
        deals_mod.DATA_DIR = tmp
        deals_mod.DEALS_JSONL = tmp / "deals.jsonl"
        deals_mod.DEALS_CSV = tmp / "deals.csv"
        deals_mod.STATE_JSON = tmp / "state.json"

        cli.iter_search_results = fake_iter_search_results
        cli.fetch_product = fake_fetch_product
        cli.tb_search = fake_tb_search
        cli.tb_analyze = fake_tb_analyze
        cli.polite_wait = lambda *a, **k: None  # no network, no need to sleep

        args = SimpleNamespace(
            term="sim-term", keywords="keywords.txt", sites="wob,tb",
            fresh=False, pages=1, max_hits=400, min_off=0.70,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli._scan_locked(args)
        out = buf.getvalue()

        seen = set(json.loads(deals_mod.STATE_JSON.read_text(encoding="utf-8"))["seen"])
        wrote_lines = [
            l for l in deals_mod.DEALS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()
        ]

        problems = []
        for expect_in, label in [
            ("P1", "wob success"), ("P4", "wob success-no-deal"), ("tb:444", "tb success"),
        ]:
            if expect_in not in seen:
                problems.append(f"{label} ({expect_in}) not marked seen")
        for expect_out, label in [
            ("P3", "wob exception"), ("P2", "wob out-of-stock skip"), ("tb:555", "tb exception"),
            ("tb:666", "tb no-copies skip"),
        ]:
            if expect_out in seen:
                problems.append(f"{label} ({expect_out}) wrongly marked seen")
        if len(wrote_lines) != 2:
            problems.append(f"append wrote {len(wrote_lines)} lines, expected 2")
        if "2 new deals" not in out or "books tracked" not in out:
            problems.append(f"summary line wrong: {out.strip().splitlines()[-1]!r}")

        if problems:
            fail_short(6, "scan-seen simulation", "; ".join(problems))
            return
        record(6, "scan-seen simulation", True,
               "seen marks correct (2 successes scored, 4 failures left retryable), "
               "append count honest (2 lines written == 2 reported)")
    finally:
        # monkeypatches intentionally left in place (in-process only, nothing restored)
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 7. Empty-data viz must exit cleanly with a message
# --------------------------------------------------------------------------- #
def check7():
    deals_mod.DEALS_JSONL = pathlib.Path(pathlib.Path(__file__).parent) / "wob_verify_no_such_deals.jsonl"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        viz.cmd_viz(SimpleNamespace(png=True, top=15))
    out = buf.getvalue()
    if "no deals yet" not in out:
        fail_short(7, "empty viz", f"unexpected output: {out.strip()[:100]!r}")
        return
    record(7, "empty viz", True, 'printed "no deals yet ... nothing to chart" and returned')
    # DEALS_JSONL left patched in-place; check 6 runs next and installs its own temp paths


def main():
    print("=" * 72)
    print("wob_verify — read-only verification of WorldofBooks repo data")
    print(f"repo:    {REPO}")
    print(f"python:  {sys.executable} ({sys.version.split()[0]})")
    print(f"harness: {pathlib.Path(__file__).resolve()}")
    print("-" * 72)
    print("future run command (any cwd):")
    print(f"  {sys.executable} {pathlib.Path(__file__).resolve()}")
    print("-" * 72)

    check1()   # JSONL integrity
    check2()   # dedupe
    check3()   # CSV sync
    check4()   # state.json histogram
    check5()   # CLI smoke (subprocess)
    check7()   # empty viz  (patches DEALS_JSONL, no restore)
    check6()   # scan sim   (re-patches DEALS_JSONL to temp dir, no restore)

    passed = sum(1 for _, _, ok in RESULTS if ok)
    total = len(RESULTS)
    print("-" * 72)
    for num, name, ok in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  [{num}] {name}")
    print(f"SUMMARY: {passed}/{total} checks passed")
    rel = getattr(sys.modules[__name__], "RELAXED_CHECKS", [])
    if rel:
        print("RELAXED: " + "; ".join(rel))
    print("=" * 72)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()