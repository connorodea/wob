"""M2 resolver tests — deterministic golden cases, no network."""

import unittest

from wob import resolver as R


def B(title, author, **kw):
    d = {"title": title, "author": author}
    d.update(kw)
    return d


class TestExact(unittest.TestCase):
    def test_same_isbn13(self):
        r = R.resolve(
            B("Deep Learning", "Ian Goodfellow", isbn13="9780262035613"),
            B("Deep Learning", "Ian Goodfellow", isbn13="9780262035613"),
        )
        self.assertEqual(r["class"], "exact")
        self.assertEqual(r["confidence"], 1.0)

    def test_isbn10_cross(self):
        r = R.resolve(
            B("Deep Learning", "Ian Goodfellow", isbn13="9780262035613"),
            B("Deep Learning", "Ian Goodfellow", isbn10="0262035618"),
        )
        self.assertEqual(r["class"], "exact")


class TestIncompatible(unittest.TestCase):
    def test_different_isbns_same_work_is_compatible(self):
        # editions of the same work share no ISBN — R3 falls back to work identity
        r = R.resolve(
            B("Deep Learning", "Ian Goodfellow", isbn13="9780262035613"),
            B("Deep Learning", "Ian Goodfellow", isbn13="9780596516499"),
        )
        self.assertEqual(r["class"], "compatible")

    def test_different_isbns_different_work(self):
        r = R.resolve(
            B("Deep Learning", "Ian Goodfellow", isbn13="9780262035613"),
            B("Natural Language Processing with Python", "Steven Bird", isbn13="9780596516499"),
        )
        self.assertEqual(r["class"], "incompatible")

    def test_similar_titles_different_books(self):
        r = R.resolve(
            B("Machine Learning", "Tom Mitchell"), B("Machine Learning for Hackers", "Drew Conway")
        )
        self.assertEqual(r["class"], "incompatible")


class TestCompatible(unittest.TestCase):
    def test_edition_variant_no_isbn(self):
        r = R.resolve(
            B("Pattern Recognition and Machine Learning", "Christopher Bishop"),
            B("Pattern Recognition and Machine Learning", "Christopher M. Bishop"),
        )
        self.assertEqual(r["class"], "compatible")


class TestUncertain(unittest.TestCase):
    def test_partial_overlap(self):
        r = R.resolve(
            B("The Elements of Statistical Learning", "Hastie"),
            B("Statistical Learning with Sparsity", "Hastie"),
        )
        self.assertEqual(r["class"], "uncertain")

    def test_missing_metadata(self):
        r = R.resolve(B("", ""), B("", ""))
        self.assertEqual(r["class"], "uncertain")


class TestShape(unittest.TestCase):
    def test_result_contract(self):
        r = R.resolve(B("x", "y"), B("x", "y"))
        for k in ("class", "confidence", "explanation", "evidence"):
            self.assertIn(k, r)
        self.assertIn(r["class"], {"exact", "compatible", "incompatible", "uncertain"})
        self.assertIsInstance(r["confidence"], float)


if __name__ == "__main__":
    unittest.main()
