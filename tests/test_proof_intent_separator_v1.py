"""Frozen observable contracts for the proof-to-intent separator experiment.

These expectations are hand-derived independently of the candidate implementation.
"""

import unittest

from experiments.proof_intent_separator_v1.separator import (
    assess_threshold_claim,
    assess_compression_claim,
    identity,
    tiny_run_compress,
    tiny_run_decompress,
)


class ProofIntentSeparatorTests(unittest.TestCase):
    def test_valid_weakened_scope_proof_does_not_warrant_false_intent(self):
        # Break caught: treating a valid n >= 3 result as an n >= 1 result.
        report = assess_threshold_claim(source_min=1, proof_min=3, upper_bound=12)
        self.assertEqual(report["formal_finite_check"], "PASS")
        self.assertEqual(report["intent_finite_check"], "COUNTEREXAMPLE")
        self.assertEqual(report["counterexample"], 1)
        self.assertFalse(report["action_authorized"])

    def test_cheapest_guard_is_a_candidate_not_an_automatic_edit(self):
        # Break caught: taking the proof's stronger guard, or automatically altering source intent.
        report = assess_threshold_claim(source_min=1, proof_min=3, upper_bound=12)
        self.assertEqual(report["minimal_repair_guard"], "n >= 2")
        self.assertEqual(report["repair_status"], "CANDIDATE_REQUIRES_SOURCE_APPROVAL_AND_PROOF")
        self.assertEqual(report["retained_proof_guard"], "n >= 3")

    def test_match_and_nonproof_cases_remain_distinct(self):
        # Break caught: calling a finite positive check a global theorem or a valid proof refuted.
        matched = assess_threshold_claim(source_min=3, proof_min=3, upper_bound=12)
        self.assertEqual(matched["intent_finite_check"], "FINITE_SUPPORTED_ONLY")
        self.assertEqual(matched["formal_finite_check"], "PASS")
        self.assertFalse(matched["action_authorized"])
        bad_proof = assess_threshold_claim(source_min=1, proof_min=1, upper_bound=12)
        self.assertEqual(bad_proof["formal_finite_check"], "COUNTEREXAMPLE")
        self.assertEqual(bad_proof["counterexample"], 1)

    def test_missing_domain_observation_is_unknown_not_true(self):
        # Break caught: vacuous bounded evidence promoting an unobserved infinite tail.
        report = assess_threshold_claim(source_min=1, proof_min=3, upper_bound=0)
        self.assertEqual(report["intent_finite_check"], "UNKNOWN_NO_ADMITTED_SOURCE_CASES")
        self.assertIsNone(report["counterexample"])
        self.assertFalse(report["action_authorized"])

    def test_vacuous_proof_scope_does_not_count_as_a_positive_observation(self):
        # Break caught: reporting an empty admitted proof domain as supportive evidence.
        report = assess_threshold_claim(source_min=1, proof_min=20, upper_bound=12)
        self.assertEqual(report["formal_finite_check"], "UNKNOWN_VACUOUS_FORMAL_SCOPE")
        self.assertEqual(report["observed_proof_cases"], 0)
        self.assertFalse(report["action_authorized"])

    def test_invalid_nat_bounds_are_rejected(self):
        # Break caught: accidentally extending a Nat theorem to negative observations.
        with self.assertRaises(ValueError):
            assess_threshold_claim(source_min=-1, proof_min=3, upper_bound=12)

    def test_identity_roundtrip_proof_is_insufficient_compression_spec(self):
        # Break caught: a kernel-admitted identity roundtrip being labelled useful compression.
        report = assess_compression_claim(identity, identity)
        self.assertTrue(report["roundtrip_finite_pass"])
        self.assertEqual(report["size_counterexample"], "0000")
        self.assertFalse(report["release_authorized"])

    def test_nontrivial_reference_compressor_passes_same_intent(self):
        # Break caught: rejecting every implementation regardless of independent observations.
        report = assess_compression_claim(tiny_run_compress, tiny_run_decompress)
        self.assertTrue(report["roundtrip_finite_pass"])
        self.assertIsNone(report["size_counterexample"])
        self.assertEqual(report["size_finite_check"], "FINITE_SUPPORTED_ONLY")
        self.assertFalse(report["release_authorized"])

    def test_wrong_decompressor_cannot_hide_behind_smaller_output(self):
        # Break caught: checking just the performance property without the protected roundtrip.
        report = assess_compression_claim(tiny_run_compress, identity)
        self.assertFalse(report["roundtrip_finite_pass"])
        self.assertEqual(report["roundtrip_counterexample"], "0000")
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
