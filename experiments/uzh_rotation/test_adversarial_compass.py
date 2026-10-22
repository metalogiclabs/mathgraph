"""Adversarial invariants for the synthetic single-column compass.

Run with: python -m unittest discover -s experiments/uzh_rotation -p 'test_adversarial_compass.py'
"""
import unittest

import numpy as np

from adversarial_compass import (
    build_first_turn_map,
    detect_rotational_alias,
    generate_trial,
    grade_correction,
    plan_separating_witness,
    run_estimators,
    run_benchmark,
)
from audit_adversarial_compass import audit_run


class AdversarialCompassTests(unittest.TestCase):
    def test_exact_fourfold_symmetry_is_a_bounded_obstruction(self):
        rng = np.random.default_rng(13)
        unit = rng.normal(size=(4, 12))
        unit /= np.linalg.norm(unit, axis=1, keepdims=True)
        reference = np.tile(unit, (4, 1))
        plan = plan_separating_witness(
            reference, np.ones(16, bool), (0, 4, 8, 12),
            angular_step_bins=1.0, max_steps=32, separation=0.25,
        )
        self.assertIsNone(plan.step)
        self.assertEqual(plan.status, "BOUNDED_NON_SEPARABILITY")

    def test_plan_finds_next_observation_that_separates_same_current_feature(self):
        reference = np.zeros((8, 4))
        reference[0] = reference[4] = [1, 0, 0, 0]
        reference[1] = [0, 1, 0, 0]
        reference[5] = [0, 0, 1, 0]
        reference[2] = [0, 0, 0, 1]
        reference[6] = [0, 0, 0, 1]
        plan = plan_separating_witness(
            reference, np.ones(8, bool), (0, 4),
            angular_step_bins=1.0, max_steps=4, separation=0.5,
        )
        self.assertEqual(plan.step, 1)
        self.assertEqual(plan.status, "SEPARATING_OBSERVATION")

    def test_missing_training_samples_are_not_filled_using_future_or_truth(self):
        columns = np.arange(24 * 4, dtype=float).reshape((24, 4))
        observed = np.ones(24, dtype=bool)
        observed[:4] = False
        gyro_deltas = np.full(24, 2 * np.pi / 8)
        first = build_first_turn_map(columns, observed, gyro_deltas, bins=8)
        later_changed = columns.copy()
        later_changed[9:] *= -1000
        second = build_first_turn_map(later_changed, observed, gyro_deltas, bins=8)
        np.testing.assert_array_equal(first.reference, second.reference)
        self.assertEqual(first.training_end, 7)
        self.assertLess(first.occupied.sum(), 8)

    def test_off_target_correction_is_counted_even_if_small_post_error(self):
        outcome = grade_correction(before=np.deg2rad(30),
                                   after=np.deg2rad(8),
                                   target=np.deg2rad(20), truth=0.0)
        self.assertTrue(outcome.incorrect_target)
        self.assertFalse(outcome.harmful)

    def test_all_methods_get_identical_sensor_stream_and_never_truth(self):
        trial = generate_trial("repeat_exact", seed=11, turns=4)
        same_sensors = run_estimators(trial.columns, trial.observed, trial.gyro_deltas)
        self.assertEqual(set(same_sensors), {"gyro_only", "matched_filter", "robust", "evidence_aware"})
        self.assertTrue(np.any(~trial.observed))
        # The estimator API accepts columns, observed flags and gyro only.
        # Ground truth is used only by the external grader.
        changed_truth = trial.truth + 1.3
        self.assertFalse(np.array_equal(changed_truth, trial.truth))
        repeated = run_estimators(trial.columns, trial.observed, trial.gyro_deltas)
        for method in same_sensors:
            np.testing.assert_array_equal(same_sensors[method].heading,
                                          repeated[method].heading)

    def test_blackout_cannot_produce_visual_acceptances(self):
        trial = generate_trial("blackout_turns", seed=19, turns=8)
        estimates = run_estimators(trial.columns, trial.observed, trial.gyro_deltas)
        for method, estimate in estimates.items():
            if method == "gyro_only":
                continue
            self.assertTrue(all(trial.observed[event.index] for event in estimate.events))

    def test_external_auditor_regrades_complete_trace(self):
        result = run_benchmark("clean", 5, turns=4, include_trace=True)
        self.assertEqual(audit_run(result), 4)

    def test_external_auditor_rejects_falsified_safety_metric(self):
        result = run_benchmark("clean", 5, turns=4, include_trace=True)
        result["methods"]["robust"]["incorrect_accepted_corrections"] += 1
        with self.assertRaises(AssertionError):
            audit_run(result)

    def test_learned_noisy_fourfold_map_has_detectable_alias(self):
        periodic = generate_trial("repeat_exact", seed=5, turns=4)
        unique = generate_trial("clean", seed=5, turns=4)
        repeated_map = build_first_turn_map(periodic.columns, periodic.observed, periodic.gyro_deltas)
        clean_map = build_first_turn_map(unique.columns, unique.observed, unique.gyro_deltas)
        self.assertAlmostEqual(detect_rotational_alias(repeated_map), 64, delta=2)
        self.assertIsNone(detect_rotational_alias(clean_map))

    def test_periodic_scene_cannot_authorize_false_global_jump(self):
        trial = generate_trial("repeat_exact", seed=5, turns=12)
        estimates = run_estimators(trial.columns, trial.observed, trial.gyro_deltas)
        for name in ("robust", "evidence_aware"):
            incorrect = [e for e in estimates[name].events
                         if grade_correction(e.before, e.after, e.target,
                                             trial.truth[e.index]).incorrect_target]
            self.assertEqual(incorrect, [], name)


if __name__ == "__main__":
    unittest.main()
