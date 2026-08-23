"""M4 profile + affinity tests — deterministic, no network."""

import unittest

from wob import profile as P


class TestProfile(unittest.TestCase):
    def test_build_validates(self):
        p = P.build_profile(
            "u1",
            ["machine learning", "causal inference"],
            favored_authors=["Judea Pearl"],
            min_condition="VERY_GOOD",
            budget_cents=5000,
        )
        self.assertEqual(p.min_condition, "VERY_GOOD")
        self.assertEqual(p.budget_cents, 5000)

    def test_bad_min_condition(self):
        with self.assertRaises(ValueError):
            P.build_profile("u1", ["x"], min_condition="MINT")

    def test_empty_profile_valid(self):
        P.build_profile("u2", []).validate()


class TestAffinity(unittest.TestCase):
    def test_interest_hit(self):
        p = P.build_profile("u1", ["reinforcement learning"])
        score, reasons = P.affinity(p, "Reinforcement Learning: An Introduction", "Richard Sutton")
        self.assertGreater(score, 0.4)
        self.assertTrue(any("reinforcement learning" in r for r in reasons))

    def test_author_hit(self):
        p = P.build_profile("u1", ["ml"], favored_authors=["Judea Pearl"])
        score, reasons = P.affinity(p, "The Book of Why", "Judea Pearl")
        self.assertGreater(score, 0.4)
        self.assertTrue(any("author" in r for r in reasons))

    def test_miss_floor(self):
        p = P.build_profile("u1", ["quantum computing"])
        score, reasons = P.affinity(p, "Floral Arrangements for Beginners", "Jane Doe")
        self.assertAlmostEqual(score, 0.2)
        self.assertEqual(reasons, [])

    def test_score_bounds(self):
        p = P.build_profile("u1", ["data science", "statistics", "python"])
        for title, author in [
            ("Python Data Science Handbook", "Jake VanderPlas"),
            ("Linear Algebra Done Right", "Sheldon Axler"),
        ]:
            score, _ = P.affinity(p, title, author)
            self.assertTrue(0.0 <= score <= 1.0)


if __name__ == "__main__":
    unittest.main()
