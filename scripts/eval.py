#!/usr/bin/env python3.13
"""eval.py — regression benchmark runner (Milestone 0 seed).

Runs the deterministic verification suites and records a versioned results
row to docs/evals/benchmark-history.jsonl (append-only). Suites now:
  harness   -> scripts/wob_verify.py (7 integrity checks)
  unit      -> unittest discover tests/ (schema/config/dedupe)
Exit 0 when all suites pass. No network, no live sites.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PY = REPO / ".venv" / "bin" / "python3.13"
HIST = REPO / "docs" / "evals" / "benchmark-history.jsonl"


def run(name, cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {"name": name, "ok": r.returncode == 0,
            "rc": r.returncode, "tail": (r.stdout or r.stderr).strip()[-300:]}


def main():
    suites = [
        ("harness", [str(PY), "scripts/wob_verify.py"]),
        ("unit", [str(PY), "-m", "unittest", "discover", "-s", "tests"]),
    ]
    results = [run(n, c, str(REPO)) for n, c in suites]
    ok = all(r["ok"] for r in results)
    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "rc": 0 if ok else 1,
        "suites": [{k: r[k] for k in ("name", "ok", "rc")} for r in results],
    }
    HIST.parent.mkdir(parents=True, exist_ok=True)
    with open(HIST, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    for r in results:
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['name']}")
        if not r["ok"]:
            print("   ", r["tail"][:200])
    print(f"recorded -> {HIST}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()