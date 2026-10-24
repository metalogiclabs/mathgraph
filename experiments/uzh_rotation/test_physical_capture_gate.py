import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from physical_capture_gate import audit


class PhysicalGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.streams = {}
        for kind in ("camera", "gyro", "encoder"):
            p = self.root / (kind + ".csv")
            p.write_text("sample\n")
            self.streams[kind] = {
                "path": p.name,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "timestamps_ns": [1, 2, 3],
                "clock_id": kind + "-clock",
            }
        self.data = {
            "streams": self.streams,
            "encoder_complete_revolutions": 5,
            "independent_timing_calibration_sha256": "a" * 64,
            "held_out_timing_envelope_passed": True,
            "frozen_first_turn_map_sha256": "b" * 64,
            "encoder_used_by_estimator": False,
        }
    def check(self):
        path = self.root / "manifest.json"
        path.write_text(json.dumps(self.data))
        return audit(path)
    def test_structural_candidate(self):
        self.assertEqual(self.check(), [])
    def test_four_turns_rejected(self):
        self.data["encoder_complete_revolutions"] = 4
        self.assertTrue(self.check())
    def test_nominal_timing_not_enough(self):
        self.data["held_out_timing_envelope_passed"] = False
        self.assertTrue(self.check())
    def test_encoder_leak_rejected(self):
        self.data["encoder_used_by_estimator"] = True
        self.assertTrue(self.check())
    def test_timestamp_collision_rejected(self):
        self.streams["gyro"]["timestamps_ns"] = [1, 1, 3]
        self.assertTrue(self.check())
    def test_changed_bytes_rejected(self):
        (self.root / "camera.csv").write_text("tampered")
        self.assertTrue(self.check())
    def test_escape_rejected(self):
        self.streams["camera"]["path"] = "../outside"
        self.assertTrue(self.check())
    def test_missing_clock_rejected(self):
        self.streams["camera"]["clock_id"] = ""
        self.assertTrue(self.check())

if __name__ == "__main__":
    unittest.main()
