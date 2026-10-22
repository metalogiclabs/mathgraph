"""Finite, noise-bounded post-blackout observational-acquisition tests."""
import unittest
from dataclasses import replace
import random

from finite_witness_compass import (
    BITS, HYPOTHESES, NOISE_BUDGET, compile_minimum_witnesses,
    generate_finite_trial, run_acquired, run_continuous,
    filter_hypotheses,
    check_retained_authority,
)
from audit_finite_witness import (
    audit_finite_trial, brute_force_minimum,
    exhaust_all_bounded_two_probe_observations,
)


class FiniteWitnessTests(unittest.TestCase):
    def test_two_distinct_times_required_and_minimum_independently_checked(self):
        trial = generate_finite_trial(5, kind="breakable")
        p = compile_minimum_witnesses(trial.reference, HYPOTHESES,
                                      tuple(range(1, 33)), NOISE_BUDGET)
        self.assertEqual(p.status, "SEPARATING_SET")
        self.assertEqual(p.steps, (7, 13))
        self.assertEqual(p.cost, 2)
        self.assertEqual(brute_force_minimum(trial.reference, HYPOTHESES,
                                             tuple(range(1, 17)), NOISE_BUDGET), (7, 13))

    def test_genuine_fourfold_symmetry_obstructs_correction(self):
        trial = generate_finite_trial(5, kind="unbreakable")
        p = compile_minimum_witnesses(trial.reference, HYPOTHESES,
                                      tuple(range(1, 33)), NOISE_BUDGET)
        self.assertEqual(p.status, "BOUNDED_OBSTRUCTION")
        self.assertEqual(run_acquired(trial.reference, HYPOTHESES, trial.columns).status,
                         "UNKNOWN_OBSTRUCTION")

    def test_acquisition_matches_equal_information_conventional_tracker(self):
        for seed in (5, 11, 19):
            for actual in HYPOTHESES:
                trial = generate_finite_trial(seed, true_bin=actual, kind="breakable")
                acquired = run_acquired(trial.reference, HYPOTHESES, trial.columns)
                conventional = run_continuous(trial.reference, HYPOTHESES, trial.columns)
                self.assertEqual(acquired.status, "AUTHORIZED")
                self.assertEqual(acquired.accepted_bin, actual)
                self.assertEqual(conventional.status, "AUTHORIZED")
                self.assertEqual(conventional.accepted_bin, actual)
                self.assertEqual(acquired.acquired_steps, (7, 13))
                self.assertLess(acquired.observations_processed,
                                conventional.observations_processed)
                audit_finite_trial(trial, acquired, conventional)

    def test_missed_planned_observation_is_replanned_without_oracle(self):
        trial = generate_finite_trial(5, kind="breakable", occluded_steps=(7,))
        acquired = run_acquired(trial.reference, HYPOTHESES, trial.columns)
        conventional = run_continuous(trial.reference, HYPOTHESES, trial.columns)
        self.assertNotIn(7, acquired.acquired_steps)
        self.assertEqual(acquired.status, "AUTHORIZED")
        self.assertEqual(acquired.accepted_bin, trial.true_bin)
        audit_finite_trial(trial, acquired, conventional)

    def test_contradictory_evidence_withdraws_authority(self):
        trial = generate_finite_trial(7, kind="breakable")
        reference = tuple(0 for _ in range(64))
        outcome = filter_hypotheses(reference, (0, 16), 1, (1 << BITS) - 1, 2)
        self.assertEqual(outcome, ())

    def test_absent_observation_cannot_erase_true_candidate(self):
        trial = generate_finite_trial(17, kind="breakable", occluded_steps=(7, 13))
        acquired = run_acquired(trial.reference, HYPOTHESES, trial.columns)
        self.assertNotEqual(acquired.status, "CONFLICT")
        audit_finite_trial(trial, acquired,
                           run_continuous(trial.reference, HYPOTHESES, trial.columns))

    def test_new_source_observation_can_withdraw_prior_authority(self):
        trial = generate_finite_trial(5, true_bin=32, kind="breakable")
        result = run_acquired(trial.reference, HYPOTHESES, trial.columns)
        self.assertEqual(result.status, "AUTHORIZED")
        step = 14
        self.assertEqual(check_retained_authority(trial.reference, result.accepted_bin,
                                                   step, trial.columns[step]), "RETAINED")
        distant = trial.reference[(result.accepted_bin + step) % 64] ^ ((1 << BITS) - 1)
        self.assertEqual(check_retained_authority(trial.reference, result.accepted_bin,
                                                   step, distant), "WITHDRAWN")
        self.assertEqual(check_retained_authority(trial.reference, result.accepted_bin,
                                                   step, None), "UNKNOWN_NO_OBSERVATION")

    def test_scene_identity_swap_breaks_assumption_and_both_trackers_can_fail(self):
        trial = generate_finite_trial(5, true_bin=0, kind="breakable")
        replacement = list(trial.columns)
        wrong_heading = 16
        for s in range(1, len(replacement)):
            replacement[s] = trial.reference[(wrong_heading+s) % 64]
        changed = replace(trial, columns=tuple(replacement))
        acquired = run_acquired(changed.reference, HYPOTHESES, changed.columns)
        conventional = run_continuous(changed.reference, HYPOTHESES, changed.columns)
        self.assertEqual(acquired.accepted_bin, wrong_heading)
        self.assertEqual(conventional.accepted_bin, wrong_heading)
        with self.assertRaisesRegex(AssertionError, "RUNTIME_NOISE_BOUND_BROKEN"):
            audit_finite_trial(changed, acquired, conventional)

    def test_exact_planner_matches_independent_oracle_on_random_small_maps(self):
        rng = random.Random(1701)
        hypotheses = (0, 4, 8, 12)
        horizon = tuple(range(1, 9))
        for _ in range(100):
            reference = tuple(rng.getrandbits(8) for _ in range(16))
            plan = compile_minimum_witnesses(reference, hypotheses, horizon, 1)
            independent = brute_force_minimum(reference, hypotheses, horizon, 1)
            if independent is None:
                self.assertEqual(plan.status, "BOUNDED_OBSTRUCTION")
            else:
                self.assertEqual(plan.steps, independent)

    def test_every_bounded_future_reading_is_safe_for_two_probe_map(self):
        reference = generate_finite_trial(5, kind="breakable").reference
        # Exhaustive 4 * (1 + 16 + 120)^2 sequences, not just sampled seeds.
        self.assertEqual(exhaust_all_bounded_two_probe_observations(reference), 75076)


if __name__ == "__main__":
    unittest.main()
