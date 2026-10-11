import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_demo_map import checked_json, load_results


class MapResultsTests(unittest.TestCase):
    def test_generated_selections_and_coordinate_identity(self):
        sites, baseline, placements, _ = load_results()
        self.assertEqual(placements[0]["sites"], baseline["exact"]["sites"])
        for p in (1, 2, 3):
            report = checked_json(f"data/qaoa_repair_p{p}.json")
            for key in ("raw", "repaired"):
                placement = next(x for x in placements if x["label"] == f"QAOA p={p} {key}")
                self.assertEqual(placement["sites"], report["selected_raw"][key]["sites"])
                self.assertEqual(
                    placement["covered_fixes"], report["selected_raw"][key]["covered_fixes"]
                )
                self.assertTrue(set(placement["sites"]) <= set(sites.site_id))

    def test_stale_dependency_rejected(self):
        with patch("build_demo_map.hashlib.sha256") as digest:
            digest.return_value.hexdigest.return_value = "stale"
            with self.assertRaisesRegex(ValueError, "stale input"):
                checked_json("data/coverage_baselines.json")

    def test_missing_provenance_rejected(self):
        with patch("build_demo_map.json.loads", return_value={}):
            with self.assertRaisesRegex(ValueError, "missing required input provenance"):
                checked_json("data/coverage_baselines.json", ("data/candidate_sites.csv",))

    def test_corrupt_coverage_count_rejected(self):
        original = checked_json

        def corrupt(path, *args):
            report = copy.deepcopy(original(path, *args))
            if path.endswith("qaoa_repair_p1.json"):
                report["selected_raw"]["raw"]["covered_fixes"] += 1
            return report

        with patch("build_demo_map.checked_json", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "coverage count"):
                load_results()

    def test_no_feasible_sample_is_preserved(self):
        original = checked_json

        def missing(path, *args):
            report = copy.deepcopy(original(path, *args))
            if path.endswith("qaoa_repair_p1.json"):
                report["selected_raw"] = None
            return report

        with patch("build_demo_map.checked_json", side_effect=missing):
            _, _, placements, _ = load_results()
            self.assertFalse(placements[1]["available"])
            self.assertIsNone(placements[1]["covered_fixes"])


if __name__ == "__main__":
    unittest.main()
