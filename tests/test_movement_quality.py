import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_pinch_points import compute_speed, load_data, run_dbscan, split_dwell_transit


class MovementQualityTests(unittest.TestCase):
    def test_unknown_intervals_not_dwell_or_transit(self):
        d = pd.DataFrame(
            {
                "individual-local-identifier": ["test"] * 5,
                "timestamp": pd.to_datetime(
                    [
                        "2020-01-01 00:00",
                        "2020-01-01 01:00",
                        "2020-01-02 01:00",
                        "2020-01-02 02:00",
                        "2020-01-02 02:00",
                    ]
                ),
                "location-lat": [0.0] * 5,
                "location-long": [0.0, 0.01, 0.02, 1.0, 1.01],
            }
        )
        d = split_dwell_transit(compute_speed(d))
        self.assertEqual(d.is_transit.tolist(), [False, True, False, False, False])
        self.assertFalse(d.is_dwell.any())
        self.assertFalse(np.isinf(d.speed_kmh).any())

    def test_missing_and_duplicate_timestamps_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            d = pd.DataFrame(
                {
                    "visible": [True, True],
                    "individual-local-identifier": ["test"] * 2,
                    "timestamp": ["2020-01-01", "2020-01-01"],
                    "location-lat": [0, 0],
                    "location-long": [0, 0],
                }
            )
            for timestamp in ("2020-01-01", None, "invalid"):
                d.loc[1, "timestamp"] = timestamp
                d.to_csv(path, index=False)
                with self.assertRaises(ValueError):
                    load_data(path)

    def test_unsorted_rows_and_empty_context(self):
        d = pd.DataFrame(
            {
                "individual-local-identifier": ["test", "test"],
                "timestamp": pd.to_datetime(["2020-01-01 01:00", "2020-01-01 00:00"]),
                "location-lat": [0.0, 0.0],
                "location-long": [0.01, 0.0],
            }
        )
        result = split_dwell_transit(compute_speed(d))
        self.assertEqual(result.is_transit.tolist(), [False, True])
        labels, count = run_dbscan(d.iloc[:0], 100)
        self.assertEqual(count, 0)
        self.assertEqual(len(labels), 0)

    def test_duplicate_events_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            pd.DataFrame(
                {
                    "visible": [True, True],
                    "individual-local-identifier": ["test"] * 2,
                    "timestamp": ["2020-01-01 00:00", "2020-01-01 01:00"],
                    "event-id": [1, 1],
                    "location-lat": [0, 0],
                    "location-long": [0, 0],
                }
            ).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                load_data(path)


if __name__ == "__main__":
    unittest.main()
