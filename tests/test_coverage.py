import sys
import unittest
import itertools
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_qubo import build_coverage_sets, true_coverage, exact_max_coverage, greedy_max_coverage, load_sites


class CoverageTests(unittest.TestCase):
    def test_real_fix_geometry_and_unique_union(self):
        sites = pd.DataFrame({'lat': [0.0, 0.0], 'lon': [0.0, 0.002]})
        fixes = pd.DataFrame({'location-lat': [0.0] * 4, 'location-long': [0.001, 0.001, -0.003, 0.1]})
        coverage = build_coverage_sets(sites, fixes)
        np.testing.assert_array_equal(coverage, [[True, True, True, False], [True, True, False, False]])
        self.assertEqual(true_coverage([0, 1], coverage)[0], 3)
        self.assertEqual(true_coverage([], coverage)[0], 0)

    def test_exact_ground_truth_when_greedy_is_suboptimal(self):
        coverage = np.array([[1, 1, 1, 1, 0, 0], [1, 1, 0, 0, 1, 0], [0, 0, 1, 1, 0, 1]], dtype=bool)
        self.assertEqual(exact_max_coverage(coverage, 2), ((1, 2), 6))
        self.assertEqual(greedy_max_coverage(coverage, 2), ([0, 1], 5))

    def test_budget_edges_and_empty_demand(self):
        coverage = np.zeros((2, 0), dtype=bool)
        for solver in (exact_max_coverage, greedy_max_coverage):
            self.assertEqual(solver(coverage, 0)[1], 0)
            self.assertEqual(solver(coverage, 5)[1], 0)
            with self.assertRaises(ValueError):
                solver(coverage, -1)
        with self.assertRaises(ValueError):
            true_coverage([-1], coverage)

    def test_invalid_coordinates_and_radius(self):
        sites = pd.DataFrame({'lat': [91.0], 'lon': [0.0]})
        fixes = pd.DataFrame({'location-lat': [0.0], 'location-long': [0.0]})
        with self.assertRaises(ValueError):
            build_coverage_sets(sites, fixes)
        with self.assertRaises(ValueError):
            build_coverage_sets(sites, fixes, 0)

    def test_binary_lists_and_invalid_matrices(self):
        for solver in (exact_max_coverage, greedy_max_coverage):
            self.assertEqual(solver([[1, 0], [0, 1]], 2)[1], 2)
            for bad in ([1, 0], [[np.nan]], [[2]], [[-1]]):
                with self.assertRaises(ValueError):
                    solver(bad, 1)
            with self.assertRaises(ValueError):
                solver([[1]], True)
        with self.assertRaises(ValueError):
            true_coverage([True], [[1]])

    def test_random_exact_against_all_up_to_budget_subsets(self):
        rng = np.random.default_rng(10)
        for _ in range(20):
            coverage = rng.random((5, 12)) < 0.3
            for k in range(6):
                expected = max(int(coverage[list(combo)].any(axis=0).sum())
                               for size in range(k + 1)
                               for combo in itertools.combinations(range(5), size))
                self.assertEqual(exact_max_coverage(coverage, k)[1], expected)
                self.assertLessEqual(greedy_max_coverage(coverage, k)[1], expected)

    def test_invalid_site_metadata_and_nonconsecutive_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sites.csv'
            valid = pd.DataFrame({'site_id': [20, 10], 'weight_c_i': [0.5, 1.0], 'support_radius_m': [400, 400]})
            valid.to_csv(path, index=False)
            self.assertEqual(load_sites(path).site_id.tolist(), [10, 20])
            for column, value in [('site_id', 20), ('weight_c_i', np.nan), ('support_radius_m', 500)]:
                bad = valid.copy()
                bad.loc[1, column] = value
                bad.to_csv(path, index=False)
                with self.assertRaises(ValueError):
                    load_sites(path)


if __name__ == '__main__':
    unittest.main()
