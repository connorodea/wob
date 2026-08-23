"""Fair-price estimator tests — deterministic, synthetic offer history."""

import unittest

from wob import fairprice as F


def offers(*prices, condition="GOOD"):
    return [{"condition": condition, "price_cents": p} for p in prices]


class TestFairPrice(unittest.TestCase):
    def test_median_and_quartiles(self):
        fair = F.fair_price_cents(offers(100, 200, 300, 400, 500), "GOOD")
        self.assertTrue(fair["confident"])
        self.assertEqual(fair["median"], 300)
        self.assertEqual(fair["p25"], 200)
        self.assertEqual(fair["p75"], 400)

    def test_abstains_when_thin(self):
        fair = F.fair_price_cents(offers(100, 200), "GOOD")
        self.assertFalse(fair["confident"])
        self.assertIsNone(fair["median"])
        self.assertEqual(fair["n"], 2)

    def test_condition_filtering(self):
        fair = F.fair_price_cents(
            offers(100, 200, 300, condition="GOOD") + offers(5000, 6000, 7000, condition="NEW"),
            "GOOD",
        )
        self.assertEqual(fair["median"], 200)


class TestDealSignal(unittest.TestCase):
    def test_deal_below_p25(self):
        fair = F.fair_price_cents(offers(200, 300, 400, 500), "GOOD")
        self.assertEqual(F.deal_signal(150, fair)[0], "deal")

    def test_no_data(self):
        self.assertEqual(F.deal_signal(100, F.fair_price_cents(offers(100), "GOOD"))[0], "no_data")

    def test_expensive(self):
        fair = F.fair_price_cents(offers(200, 300, 400, 500), "GOOD")
        self.assertEqual(F.deal_signal(600, fair)[0], "expensive")

    def test_strong_deal_needs_history(self):
        prices = list(range(100, 1100, 100))  # 10 offers, p25=300 p75=800
        fair = F.fair_price_cents(offers(*prices), "GOOD")
        self.assertEqual(F.deal_signal(50, fair)[0], "strong_deal")


class TestNearestCondition(unittest.TestCase):
    def test_order(self):
        self.assertEqual(F.nearest_condition("GOOD"), "VERY_GOOD")
        self.assertIsNone(F.nearest_condition("NEW"))
        self.assertIsNone(F.nearest_condition("NONSENSE"))


if __name__ == "__main__":
    unittest.main()
