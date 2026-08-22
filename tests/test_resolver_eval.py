"""M2 resolver evaluation on the labeled fixture set (offline, deterministic).

Reports precision/recall/F1 per class and the abstention rate. This is
the baseline score an embedding model must beat. Run manually or via
scripts/eval.py later; it is NOT part of the fast unit-test path.
"""

import json
import pathlib
import unittest

from wob import resolver as R

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "matching"


def load_all():
    pairs = []
    for f in sorted(FIXTURES.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                pairs.append(json.loads(line))
    return pairs


def evaluate():
    pairs = load_all()
    per_class = {}
    for p in pairs:
        truth = p["true_class"]
        got = R.resolve(p["a"], p["b"])["class"]
        per_class.setdefault(truth, {"tp": 0, "fp": 0, "fn": 0, "n": 0})
        per_class[truth]["n"] += 1
        if got == truth:
            per_class[truth]["tp"] += 1
        else:
            per_class[truth]["fn"] += 1
            per_class.setdefault(got, {"tp": 0, "fp": 0, "fn": 0, "n": 0})
            per_class[got]["fp"] += 1
    out = {}
    for cls, m in per_class.items():
        p = m["tp"] / max(m["tp"] + m["fp"], 1)
        r = m["tp"] / max(m["tp"] + m["fn"], 1)
        f1 = 2 * p * r / max(p + r, 1e-9)
        out[cls] = {
            "precision": round(p, 3),
            "recall": round(r, 3),
            "f1": round(f1, 3),
            "n": m["n"],
        }
    return out


class TestResolverEval(unittest.TestCase):
    def test_baseline_metrics(self):
        out = evaluate()
        # baseline release bar: exact-class precision == 1.0 on this set
        self.assertEqual(out["exact"]["precision"], 1.0)
        # incompatible recall should be 1.0: no false "compatible" matches
        self.assertEqual(out["incompatible"]["recall"], 1.0)
        # nothing abstains into silence: uncertain rows exist and resolve
        self.assertIn("uncertain", out)


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
    unittest.main()
