"""Adversarial independent audit for active camera witnessing (synthetic grammar)."""
import copy
import unittest

from finite_witness_compass import HYPOTHESES, generate_finite_trial
from physical_active_acquisition import (
    active_policy, continuous_policy, experiment, run_trial,
)
from audit_physical_active_acquisition import (
    audit_trial, audit_experiment, exact_minimum_basis_size,
)

class ActiveAcquisitionTests(unittest.TestCase):
    def test_clean_source_separates_all_four_heading_hypotheses(self):
        for seed in range(8):
            for true in HYPOTHESES:
                trace = run_trial(seed, true, "breakable", ())
                self.assertEqual(trace["active"]["status"], "MODEL_UNIQUE")
                self.assertEqual(trace["active"]["accepted_bin"], true)
                self.assertEqual(trace["continuous"]["accepted_bin"], true)
                self.assertLess(trace["active"]["sample_attempts"],
                                trace["continuous"]["sample_attempts"])
                self.assertEqual(trace["active"]["sample_attempts"], 2)
                self.assertEqual(audit_trial(trace)["active_unique"], 1)

    def test_indistinguishable_scene_produces_bounded_obstruction(self):
        for true in HYPOTHESES:
            t = run_trial(7, true, "unbreakable", ())
            self.assertEqual(t["active"]["status"], "UNKNOWN_OBSTRUCTION")
            self.assertEqual(t["active"]["sample_attempts"], 0)
            self.assertEqual(t["continuous"]["status"], "UNKNOWN_AMBIGUOUS")
            self.assertEqual(audit_trial(t)["active_unknown"], 1)

    def test_missing_critical_witness_refuses_correction(self):
        for missing in ((7,), (13,), (7, 13)):
            t = run_trial(12, HYPOTHESES[0], "breakable", missing)
            self.assertTrue(t["active"]["status"].startswith("UNKNOWN"))
            self.assertTrue(t["continuous"]["status"].startswith("UNKNOWN"))
            audit_trial(t)

    def test_adaptive_plan_never_reads_unrequested_source(self):
        t = run_trial(11, HYPOTHESES[-1], "breakable", ())
        recorded = t["active"]["requests"]
        self.assertEqual([x["step"] for x in recorded], [7, 13])
        self.assertEqual([x["observed_column"] for x in recorded],
                         [t["source_columns_grader_only"][7],
                          t["source_columns_grader_only"][13]])
        self.assertEqual(audit_trial(t)["active_witness_acquisitions"], 2)

    def test_exact_oracle_matches_compiler_minimum_basis(self):
        t = run_trial(3, 0, "breakable", ())
        basis_size = exact_minimum_basis_size(t["firstturn_reference"],
                                                list(HYPOTHESES), 1, 32, 2)
        self.assertEqual(basis_size, 2)
        self.assertEqual(t["active"]["requests"][0]["minimum_basis_size"], 2)

    def test_forged_unrequested_sensor_read_rejected(self):
        t = run_trial(0, 0, "breakable", ())
        t["active"]["requests"][0]["observed_column"] ^= 0xFFFF
        with self.assertRaisesRegex(ValueError, "forged or not acquired"):
            audit_trial(t)

    def test_claimed_false_unique_witness_rejected(self):
        t = run_trial(0, 0, "breakable", ())
        t["active"]["accepted_bin"] = 16
        with self.assertRaisesRegex(ValueError, "invalid unique"):
            audit_trial(t)

    def test_nonminimal_witness_plan_rejected(self):
        t = run_trial(0, 0, "breakable", ())
        t["active"]["requests"][0]["planned_basis"] = [7, 13, 14]
        with self.assertRaisesRegex(ValueError, "not exactly minimum"):
            audit_trial(t)

    def test_obstruction_when_future_separation_exists_rejected(self):
        t = run_trial(0, 0, "breakable", ())
        t["active"]["status"] = "UNKNOWN_OBSTRUCTION"
        with self.assertRaises(ValueError):
            audit_trial(t)

    def test_violation_of_noise_assumption_can_fool_estimator(self):
        # Deliberately replace two genuine columns with the WRONG map sector.
        # Such evidence falls OUTSIDE the predeclared sensor-error model.
        trial = generate_finite_trial(17, true_bin=0, kind="breakable")
        fake = list(trial.columns)
        for step in (7, 13):
            fake[step] = trial.reference[(16 + step) % len(trial.reference)]
        outcome = active_policy(trial.reference, HYPOTHESES, 32,
                                lambda step: fake[step])
        self.assertEqual(outcome["status"], "MODEL_UNIQUE")
        self.assertNotEqual(outcome["accepted_bin"], 0)
        trace = run_trial(17, 0, "breakable", ())
        trace["source_columns_grader_only"] = fake
        trace["active"] = outcome
        trace["continuous"] = continuous_policy(trial.reference, HYPOTHESES, 32,
                                                 lambda step: fake[step])
        with self.assertRaisesRegex(ValueError, "false correction"):
            audit_trial(trace)

    def test_complete_aggregate_replays_independently(self):
        result = experiment(seeds=3)
        proof = audit_experiment(result)
        self.assertEqual(proof["trial_traces_replayed"], 3 * 4 * 5)
        self.assertEqual(proof["physical_validation"], "UNKNOWN")
        self.assertEqual(proof["status"], "WARRANTED_WITHIN_FROZEN_SYNTHETIC_GRAMMAR")
        self.assertTrue(all(not c["active_false_unique"]
                            for c in result["cases"]))

    def test_physical_claim_injection_rejected(self):
        result = experiment(seeds=1)
        result["hardware_acquisitions"] = 1
        with self.assertRaises(ValueError):
            audit_experiment(result)

if __name__ == "__main__":
    unittest.main()
