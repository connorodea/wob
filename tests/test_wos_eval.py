"""M3 WOS-vs-lowest-price ranking evaluation (offline, deterministic)."""

import unittest

from wob import woseval as W


class TestWosRanking(unittest.TestCase):
    def test_dataset_loads(self):
        rows = W.load_rows()
        self.assertGreaterEqual(len(rows), 12)
        self.assertTrue(all(isinstance(r.get("good"), bool) for r in rows))

    def test_wos_beats_lowest_price_on_ndcg(self):
        out = W.evaluate(k=8)
        self.assertGreaterEqual(out["wos"]["ndcg"], 0.8)
        self.assertGreater(out["wos"]["ndcg"], out["lowest_price"]["ndcg"])

    def test_wos_topk_precision(self):
        out = W.evaluate(k=8)
        self.assertGreaterEqual(out["wos"]["precision"], 0.7)
        self.assertGreaterEqual(out["wos"]["precision"], out["lowest_price"]["precision"])

    def test_budget_penalty_changes_ranking(self):
        a = W.evaluate(k=15, budget_cents=500)
        b = W.evaluate(k=15, budget_cents=10000)
        self.assertNotEqual(a["wos"]["ndcg"], b["wos"]["ndcg"])


if __name__ == "__main__":
    out = W.evaluate(k=8)
    print(out)
    unittest.main()
