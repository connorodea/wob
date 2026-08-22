"""Milestone 0 schema tests — deterministic, no network, stdlib only.

Run: .venv/bin/python3.13 -m unittest discover -s tests
"""

import unittest

from wob import entities as E


def base_offer(**kw):
    d = dict(
        offer_id="o1",
        edition_id="e1",
        seller_id="s1",
        condition="GOOD",
        price_cents=500,
        currency="USD",
        shipping_cents=0,
        url="https://x/1",
        source="wob",
        retrieved_at="2026-08-23T00:00:00Z",
        landed_cost_cents=500,
    )
    d.update(kw)
    return d


class TestBookIdentifier(unittest.TestCase):
    def test_valid_isbn13(self):
        e = E.BookIdentifier(kind="isbn13", value="9780596516499", primary=True)
        e.validate()

    def test_bad_isbn13(self):
        with self.assertRaises(ValueError):
            E.BookIdentifier(kind="isbn13", value="978059651649X", primary=True).validate()

    def test_isbn10(self):
        E.BookIdentifier(kind="isbn10", value="0596516497", primary=False).validate()

    def test_roundtrip(self):
        e = E.BookIdentifier(kind="isbn13", value="9780596516499", primary=True)
        d = e.to_dict()
        self.assertEqual(d["_type"], "BookIdentifier")
        self.assertEqual(E.BookIdentifier.from_dict(d), e)


class TestBookOffer(unittest.TestCase):
    def test_valid(self):
        E.BookOffer(**base_offer()).validate()

    def test_unknown_condition(self):
        with self.assertRaises(ValueError):
            E.BookOffer(**base_offer(condition="MINT")).validate()

    def test_unknown_currency(self):
        with self.assertRaises(ValueError):
            E.BookOffer(**base_offer(currency="CAD")).validate()

    def test_negative_price(self):
        with self.assertRaises(ValueError):
            E.BookOffer(**base_offer(price_cents=-1)).validate()

    def test_roundtrip_preserves_landed_cost(self):
        e = E.BookOffer(**base_offer(price_cents=400, shipping_cents=150, landed_cost_cents=550))
        self.assertEqual(E.BookOffer.from_dict(e.to_dict()), e)


class TestConditionAssessment(unittest.TestCase):
    def test_canonical_set(self):
        for c in E.CANONICAL_CONDITIONS:
            E.ConditionAssessment(condition=c, source_vocabulary=None, confidence=None).validate()

    def test_confidence_bounds(self):
        with self.assertRaises(ValueError):
            E.ConditionAssessment(
                condition="GOOD", source_vocabulary="Very Good", confidence=1.5
            ).validate()


class TestReadingList(unittest.TestCase):
    def test_valid(self):
        E.ReadingList(
            list_id="l1",
            user_id="u1",
            title="cs229",
            items=[
                {"book": "PRML", "required": "required"},
                {"book": "ISLR", "required": "recommended"},
            ],
        ).validate()

    def test_bad_requirement_level(self):
        with self.assertRaises(ValueError):
            E.ReadingList(
                list_id="l1", user_id="u1", title="t", items=[{"book": "x", "required": "maybe"}]
            ).validate()


class TestPurchasePolicy(unittest.TestCase):
    def test_default_mode(self):
        p = E.PurchasePolicy(
            policy_id="p1",
            user_id="u1",
            mode="recommend_only",
            budget_monthly_cents=0,
            seller_allowlist=[],
            seller_blocklist=[],
            min_condition="GOOD",
        )
        p.validate()

    def test_autonomous_requires_budget(self):
        with self.assertRaises(ValueError):
            E.PurchasePolicy(
                policy_id="p1",
                user_id="u1",
                mode="autonomous_within_policy",
                budget_monthly_cents=0,
                seller_allowlist=[],
                seller_blocklist=[],
                min_condition="GOOD",
            ).validate()

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            E.PurchasePolicy(
                policy_id="p1",
                user_id="u1",
                mode="yolo",
                budget_monthly_cents=0,
                seller_allowlist=[],
                seller_blocklist=[],
                min_condition="GOOD",
            ).validate()


class TestOpportunityScore(unittest.TestCase):
    def test_valid(self):
        E.OpportunityScore(
            score=0.81,
            inputs={"pct_off": 0.9},
            explanation="90% off, high relevance",
            computed_at="2026-08-23T00:00:00Z",
        ).validate()

    def test_requires_explanation(self):
        with self.assertRaises(ValueError):
            E.OpportunityScore(score=0.5, inputs={}, explanation="   ", computed_at="x").validate()


class TestProvenance(unittest.TestCase):
    def test_valid(self):
        E.PredictionProvenance(
            pred_id="x1",
            model_id="resolver-v1",
            model_version="1.2",
            inputs_hash="a" * 12,
            dataset_ref=None,
            run_id=None,
        ).validate()

    def test_short_hash(self):
        with self.assertRaises(ValueError):
            E.PredictionProvenance(
                pred_id="x1",
                model_id="m",
                model_version="1",
                inputs_hash="abc",
                dataset_ref=None,
                run_id=None,
            ).validate()


class TestUserProfileAndWatchlist(unittest.TestCase):
    def test_profile(self):
        E.UserProfile(
            user_id="u1",
            interests=["ml"],
            favored_authors=[],
            min_condition="VERY_GOOD",
            budget_cents=10000,
        ).validate()

    def test_watchlist(self):
        E.Watchlist(
            watch_id="w1",
            user_id="u1",
            edition_id="e1",
            target_price_cents=800,
            min_condition="GOOD",
            active=True,
        ).validate()


if __name__ == "__main__":
    unittest.main()
