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
            if kind == "encoder":
                p.write_text("timestamp_ns,unwrapped_count\n" + "".join(f"{i+1},{i}\n" for i in range(11)))
                stamps = list(range(1, 12))
            else:
                p.write_text("sample\n")
                stamps = [1, 2, 3]
            self.streams[kind] = {"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "timestamps_ns": stamps, "clock_id": kind + "-clock"}
        for role, base in (("calibration", 100), ("holdout", 200)):
            p = self.root / (role + "_clock.csv")
            p.write_text("reference_timestamp_ns,sensor_timestamp_ns\n" + "".join(f"{base+i},{base+i+2}\n" for i in range(3)))
        self.clock = {"frozen_offset_ns": 2, "frozen_max_abs_residual_ns": 0}
        self.refresh_clock_hashes()
        self.data = {"clock_calibration": self.clock, "streams": self.streams, "encoder_pulses_per_revolution": 2, "independent_timing_calibration_sha256": "a"*64, "held_out_timing_envelope_passed": True, "frozen_first_turn_map_sha256": "b"*64, "encoder_used_by_estimator": False}
    def refresh_clock_hashes(self):
        for role in ("calibration", "holdout"):
            p = self.root / (role + "_clock.csv")
            self.clock[role + "_path"] = p.name
            self.clock[role + "_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    def check(self):
        path = self.root / "manifest.json"
        path.write_text(json.dumps(self.data))
        return audit(path)
    def refresh_encoder_hash(self):
        p = self.root / "encoder.csv"
        self.streams["encoder"]["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    def test_structural_candidate(self):
        self.assertEqual(self.check(), [])
    def test_four_turns_rejected(self):
        self.data["encoder_pulses_per_revolution"] = 3
        self.assertTrue(self.check())
    def test_nominal_timing_not_enough(self):
        self.clock["frozen_max_abs_residual_ns"] = 0\n        p = self.root / "holdout_clock.csv"\n        p.write_text(p.read_text().replace("200,202", "200,203"))\n        self.refresh_clock_hashes()
        self.assertTrue(self.check())
    def test_overlapping_clock_windows_rejected(self):
        p = self.root / "holdout_clock.csv"
        p.write_text((self.root / "calibration_clock.csv").read_text())
        self.refresh_clock_hashes()
        self.assertTrue(self.check())
    def test_missing_clock_trace_rejected(self):
        (self.root / "holdout_clock.csv").unlink()
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
    def test_encoder_count_gap_rejected_even_if_hash_matches(self):
        p = self.root / "encoder.csv"
        p.write_text(p.read_text().replace("5,4\n", "5,40\n"))
        self.refresh_encoder_hash()
        self.assertTrue(self.check())
    def test_encoder_time_mismatch_rejected(self):
        self.streams["encoder"]["timestamps_ns"][0] = 0
        self.assertTrue(self.check())
    def test_declared_turns_cannot_override_source(self):
        self.data["encoder_complete_revolutions"] = 100
        self.data["encoder_pulses_per_revolution"] = 3
        self.assertTrue(self.check())

if __name__ == "__main__":
    unittest.main()
