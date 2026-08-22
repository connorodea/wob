"""Milestone 0: versioned-schema marker on persisted deal records."""

import json
import pathlib
import tempfile
import unittest

from wob import deals as D
from wob.entities import SCHEMA_VERSION


class TestSchemaMarker(unittest.TestCase):
    def test_append_writes_schema(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            D.DATA_DIR = td
            D.DEALS_JSONL = td / "deals.jsonl"
            D.STATE_JSON = td / "state.json"
            D.DEALS_CSV = td / "deals.csv"
            D.HISTORY_JSONL = td / "history.jsonl"
            D.append_deals([{
                "site": "wob", "product_id": "P1", "isbn13": "9780000000002",
                "title": "T", "used_price": 1.0, "new_price": 10.0,
                "pct_off": 0.9, "condition": "GOOD",
            }])
            row = json.loads((td / "deals.jsonl").read_text().splitlines()[0])
            self.assertEqual(row["_schema"], SCHEMA_VERSION)

    def test_dedupe_keeps_first_schema(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            D.DATA_DIR = td
            D.DEALS_JSONL = td / "deals.jsonl"
            D.STATE_JSON = td / "state.json"
            D.DEALS_CSV = td / "deals.csv"
            D.HISTORY_JSONL = td / "history.jsonl"
            rec = {"site": "wob", "product_id": "P1", "isbn13": "9780000000002",
                   "title": "T", "used_price": 1.0, "new_price": 10.0,
                   "pct_off": 0.9, "condition": "GOOD"}
            D.append_deals([rec])
            D.append_deals([rec])
            lines = (td / "deals.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()