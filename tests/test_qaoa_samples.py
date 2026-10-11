import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from qaoa_samples import decode_bitstring, summarize_samples


class QaoaSampleTests(unittest.TestCase):
    def summary(self, counts, shots=None):
        return summarize_samples(counts, np.array([2., 1.]), np.zeros((2, 2)),
            1, 5., [10, 20], 2., shots)

    def test_mode_is_not_best_and_rates_are_shot_weighted(self):
        r = self.summary({'11': 7, '01': 2, '10': 1}, 10)
        self.assertEqual(r['mode']['sites'], [10, 20])
        self.assertEqual(r['selected_raw']['sites'], [10])
        self.assertEqual(r['feasible_rate'], 0.3)
        self.assertEqual(r['proxy_optimal_rate'], 0.2)
        self.assertEqual(r['exactly_budget_rate'], 0.3)

    def test_underbudget_feasibility_and_no_feasible_sample(self):
        r = self.summary({'00': 3, '11': 1})
        self.assertEqual(r['feasible_rate'], 0.75)
        self.assertEqual(r['exactly_budget_rate'], 0.0)
        self.assertEqual(r['selected_raw']['sites'], [])
        self.assertIsNone(self.summary({'11': 4})['selected_raw'])

    def test_ties_and_all_optimal_bitstrings(self):
        r = summarize_samples({'10': 3, '01': 3}, np.ones(2), np.zeros((2, 2)),
            1, 5., [10, 20], 1., 6)
        self.assertEqual(r['mode']['bitstring'], '01')
        self.assertEqual(r['selected_raw']['bitstring'], '01')
        self.assertEqual(r['proxy_optimal_rate'], 1.0)

    def test_endianness_and_invalid_counts(self):
        np.testing.assert_array_equal(decode_bitstring('10 01', 4), [1, 0, 0, 1])
        for counts in ({}, {'1': 2}, {'xx': 2}, {'01': -1}, {'01': 1.5}, {'01': True}):
            with self.assertRaises(ValueError):
                self.summary(counts)
        with self.assertRaises(ValueError):
            self.summary({'01': 3}, 4)
        self.assertEqual(self.summary({'0 1': 1, '01': 2}, 3)['unique_bitstrings'], 1)

    def test_invalid_objective_metadata(self):
        for shots in (True, 2.0, 0):
            with self.assertRaises(ValueError):
                self.summary({'01': 2}, shots)
        cases = [([2., 1.], [[0., 1.], [0., 0.]], 5., [10, 20]),
                 ([2., 1.], [[1., 0.], [0., 0.]], 5., [10, 20]),
                 ([2., 1.], np.zeros((2, 2)), -1., [10, 20]),
                 ([2., 1.], np.zeros((2, 2)), 5., [True, 20])]
        for c, Q, A, ids in cases:
            with self.assertRaises(ValueError):
                summarize_samples({'01': 2}, c, Q, 1, A, ids, 2.)
        with self.assertRaises(ValueError):
            summarize_samples({'01': 2}, [2., 1.], np.zeros((2, 2)), 1, 5., [10, 20], 1.)


if __name__ == '__main__':
    unittest.main()
