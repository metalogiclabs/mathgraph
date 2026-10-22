"""Integrity and source-admission tests with generated, non-dataset archives."""

import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np

from replay_robotevt import replay_archive
from test_robotevt_sweep import z_rotation


class TestRobotEvtReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "Synthetic.zip"
        self.angles = np.linspace(0, 6 * np.pi, 1201)
        self.groundtruth = self.make_groundtruth(self.angles)
        self.pack(self.groundtruth)

    @staticmethod
    def make_groundtruth(angles):
        rotations = z_rotation(angles).reshape(-1, 9)
        time = np.arange(len(angles), dtype=float)[:, None] / 100
        return np.column_stack((time, rotations, np.zeros((len(angles), 3))))

    def pack(self, groundtruth):
        out = io.StringIO()
        np.savetxt(out, groundtruth, fmt="%.12f")
        self.payload = out.getvalue().encode("utf-8")
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Synthetic_GT.txt", self.payload)
            archive.writestr("Synthetic_.bag", b"synthetic-not-real-camera-data")
        self.source = {
            "name": "Synthetic",
            "gt_member": "Synthetic_GT.txt",
            "archive_sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            "gt_sha256": hashlib.sha256(self.payload).hexdigest(),
            "expected_admission": "ADMITTED",
        }

    def test_authenticated_source_runs_two_distinct_heading_formulas(self):
        report = replay_archive(self.archive, self.source)
        self.assertEqual(report["independent"]["admission"], "ADMITTED")
        self.assertAlmostEqual(report["legacy_yaw_excursion_turns"], 3.0, places=4)
        self.assertLess(report["method_excursion_gap_turns"], 0.0001)

    def test_archive_content_swap_fails_before_calculating_heading(self):
        tampered = self.archive.read_bytes() + b"changed"
        self.archive.write_bytes(tampered)
        with self.assertRaisesRegex(ValueError, "archive SHA256"):
            replay_archive(self.archive, self.source)

    def test_groundtruth_member_swap_fails_even_with_updated_archive_hash(self):
        bad = dict(self.source)
        bad["gt_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "ground truth SHA256"):
            replay_archive(self.archive, bad)

    def test_archive_observations_cannot_overrule_expected_admission(self):
        bad = dict(self.source)
        bad["expected_admission"] = "REJECTED"
        with self.assertRaisesRegex(AssertionError, "expected admission"):
            replay_archive(self.archive, bad)

    def test_partial_sweeps_authenticated_but_rejected(self):
        self.pack(self.make_groundtruth(0.8 * np.pi * np.sin(
            np.linspace(0, 10 * np.pi, 1201))))
        self.source["expected_admission"] = "REJECTED"
        report = replay_archive(self.archive, self.source)
        self.assertGreater(report["independent"]["absolute_3d_path_turns"], 6)
        self.assertEqual(report["independent"]["admission"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
