"""Bounded one-bin timing uncertainty for acquired single-column witnesses."""

from dataclasses import replace
import random
import unittest

from finite_witness_jitter import (
    BITS, HYPOTHESES, compile_jitter_witnesses, generate_jitter_trial,
    run_jitter_acquired, run_jitter_continuous, filter_jitter_hypotheses,
)
from audit_finite_witness_jitter import (
    brute_force_jitter_plan, audit_jitter_trial, exhaust_jitter_observations,
)


class FiniteJitterTests(unittest.TestCase):
    def test_wide_landmarks_produce_two_guaranteed_distinct_observations(self):
        trial = generate_jitter_trial(5, true_bin=32, kind="wide")
        plan = compile_jitter_witnesses(trial.reference, HYPOTHESES,
                                        tuple(range(1, 33)), 2, 1)
        self.assertEqual(plan.status, "SEPARATING_SET")
        self.assertEqual(plan.steps, (7, 13))
        self.assertEqual(plan.cost, 2)
        self.assertEqual(brute_force_jitter_plan(trial.reference, HYPOTHESES,
                                                 tuple(range(1, 17)), 2, 1), (7, 13))

    def test_isolated_landmarks_cannot_guarantee_separation_with_jitter(self):
        isolated = generate_jitter_trial(5, true_bin=0, kind="narrow")
        plan = compile_jitter_witnesses(isolated.reference, HYPOTHESES,
                                        tuple(range(1, 33)), 2, 1)
        self.assertEqual(plan.status, "BOUNDED_NO_GUARANTEED_SEPARATION")
        policy = run_jitter_acquired(isolated.reference, HYPOTHESES, isolated.columns)
        self.assertEqual(policy.status, "UNKNOWN_OBSTRUCTION")

    def test_actual_fourfold_symmetry_withholds_even_without_timing_uncertainty(self):
        trial = generate_jitter_trial(5, true_bin=0, kind="unbreakable")
        self.assertEqual(run_jitter_acquired(trial.reference, HYPOTHESES,
                                              trial.columns).status,"UNKNOWN_OBSTRUCTION")
        self.assertEqual(run_jitter_continuous(trial.reference, HYPOTHESES,
                                                trial.columns).status,"UNKNOWN_AMBIGUOUS")

    def test_bounded_gyro_jitter_keeps_true_candidate_and_recovers(self):
        for seed in (5, 11, 19):
            for actual in HYPOTHESES:
                trial = generate_jitter_trial(seed, true_bin=actual, kind="wide")
                sparse = run_jitter_acquired(trial.reference, HYPOTHESES, trial.columns)
                baseline = run_jitter_continuous(trial.reference, HYPOTHESES, trial.columns)
                self.assertEqual(sparse.status, "AUTHORIZED")
                self.assertEqual(sparse.accepted_bin, actual)
                self.assertEqual(sparse.acquired_steps, (7, 13))
                self.assertEqual(baseline.status, "AUTHORIZED")
                self.assertEqual(baseline.accepted_bin, actual)
                self.assertLess(sparse.observations_processed,baseline.observations_processed)
                audit_jitter_trial(trial, sparse, baseline)

    def test_missing_witness_triggers_real_replanning(self):
        trial = generate_jitter_trial(5, true_bin=0, kind="wide", occluded_steps=(7,))
        sparse = run_jitter_acquired(trial.reference, HYPOTHESES, trial.columns)
        baseline = run_jitter_continuous(trial.reference, HYPOTHESES, trial.columns)
        self.assertNotIn(7, sparse.acquired_steps)
        self.assertEqual(sparse.status, "AUTHORIZED")
        self.assertEqual(sparse.accepted_bin, 0)
        audit_jitter_trial(trial, sparse, baseline)

    def test_random_small_plans_match_independent_oracle(self):
        rng = random.Random(1409)
        candidates = (0, 4, 8, 12)
        times = tuple(range(1, 9))
        for _ in range(100):
            reference = tuple(rng.getrandbits(8) for _ in range(16))
            for jitter in (0, 1):
                p = compile_jitter_witnesses(reference, candidates, times, 1, jitter)
                oracle = brute_force_jitter_plan(reference, candidates, times, 1, jitter)
                self.assertEqual(p.steps if p.status=="SEPARATING_SET" else None,
                                 oracle)

    def test_all_radius_two_observations_and_allowed_jitters_are_safe(self):
        t = generate_jitter_trial(5, kind="wide")
        self.assertEqual(exhaust_jitter_observations(t.reference), 675684)

    def test_beyond_bound_timing_outage_is_not_treated_as_proven(self):
        t = generate_jitter_trial(5, true_bin=16, kind="wide")
        # A non-physical 7-bin timing slip exceeds the declared +/-1 support.
        cols = list(t.columns)
        offsets = list(t.timing_offsets)
        offsets[13] = 7
        cols[13] = t.physical_source[(t.true_bin + 13 + offsets[13]) % 64]
        broken = replace(t, columns=tuple(cols), timing_offsets=tuple(offsets))
        with self.assertRaisesRegex(AssertionError,"TIMING_BOUND_BROKEN"):
            audit_jitter_trial(broken,
                               run_jitter_acquired(broken.reference, HYPOTHESES, broken.columns),
                               run_jitter_continuous(broken.reference, HYPOTHESES, broken.columns))

    def test_scene_swap_remains_undetectable_if_it_mimics_another_candidate(self):
        trial = generate_jitter_trial(5, true_bin=0, kind="wide")
        wrong=16
        spoof=tuple(trial.reference[(wrong+step)%64] for step in range(len(trial.columns)))
        mutated=replace(trial,columns=spoof,timing_offsets=(0,)*len(spoof))
        acquired=run_jitter_acquired(mutated.reference,HYPOTHESES,mutated.columns)
        conventional=run_jitter_continuous(mutated.reference,HYPOTHESES,mutated.columns)
        self.assertEqual(acquired.accepted_bin,wrong)
        self.assertEqual(conventional.accepted_bin,wrong)
        with self.assertRaisesRegex(AssertionError,"RUNTIME_ERROR_BOUND_BROKEN"):
            audit_jitter_trial(mutated,acquired,conventional)


if __name__ == "__main__":
    unittest.main()
