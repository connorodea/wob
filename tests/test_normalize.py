"""Deterministic normalizer tests — golden cases, no network."""

import unittest

from wob import normalize as N


class TestTitles(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(N.normalize_title("  The Great  BOOK "), "the great book")

    def test_subtitle_stripped(self):
        self.assertEqual(
            N.normalize_title("Deep Learning: Adaptive Computation and ML"),
            "deep learning",
        )

    def test_no_colon_kept(self):
        self.assertEqual(N.normalize_title("C++ Primer"), "c++ primer")

    def test_accents_folded(self):
        self.assertEqual(N.normalize_title("Éléments d'analyse"), "elements d'analyse")

    def test_empty(self):
        self.assertEqual(N.normalize_title("   "), "")


class TestAuthors(unittest.TestCase):
    def test_last_first(self):
        self.assertEqual(N.normalize_author("Goodfellow, Ian"), "ian goodfellow")

    def test_first_last(self):
        self.assertEqual(N.normalize_author("Ian Goodfellow"), "ian goodfellow")

    def test_multi_reversed(self):
        self.assertEqual(
            N.normalize_author("Cormen, Thomas H., Leiserson, Charles E."),
            "charles e. leiserson thomas h. cormen",
        )


class TestPublishers(unittest.TestCase):
    def test_strips_legal(self):
        self.assertEqual(
            N.normalize_publisher("O'Reilly Media, Inc."), "o'reilly media"
        )

    def test_empty(self):
        self.assertEqual(N.normalize_publisher(""), "")


class TestFormats(unittest.TestCase):
    def test_map(self):
        self.assertEqual(N.normalize_format("Mass Market Paperback"),
                         "mass_market_paperback")
        self.assertEqual(N.normalize_format("Kindle Edition"), "ebook")
        self.assertEqual(N.normalize_format("Hardcover"), "hardcover")
        self.assertEqual(N.normalize_format("Audible Audio"), "audiobook")
        self.assertEqual(N.normalize_format("weird"), "unknown")


class TestLanguages(unittest.TestCase):
    def test_map(self):
        self.assertEqual(N.normalize_language("English"), "en")
        self.assertEqual(N.normalize_language("Français"), "fr")
        self.assertEqual(N.normalize_language("Klingon"), "klingon")


class TestDates(unittest.TestCase):
    def test_year(self):
        self.assertEqual(N.normalize_publication_date("2022"), (2022, None, None))

    def test_iso(self):
        self.assertEqual(N.normalize_publication_date("2020-05-14"), (2020, 5, 14))

    def test_slash(self):
        self.assertEqual(N.normalize_publication_date("05/14/2020"), (2020, 5, 14))

    def test_month_year(self):
        self.assertEqual(N.normalize_publication_date("May 2020"), (2020, 5, None))

    def test_day_month_year(self):
        self.assertEqual(N.normalize_publication_date("14 May 2020"), (2020, 5, 14))

    def test_garbage(self):
        self.assertEqual(N.normalize_publication_date("nope"), (None, None, None))


class TestCurrency(unittest.TestCase):
    def test_map(self):
        self.assertEqual(N.normalize_currency("$"), "USD")
        self.assertEqual(N.normalize_currency("pounds"), "GBP")

    def test_usd_cents_no_conversion(self):
        self.assertEqual(N.to_usd_cents(12.5, "USD", None), 1250)

    def test_conversion_with_hint(self):
        self.assertEqual(N.to_usd_cents(10, "GBP", {"GBP": 1.25}), 1250)

    def test_no_hint_returns_none(self):
        self.assertIsNone(N.to_usd_cents(10, "GBP", None))
        self.assertIsNone(N.to_usd_cents(10, "INR", {"GBP": 1.25}))


if __name__ == "__main__":
    unittest.main()