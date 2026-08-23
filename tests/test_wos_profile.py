"""Profile-aware WOS + recommendation wiring tests (offline)."""

import unittest

from wob import scoring as S
from wob.profile import build_profile
from wob.recommend import recommend_for_profile


def _rows():
    return [
        {
            "title": "Reinforcement Learning: An Introduction",
            "author": "Sutton",
            "used_price": 12.0,
            "pct_off": 0.8,
            "condition": "VERY_GOOD",
            "quality": False,
            "stock": 2,
            "site": "wob",
            "url": "",
        },
        {
            "title": "Floral Arrangements for Beginners",
            "author": "J. Doe",
            "used_price": 4.0,
            "pct_off": 0.9,
            "condition": "GOOD",
            "quality": False,
            "stock": 1,
            "site": "wob",
            "url": "",
        },
        {
            "title": "Bandit Algorithms",
            "author": "Lattimore",
            "used_price": 25.0,
            "pct_off": 0.75,
            "condition": "LIKE_NEW",
            "quality": True,
            "stock": 3,
            "site": "wob",
            "url": "",
        },
    ]


class TestProfileAwareWos(unittest.TestCase):
    def test_profile_relevance_changes_ranking(self):
        p = build_profile("u", ["reinforcement learning"], favored_authors=["Lattimore"])
        out = S.compute_deal_scores(_rows(), profile=p)
        top2 = {r["title"] for r, _ in out[:2]}
        self.assertEqual(
            top2,
            {"Reinforcement Learning: An Introduction", "Bandit Algorithms"},
        )
        self.assertEqual(out[-1][0]["title"], "Floral Arrangements for Beginners")
        expl = out[0][1].explanation.lower()
        self.assertTrue("interest" in expl or "favor" in expl)

    def test_no_profile_falls_back_to_quality_proxy(self):
        out = S.compute_deal_scores(_rows())
        self.assertEqual(out[0][0]["title"], "Bandit Algorithms")


class TestRecommendForProfile(unittest.TestCase):
    def test_profile_recommendations(self):
        p = build_profile(
            "u", ["reinforcement learning", "control theory"], favored_authors=["Lattimore"]
        )
        rows = _rows()
        recs = recommend_for_profile(p, top=3, rows=rows)
        self.assertEqual(len(recs), 2)  # floral is filtered at affinity < 0.4
        self.assertEqual(recs[0]["title"], "Reinforcement Learning: An Introduction")
        self.assertTrue(recs[0]["reasons"])
        self.assertEqual(recs[1]["title"], "Bandit Algorithms")
        self.assertTrue(any("favor" in r for r in recs[1]["reasons"]))


if __name__ == "__main__":
    unittest.main()
