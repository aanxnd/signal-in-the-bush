"""Qollab archive limits, provenance, and live-entry regression checks."""

import gzip
import importlib.util
import json
import os
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_qollab import OUTPUT
from package_qollab import main as package_project


class QollabPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package_project()
        sys.path.insert(0, str(OUTPUT))
        spec = importlib.util.spec_from_file_location("qollab_runner_test", OUTPUT / "runner.py")
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def setUp(self):
        self.previous_directory = Path.cwd()
        os.chdir(OUTPUT)

    def tearDown(self):
        os.chdir(self.previous_directory)

    def test_upload_limits_and_raw_data_roundtrip(self):
        with zipfile.ZipFile(ROOT / "dist/signal-in-the-bush-qollab.zip") as archive:
            self.assertLessEqual(len(archive.infolist()), 100)
            self.assertTrue(all(item.file_size <= 2_000_000 for item in archive.infolist()))
            self.assertEqual(
                gzip.decompress(archive.read("data/elephant_gps_raw.csv.gz")),
                (ROOT / "data/elephant_gps_raw.csv").read_bytes(),
            )
            self.assertEqual(archive.read("requirements.txt").decode().strip(), "qiskit==2.5.2")

    def test_classical_results_recomputed(self):
        prepared = json.loads(self.runner.prepare())
        self.assertEqual(prepared["exact_sites"], [0, 1, 4])
        self.assertEqual(prepared["exact_covered"], 1075)
        self.assertEqual(prepared["greedy_covered"], 1075)

    def test_invalid_request_never_submits_job(self):
        for depth, shots in ((True, 4096), (4, 4096), (1, 127), (1, 128.5)):
            with self.assertRaises(ValueError):
                self.runner.measure(None, depth, shots)

    def test_tampered_input_rejected(self):
        path = Path("data/candidate_sites.csv")
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "Package input changed"):
                self.runner.prepare()
        finally:
            path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
