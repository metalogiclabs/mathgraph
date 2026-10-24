"""Offline synthetic integration: existing finite-witness law, capture gate and scorer."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from physical_column_demo import generate
from physical_column_replay import Gyro, build_map, camera, replay, validate_map
from physical_encoder_scorer import score
from physical_estimator_isolation import execute, build_map_isolated
from finite_witness_compass import filter_hypotheses

class ColumnReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = generate(self.root)

    def replay_local(self):
        frozen = json.loads((self.root / "frozen_map.json").read_text())
        return replay(camera(self.root / "camera.csv"),
                      Gyro(self.root / "gyro.csv"), frozen)

    def test_model_capture_is_declared_synthetic(self):
        self.assertEqual(self.manifest["generated_turns"], 6)
        self.assertTrue(self.manifest["not_a_physical_capture_manifest"])
        self.assertFalse(self.manifest["independent_physical_timing_warrant"])

    def test_map_freeze_and_actual_gyro_improvement_in_model(self):
        filename = self.root / "frozen_map.json"
        before = hashlib.sha256(filename.read_bytes()).hexdigest()
        result = self.replay_local()
        self.assertEqual(before, hashlib.sha256(filename.read_bytes()).hexdigest())
        self.assertFalse(result["physical_navigation_authorized"])
        self.assertTrue(result["events"])
        self.assertTrue(all(not e["navigation_correction_authorized"]
                            for e in result["events"]))
        self.assertGreater(sum(e["model_state"] == "MODEL_SEPARATED"
                               for e in result["events"]), 100)
        result_score = score(result, self.root / "encoder.csv", 64)
        baseline = result_score["overall"]["gyro_only_rad"]["circular_rmse_deg"]
        corrected = result_score["overall"]["mathgraph_estimate_rad"]["circular_rmse_deg"]
        self.assertLess(corrected, baseline)
        self.assertFalse(result_score["physical_heading_correction_warranted"])
        self.assertEqual(result_score["encoder_complete_turns_from_origin"], 6)

    def test_blackout_abstains(self):
        generate(self.root, blackout=True)
        result = self.replay_local()
        blackout = [e for e in result["events"] if
                    80 * 50_000_000 <= e["timestamp_ns"] < 104 * 50_000_000]
        self.assertTrue(blackout)
        self.assertTrue(all(e["model_state"] == "UNKNOWN_NO_OBSERVATION"
                            and e["gyro_only_rad"] == e["mathgraph_estimate_rad"]
                            for e in blackout))

    def test_repeated_scene_abstains(self):
        generate(self.root, scene="ambiguous")
        result = self.replay_local()
        self.assertGreater(sum(e["model_state"] == "UNKNOWN_AMBIGUOUS"
                               for e in result["events"]), 100)
        self.assertTrue(all(not e["navigation_correction_authorized"]
                            for e in result["events"]))

    def test_scene_change_withdraws(self):
        generate(self.root, change=True)
        result = self.replay_local()
        later = [e for e in result["events"] if e["timestamp_ns"] >= 150*50_000_000]
        self.assertGreater(sum(e["model_state"] == "UNKNOWN_CONFLICT"
                               for e in later), 50)

    def test_map_does_not_accept_fake_physical_warrant(self):
        frozen = json.loads((self.root / "frozen_map.json").read_text())
        frozen["physical_error_bounds_independently_certified"] = True
        with self.assertRaises(ValueError):
            validate_map(frozen)

    def test_finite_witness_filter_equivalence(self):
        reference = tuple(range(64))
        for step in range(8):
            for bits in range(20):
                hypotheses = (0, 1, 2, 3, 4, 5)
                canonical = filter_hypotheses(reference, hypotheses, step, bits, 2)
                manual = tuple(h for h in hypotheses
                               if (reference[(h+step)%64] ^ bits).bit_count() <= 2)
                self.assertEqual(canonical, manual)

    def test_future_image_change_does_not_modify_initial_map(self):
        frozen = (self.root / "frozen_map.json").read_bytes()
        generate(self.root, change=True)
        self.assertEqual(frozen, (self.root / "frozen_map.json").read_bytes())

    def test_encoder_ground_truth_is_never_passed_to_map(self):
        path = self.root / "encoder.csv"
        path.write_text("corrupted ground truth")
        # Estimator itself still works; ONLY scorer and capture gate reject.
        result = self.replay_local()
        self.assertTrue(result["events"])
        with self.assertRaises(ValueError):
            score(result, path, 64)
        self.assertNotEqual(self.manifest["file_sha256"]["encoder"],
                            hashlib.sha256(path.read_bytes()).hexdigest())

    def test_independent_scorer_rejects_early_map_freeze(self):
        result = self.replay_local()
        result["firstturn_end_ns"] = 58 * 50_000_000  # recorder lied
        with self.assertRaisesRegex(ValueError, "freeze contradicted"):
            score(result, self.root / "encoder.csv", 64)

    def test_independent_scorer_reveals_full_turn_slip(self):
        result = self.replay_local()
        ordinary = score(result, self.root / "encoder.csv", 64)
        result["events"][4]["mathgraph_estimate_rad"] += 2 * 3.141592653589793
        perturbed = score(result, self.root / "encoder.csv", 64)
        base = ordinary["overall"]["mathgraph_estimate_rad"]
        slipped = perturbed["overall"]["mathgraph_estimate_rad"]
        self.assertAlmostEqual(base["circular_rmse_deg"], slipped["circular_rmse_deg"])
        self.assertGreater(slipped["unwrapped_rmse_deg"], base["unwrapped_rmse_deg"])
        self.assertEqual(slipped["potential_full_turn_slip_samples"], 1)

    def test_scorer_refuses_authority_forgery(self):
        result = self.replay_local()
        result["physical_navigation_authorized"] = True
        with self.assertRaises(ValueError):
            score(result, self.root / "encoder.csv", 64)

    @unittest.skipUnless(os.environ.get("RUN_DOCKER_REPLAY_TEST") == "1",
                         "real isolated replay reserved for dedicated CI job")
    def test_real_docker_complete_six_turn_replay(self):
        estimator = Path(__file__).with_name("physical_column_replay.py")
        isolated_map = build_map_isolated(estimator, self.root / "camera.csv",
                                          self.root / "gyro.csv", timeout=120)
        frozen = json.loads((self.root / "frozen_map.json").read_text())
        self.assertEqual(isolated_map, frozen)
        result = execute(estimator, self.root / "camera.csv",
                         self.root / "gyro.csv", self.root / "frozen_map.json",
                         timeout=120)
        self.assertTrue(result["events"])
        verdict = score(result, self.root / "encoder.csv", 64)
        self.assertLess(
            verdict["overall"]["mathgraph_estimate_rad"]["circular_rmse_deg"],
            verdict["overall"]["gyro_only_rad"]["circular_rmse_deg"]
        )
        self.assertFalse(verdict["physical_heading_correction_warranted"])

if __name__ == "__main__":
    unittest.main()
