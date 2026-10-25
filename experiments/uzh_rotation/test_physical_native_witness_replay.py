"""Cross-qualification: reuse existing richer native C99 map, not duplicate it."""
import ctypes
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from audit_finite_partial_map import build_map, load_library, Plan
from finite_witness_compass import HYPOTHESES, generate_finite_trial
from physical_active_acquisition import active_policy
from physical_native_witness_replay import experiment, native_follow

class NativeActiveReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.native = load_library(Path(cls.tmp.name) / "native.so")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exact_zero_jitter_replay_matches_python_under_occlusion(self):
        for seed in range(12):
            for true in HYPOTHESES:
                for absent in ((), (7,), (13,), (7, 13), (7, 13, 23, 29)):
                    trial = generate_finite_trial(seed, true_bin=true,
                                                  kind="breakable", occluded_steps=absent)
                    native = native_follow(self.native, trial.reference, trial.columns,
                                           jitter=0)
                    python = active_policy(trial.reference, HYPOTHESES, 32,
                                           lambda step: trial.columns[step])
                    self.assertEqual(native["status"], python["status"])
                    self.assertEqual(native["accepted_bin"], python["accepted_bin"])
                    self.assertEqual(native["remaining"], python["candidates"])
                    self.assertEqual([e["step"] for e in native["events"]],
                                     [e["step"] for e in python["requests"]])
                    if native["status"] == "MODEL_UNIQUE":
                        self.assertEqual(native["accepted_bin"], true)

    def test_one_bin_timing_uncertainty_withholds_unique_result(self):
        for seed in range(16):
            t = generate_finite_trial(seed, true_bin=0, kind="breakable")
            exact = native_follow(self.native, t.reference, t.columns, jitter=0)
            uncertain = native_follow(self.native, t.reference, t.columns, jitter=1)
            self.assertEqual(exact["status"], "MODEL_UNIQUE")
            self.assertEqual(uncertain["status"], "UNKNOWN_OBSTRUCTION")
            self.assertEqual(uncertain["accepted_bin"], None)

    def test_quarantined_firstturn_coverage_refuses_guaranteed_plan(self):
        t = generate_finite_trial(5, true_bin=0, kind="breakable")
        available = [i for i in range(64) if i % 16 not in (7, 13)]
        limited = native_follow(self.native, t.reference, t.columns,
                                jitter=0, known=available)
        self.assertEqual(limited["status"], "UNKNOWN_OBSTRUCTION")
        self.assertIsNone(limited["accepted_bin"])

    def test_native_already_unique_is_not_a_camera_authority(self):
        t = generate_finite_trial(3, true_bin=0, kind="breakable")
        m = build_map(self.native, SimpleNamespace(reference=t.reference), range(64))
        plan = Plan()
        rc = self.native.mg_sparse_plan(ctypes.byref(m), 1, 1, 32, 2, 0,
                                         ctypes.byref(plan))
        self.assertEqual(rc, 0)
        self.assertEqual(plan.status, 2)
        self.assertEqual(plan.cost, 0)
        self.assertEqual(plan.first_step, 0)

    def test_conservative_jitter_candidate_filter_includes_true(self):
        for seed in range(12):
            for true in HYPOTHESES:
                t = generate_finite_trial(seed, true_bin=true, kind="breakable")
                m = build_map(self.native, t.reference, range(64))
                for step in (1, 7, 13, 23, 29):
                    mask = self.native.mg_sparse_filter(
                        ctypes.byref(m), 15, step, t.columns[step], 2, 1)
                    self.assertNotEqual(mask & (1 << (true // 16)), 0)

    def test_native_census_is_not_physical_authority(self):
        result = experiment(seeds=3)
        self.assertTrue(result["native_vs_python_agreement_in_all_jitter0_trials"])
        self.assertEqual(result["hardware_observation_acquisitions"], 0)
        self.assertFalse(result["physical_heading_authorized"])
        clean = next(x for x in result["conditions"]
                     if x["condition"] == "breakable_clean")
        self.assertEqual(clean["jitter_0_unique"], 12)
        self.assertEqual(clean["jitter_1_unique"], 0)
        self.assertEqual(clean["jitter_0_camera_attempts"], 24)

if __name__ == "__main__":
    unittest.main()
