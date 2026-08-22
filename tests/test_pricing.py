"""Pricing math tests — deterministic golden cases, no network."""

import unittest

from wob import pricing as P


class TestLandedCost(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(P.landed_cost_usd_cents(0), 0)

    def test_sum(self):
        self.assertEqual(P.landed_cost_usd_cents(2500, 350, 200, 100), 3150)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            P.landed_cost_usd_cents(2500, -1)

    def test_float_rejected(self):
        with self.assertRaises(ValueError):
            P.landed_cost_usd_cents(25.0)


class TestDiscount(unittest.TestCase):
    def test_half_off(self):
        self.assertAlmostEqual(P.discount_pct(500, 1000), 0.5)

    def test_overpriced_negative(self):
        self.assertAlmostEqual(P.discount_pct(1200, 1000), -0.2)

    def test_no_reference(self):
        self.assertIsNone(P.discount_pct(500, 0))
        self.assertIsNone(P.discount_pct(500, -10))

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            P.discount_pct(5.0, 10)


class TestCheapestLanded(unittest.TestCase):
    def test_picks_by_landed_not_sticker(self):
        offers = [
            {"price_cents": 500, "shipping_cents": 700},  # 1200 landed
            {"price_cents": 800, "shipping_cents": 0},  # 800 landed
            {"price_cents": 100, "shipping_cents": 3000, "fee_cents": 50},
        ]
        best = P.cheapest_landed(offers)
        self.assertEqual(best["price_cents"], 800)
        self.assertEqual(best["_landed"], 800)

    def test_bad_rows_skipped(self):
        best = P.cheapest_landed([{"price_cents": "x"}, {"price_cents": 100}])
        self.assertEqual(best["price_cents"], 100)

    def test_empty(self):
        self.assertIsNone(P.cheapest_landed([]))


if __name__ == "__main__":
    unittest.main()
