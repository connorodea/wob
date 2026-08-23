"""Watchlist tests — deterministic, hermetic (temp data dir), no network."""

import pathlib
import tempfile
import unittest
from unittest import mock

from wob import watch as W


class TestWatchlist(unittest.TestCase):
    def setUp(self):
        self.td = pathlib.Path(tempfile.mkdtemp())
        patcher = mock.patch.object(W, "WATCH_FILE", self.td / "watchlist.jsonl")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_add_requires_valid_isbn(self):
        with self.assertRaises(ValueError):
            W.add("u", "not-an-isbn")

    def test_add_duplicate_returns_none(self):
        e = W.add("u", "9780596516499")
        self.assertIsNotNone(e)
        self.assertIsNone(W.add("u", "9780596516499"))

    def test_remove_by_isbn(self):
        W.add("u", "9780596516499")
        W.add("u", "9780387310732")
        self.assertEqual(W.remove("9780596516499"), 1)
        self.assertEqual(len(W.load_all()), 1)

    def test_check_matches_and_signals(self):
        W.add("u", "9780262035613", target_price_cents=5000)
        rows = [
            {"isbn13": "9780262035613", "used_price": 4.99, "condition": "GOOD", "url": ""},
            {"isbn13": "9780262035613", "used_price": 7.99, "condition": "VERY_GOOD", "url": ""},
            {"isbn13": "9780262035613", "used_price": 9.99, "condition": "NEW", "url": ""},
            {"isbn13": "9999999999999", "used_price": 2.0, "condition": "GOOD", "url": ""},
        ]
        hits = W.check(rows)
        self.assertEqual(len(hits), 1)
        h = hits[0]
        self.assertTrue(h["found"])
        self.assertEqual(h["price"], 4.99)
        self.assertTrue(h["within_budget"])

    def test_check_missing(self):
        W.add("u", "9780262035613")
        hits = W.check([])
        self.assertEqual(hits[0]["found"], False)

    def test_over_budget_flagged(self):
        W.add("u", "9780262035613", target_price_cents=100)
        rows = [{"isbn13": "9780262035613", "used_price": 4.99, "condition": "GOOD", "url": ""}]
        h = W.check(rows)[0]
        self.assertFalse(h["within_budget"])

    def test_corrupt_line_tolerated(self):
        W.WATCH_FILE.write_text('{"broken": true\n' + "")
        self.assertEqual(W.load_all(), [])


if __name__ == "__main__":
    unittest.main()
