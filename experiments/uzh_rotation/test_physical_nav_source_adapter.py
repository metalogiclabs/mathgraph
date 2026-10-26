"""Protect canonical NAVIGATION-to-column replay adapter and provenance."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from physical_nav_source_adapter import convert
from physical_column_replay import Gyro, build_map, camera
from test_physical_evidence_gate import make_fixture

class CanonicalNavAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.nav, self.encoder = make_fixture(self.root)
        self.out = self.root / "adapted"

    def test_original_role_source_adapted_without_encoder_access(self):
        evidence = convert(self.nav, self.out)
        self.assertEqual(evidence["state"], "SUPPLEMENTAL_NAVIGATION_SOURCE_ADAPTED_ONLY")
        self.assertFalse(evidence["encoder_input_provided"])
        self.assertFalse(evidence["physical_navigation_authorized"])
        self.assertEqual(evidence["capture_mode_as_claimed"], "FIXTURE")
        self.assertEqual(evidence["original_sensor_sha256"],
                         hashlib.sha256((self.nav / "sensors.jsonl").read_bytes()).hexdigest())
        self.assertFalse((self.out / "encoder.csv").exists())
        rows = (self.nav / "sensors.jsonl").read_text().splitlines()
        original = [json.loads(row) for row in rows]
        cam_count = sum(x["kind"] == "COLUMN" for x in original)
        gyro_count = sum(x["kind"] == "GYRO" for x in original)
        self.assertEqual(evidence["camera_samples"], cam_count)
        self.assertEqual(evidence["gyro_samples"], gyro_count)
        with (self.out / "camera.csv").open(newline="") as f:
            images = list(csv.DictReader(f))
        self.assertEqual(len(images), cam_count)
        self.assertTrue(any(x["usable"] == "0" for x in images))

    def test_nav_source_tamper_rejected_even_with_rehashed_adapter(self):
        p = self.nav / "sensors.jsonl"
        p.write_bytes(p.read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            convert(self.nav, self.out)

    def test_encoders_in_nav_role_rejected(self):
        (self.nav / "encoder.jsonl").write_bytes((self.encoder / "encoder.jsonl").read_bytes())
        with self.assertRaises(ValueError):
            convert(self.nav, self.out)

    def test_cannot_write_inside_canonical_source_bundle(self):
        with self.assertRaises(ValueError):
            convert(self.nav, self.nav / "outputs")

    def test_sparse_canonical_fixture_not_falsely_upgraded_to_firstturn(self):
        convert(self.nav, self.out)
        with self.assertRaisesRegex(ValueError,
                                    "camera outside bounded causal gyro window"):
            build_map(camera(self.out / "camera.csv"), Gyro(self.out / "gyro.csv"))

if __name__ == "__main__":
    unittest.main()
