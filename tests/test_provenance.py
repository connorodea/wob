"""M1 provenance + landed-cost field tests (deterministic, no network)."""

import unittest

from wob.products import best_deal


class TestDealProvenance(unittest.TestCase):
    def _product(self):
        return {
            "id": 123,
            "title": "Deep Learning",
            "handle": "deep-learning-goodfellow-9780262035613",
            "variants": [
                {
                    "id": 1,
                    "option2": "NEW",
                    "price": 6500,
                    "available": True,
                    "sku": "S1",
                    "barcode": "9780262035613",
                },
                {
                    "id": 2,
                    "option2": "GOOD",
                    "price": 2500,
                    "available": True,
                    "sku": "S2",
                    "barcode": "9780262035613",
                },
            ],
        }

    def test_fields_present(self):
        d = best_deal(self._product(), 0.0, meta={"isbn13": "9780262035613"})
        for k in (
            "source_url",
            "source_raw_ref",
            "retrieved_at",
            "landed_cost_cents",
            "shipping_unknown",
        ):
            self.assertIn(k, d)
        self.assertEqual(d["landed_cost_cents"], 2500)
        self.assertTrue(d["shipping_unknown"])
        self.assertTrue(d["source_url"].endswith(".js"))
        self.assertTrue(d["retrieved_at"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()
