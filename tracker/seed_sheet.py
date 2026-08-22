#!/usr/bin/env python3
"""One-shot: seed the wob tracker spreadsheet Milestones + Metrics tabs."""

import json
import os
import pathlib
import subprocess
import urllib.request

SHEETS_URL = "https://sheets.googleapis.com/v4/spreadsheets"


def sheet_id():
    env = os.environ.get("WOB_TRACKER_SHEET_ID")
    if env:
        return env
    p = pathlib.Path.home() / ".wob_tracker_sheet_id"
    if p.exists():
        return p.read_text().strip()
    raise SystemExit("no sheet id")


def gaccess():
    tok = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True, text=True, check=True).stdout.strip()
    return f"Bearer {tok}"


def put(sid, rng, rows):
    req = urllib.request.Request(
        f"{SHEETS_URL}/{sid}/values/{rng}", method="PUT",
        headers={"Authorization": gaccess(), "Content-Type": "application/json"},
        data=json.dumps({"majorDimension": "ROWS", "values": rows}).encode())
    with urllib.request.urlopen(req) as r:
        return json.load(r)


MILESTONES = [
    ["Milestone", "Name", "Status", "Key gaps", "Next actions"],
    ["M0", "Reproducible foundation", "Partial",
     "no typed config/schemas/lint; fixture tests missing",
     "pyproject+config validation; domain entities; CI test/lint/typecheck"],
    ["M1", "Canonical book + offer pipeline", "Partial",
     "no landed cost, currency norm, full provenance, health reporting",
     "provenance fields; landed cost; connector health; snapshot schema v2"],
    ["M2", "Book & edition entity resolution", "Partial",
     "exact ISBN + token-title only; no calibration/abstention/labeled data",
     "labeled match fixtures; calibrated resolver w/ abstention"],
    ["M3", "Deal intelligence + WOS v1", "Partial",
     "pct_off/history/alerts exist; no fair-value model or WOS",
     "WOS v1 scoring fn w/ explanations; fair-price quantiles; eval vs lowest-price"],
    ["M4", "Personalized recommendations", "Partial",
     "content sim + discount boost; no profile/signals/evals",
     "cold-start onboarding; profile store; Precision/NDCG offline evals"],
    ["M5", "Reading-list + semester optimization", "Partial",
     "parse+match exist; no req classification/substitution/optimizer",
     "required-vs-optional classes; edition-substitution; deterministic basket optimizer"],
    ["M6", "Monitoring, alerts, agentic safeguards", "Partial",
     "track/history/alerts/throttle exist; no purchase modes/policies",
     "policy entities + modes (default recommend_only); dry-run path"],
    ["M7", "Adaptive personalization", "Deferred", "no interaction data",
     "contextual bandits only after M4 data exists"],
    ["M8", "Institutional & market intelligence", "Deferred", "needs real usage",
     "aggregates; backtested forecasts; B2B separation"],
    ["M9", "Production ML operations", "Deferred", "usage not justified",
     "model registry/evals/drift when scale demands"],
]

METRICS = [
    ["Area", "Metric", "Target", "Current", "Measured in"],
    ["Matching", "exact-edition precision (non-abstained)", ">= 98%", "n/a (crude matcher)",
     "M2 eval suite"],
    ["Matching", "false-substitution rate", "0 silent", "partial (dedupe by ISBN only)",
     "M2 eval"],
    ["Deals", "fair-price MAE / interval coverage", "TBD baseline first", "n/a",
     "M3 backtest"],
    ["Deals", "top-K deal ranking (WOS vs lowest-price)", "WOS > baseline", "n/a",
     "M3 labeled set"],
    ["Deals", "savings as landed cost", "reported", "sticker-price only today",
     "M1 landed-cost fn"],
    ["Recommender", "Precision@K / NDCG@K", "> content baseline", "n/a",
     "M4 offline eval"],
    ["Recommender", "novelty, diversity, coverage", "recorded", "n/a",
     "M4 eval"],
    ["Reading lists", "extraction accuracy", "flagged uncertain", "basic parse",
     "M5 fixtures"],
    ["Reading lists", "constraint-violation rate", "0", "n/a", "M5 optimizer"],
    ["Agent", "policy-violation / dup / unauthorized purchases", "0 (hard)", "no executor",
     "M6 audits"],
]


def main():
    sid = sheet_id()
    put(sid, "Milestones!A1", MILESTONES)
    put(sid, "Metrics!A1", METRICS)
    print(f"seeded {sid}")


if __name__ == "__main__":
    main()