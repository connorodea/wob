"""WOS v1 scoring tests — deterministic golden cases, no network."""

import unittest

from wob import scoring as S


def base(**kw):
    d = dict(
        relevance=0.9,
        discount=0.9,
        condition="VERY_GOOD",
        match_confidence=0.95,
        landed_cents=800,
        stock=5,
        budget_cents=2500,
    )
    d.update(kw)
    return S.wos_v1(**d)


class TestWosV1(unittest.TestCase):
    def test_score_bounds(self):
        for kwargs in (
            {},
            {"discount": 1.5},
            {"budget_cents": 1},
            {"relevance": 2.0},
            {"condition": "ACCEPTABLE"},
            {"stock": None},
        ):
            r = base(**kwargs)
            r.validate()
            self.assertTrue(0.0 <= r.score <= 1.0)

    def test_versioned_and_explained(self):
        r = base()
        self.assertEqual(r.version, S.WOS_VERSION)
        self.assertIn("relevance", r.explanation)
        self.assertIn("budget fit", r.explanation)

    def test_cheap_but_irrelevant_scores_lower(self):
        great = base()
        meh = base(relevance=0.1, match_confidence=0.2)
        self.assertGreater(great.score, meh.score)

    def test_bad_condition_penalized(self):
        good = base(condition="NEW")
        bad = base(condition="ACCEPTABLE")
        self.assertGreater(good.score, bad.score)

    def test_over_budget_capped(self):
        ok = base(landed_cents=2000, budget_cents=2500)
        over = base(landed_cents=6000, budget_cents=2500)
        self.assertGreater(ok.score, over.score)
        self.assertLessEqual(over.score, 0.8)

    def test_low_stock_scores_higher(self):
        scarce = base(stock=2)
        common = base(stock=500)
        self.assertGreater(scarce.score, common.score)


class TestComputeDealScores(unittest.TestCase):
    def _row(self, **kw):
        d = {
            "title": "T",
            "used_price": 5.0,
            "pct_off": 0.9,
            "condition": "VERY_GOOD",
            "quality": False,
        }
        d.update(kw)
        return d

    def test_sorted_desc(self):
        rows = [
            self._row(title="cheap", used_price=1.0),
            self._row(title="curated", used_price=3.0, quality=True, stock=2),
        ]
        out = S.compute_deal_scores(rows)
        self.assertEqual(out[0][0]["title"], "curated")
        self.assertGreaterEqual(out[0][1].score, out[1][1].score)

    def test_budget_penalty(self):
        row = self._row(used_price=80.0, quality=True)
        a = S.compute_deal_scores([row], budget_cents=2000)[0][1]
        b = S.compute_deal_scores([row], budget_cents=20000)[0][1]
        self.assertGreater(b.score, a.score)

    def test_skips_bad_rows(self):
        self.assertEqual(S.compute_deal_scores([{"title": "no prices"}]), [])


if __name__ == "__main__":
    unittest.main()
