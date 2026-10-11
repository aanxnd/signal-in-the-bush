import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_pinch_points import build_local_candidates, build_candidate_table, validate_candidates, haversine_m


class CandidateGeometryTests(unittest.TestCase):
    def points(self, centers):
        return pd.DataFrame({
            "location-lat": [lat for lat in centers for _ in range(6)],
            "location-long": [0.0] * (6 * len(centers)),
            "individual-local-identifier": ["test"] * (6 * len(centers)),
        })

    def test_empty_centroid_replaced_by_supported_observed_sites(self):
        points = self.points([0.0, 0.1])
        self.assertTrue((haversine_m(0.05, 0, points['location-lat'], 0) > 400).all())
        sites = build_local_candidates(points, np.zeros(len(points), dtype=int))
        validate_candidates(sites, points)
        self.assertEqual(len(sites), 2)
        self.assertEqual(sites.n_fixes.tolist(), [6, 6])

    def test_explicit_reduction_and_hard_cap_validation(self):
        points = self.points(np.arange(20) * 0.02)
        sites = build_local_candidates(points, np.zeros(len(points), dtype=int))
        self.assertEqual(len(sites), 15)
        validate_candidates(sites, points)
        with self.assertRaises(ValueError):
            validate_candidates(pd.concat([sites, sites.iloc[:1]]), points)
        pd.testing.assert_frame_equal(sites, build_local_candidates(points, np.zeros(len(points), dtype=int)))

    def test_insufficient_support_rejected(self):
        points = self.points([0.0]).iloc[:4]
        with self.assertRaises(ValueError):
            build_local_candidates(points, np.zeros(len(points), dtype=int))

    def test_invalid_inputs_and_optional_empty_dwell(self):
        points = self.points([0.0])
        for labels in ([0], np.zeros((len(points), 1))):
            with self.assertRaises(ValueError):
                build_local_candidates(points, labels)
        bad = points.copy()
        bad.loc[0, 'location-lat'] = np.nan
        with self.assertRaises(ValueError):
            build_local_candidates(bad, np.zeros(len(bad)))
        context = build_candidate_table(points, np.full(len(points), -1))
        self.assertTrue(context.empty)
        self.assertIn('lat', context.columns)

    def test_ties_follow_timestamps_and_noise_cannot_be_centers(self):
        points = self.points([0.1, 0.0])
        points['timestamp'] = pd.to_datetime(['2020-02-01'] * 6 + ['2020-01-01'] * 6)
        sites = build_local_candidates(points, np.zeros(len(points)))
        self.assertEqual(sites.iloc[0].lat, 0.0)
        labels = np.array([-1] * 6 + [0] * 6)
        sites = build_local_candidates(points, labels)
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites.iloc[0].lat, 0.0)

    def test_corrupt_site_metadata_and_overlap_rejected(self):
        points = self.points([0.0, 0.02])
        sites = build_local_candidates(points, np.zeros(len(points)))
        for column, value in [('site_id', 0), ('support_radius_m', 500), ('n_fixes', 99), ('weight_c_i', 0.2)]:
            bad = sites.copy()
            bad.loc[1, column] = value
            with self.assertRaises(ValueError):
                validate_candidates(bad, points)
        bad = sites.copy()
        bad.loc[1, ['lat', 'lon']] = bad.loc[0, ['lat', 'lon']].to_numpy()
        with self.assertRaises(ValueError):
            validate_candidates(bad, points)


if __name__ == "__main__":
    unittest.main()
