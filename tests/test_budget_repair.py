import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from repair_qaoa import evaluate_placement, repair_budget


class BudgetRepairTests(unittest.TestCase):
    def test_trim_redundant_site_then_fill_positive_marginal(self):
        coverage = np.array([[1, 1, 0], [1, 1, 0], [0, 0, 1]], dtype=bool)
        chosen, actions = repair_budget([0, 1, 2], coverage, 2, [30, 10, 20])
        self.assertEqual(chosen, [0, 2])
        self.assertEqual(actions, [dict(action="remove", site_id=10, coverage_change=0)])
        chosen, actions = repair_budget([0], coverage, 2, [30, 10, 20])
        self.assertEqual(chosen, [0, 2])
        self.assertEqual(actions[0]["coverage_change"], 1)

    def test_no_positive_gain_and_budget_zero(self):
        coverage = np.ones((3, 2), dtype=bool)
        self.assertEqual(repair_budget([1], coverage, 3, [0, 1, 2]), ([1], []))
        chosen, actions = repair_budget([0, 1], coverage, 0, [0, 1, 2])
        self.assertEqual(chosen, [])
        self.assertEqual(len(actions), 2)

    def test_exact_budget_identity_and_invalid_inputs(self):
        coverage = np.eye(3, dtype=bool)
        self.assertEqual(repair_budget([0, 2], coverage, 2, [0, 1, 2]), ([0, 2], []))
        for chosen in ([0, 0], [-1], [True], [3]):
            with self.assertRaises(ValueError):
                repair_budget(chosen, coverage, 2, [0, 1, 2])

    def test_random_repair_feasibility_and_idempotence(self):
        rng = np.random.default_rng(123)
        for _ in range(30):
            coverage = rng.random((6, 20)) < 0.2
            chosen = np.flatnonzero(rng.random(6) < 0.5).tolist()
            repaired, _ = repair_budget(chosen, coverage, 3, list(range(6)))
            self.assertLessEqual(len(repaired), 3)
            self.assertEqual(repair_budget(repaired, coverage, 3, list(range(6))), (repaired, []))
            if len(chosen) <= 3:
                self.assertGreaterEqual(
                    coverage[repaired].any(axis=0).sum(), coverage[chosen].any(axis=0).sum()
                )

    def test_infeasible_coverage_not_presented_as_valid_ratio(self):
        report = evaluate_placement(
            [0, 1], np.eye(2, dtype=bool), np.ones(2), np.zeros((2, 2)), 1, 2.0, [10, 20], 1.0, 1
        )
        self.assertEqual(report["covered_fixes"], 2)
        self.assertFalse(report["coverage_comparison_valid"])
        self.assertIsNone(report["coverage_ratio_to_feasible_optimum"])

    def test_evaluation_rejects_duplicate_or_invalid_indices(self):
        for indices in ([0, 0], [-1], [True], [2]):
            with self.assertRaises(ValueError):
                evaluate_placement(
                    indices,
                    np.eye(2, dtype=bool),
                    np.ones(2),
                    np.zeros((2, 2)),
                    1,
                    2.0,
                    [10, 20],
                    1.0,
                    1,
                )
        for ids in ([True, 20], [-1, 20], [10, 10]):
            with self.assertRaises(ValueError):
                repair_budget([], np.eye(2, dtype=bool), 1, ids)

    def test_underbudget_ties_and_generator_input(self):
        selected, actions = repair_budget(iter([]), np.eye(2, dtype=bool), 1, [20, 10])
        self.assertEqual(selected, [1])
        self.assertEqual(actions[0]["site_id"], 10)


if __name__ == "__main__":
    unittest.main()
