"""Independent controls for a pinned, already-documented AnnalsChallenge gap."""

import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from experiments.annals_source_intent_v1.audit import (
    ANNALS_BLOB_SHA256,
    assess,
    bind_source,
    finite_singleton_countermodel,
)


class AnnalsSourceIntentV1Tests(unittest.TestCase):
    def test_real_frozen_source_is_bound_but_its_sorry_is_not_warrant(self):
        from experiments.annals_source_intent_v1.audit import locate_annals_source

        bound = bind_source(locate_annals_source())
        self.assertEqual(bound["state"], "SOURCE_BOUND")
        self.assertEqual(bound["sha256"], ANNALS_BLOB_SHA256)
        self.assertTrue(bound["has_formal_guard"])
        self.assertTrue(bound["has_sorry"])
        self.assertFalse(bound["theorem_proved"])

    def test_singleton_is_an_explicit_finite_countermodel_to_unguarded_bound(self):
        w = finite_singleton_countermodel()
        self.assertTrue(w["is_upward_closed"])
        self.assertEqual(w["max_minimal_size"], 1)
        self.assertEqual(w["critical_probability"], Fraction(1, 2))
        self.assertEqual(w["log_l"], 0)
        self.assertEqual(w["rhs_at_any_finite_constant"], 0)
        self.assertFalse(w["unguarded_bound_holds"])
        self.assertFalse(w["satisfies_formal_guard"])

    def test_outcome_distinguishes_a_countermodel_from_full_claim_certification(self):
        from experiments.annals_source_intent_v1.audit import locate_annals_source

        result = assess(locate_annals_source())
        self.assertEqual(result["terminal"], "FINITE_COUNTERMODEL")
        self.assertEqual(result["scope"], "SINGLETON_REDUCED_UNGUARDED_FORMULA")
        self.assertEqual(result["full_paper_theorem"], "UNKNOWN")
        self.assertEqual(result["paper_intent"], "UNKNOWN_CONTEXT_DEPENDENT")
        self.assertFalse(result["release_authorized"])

    def test_missing_source_withdraws_authority(self):
        result = assess(Path("/not/a/source/annals.lean"))
        self.assertEqual(result["terminal"], "NAMED_OBSTRUCTION")
        self.assertEqual(result["obstruction"], "SOURCE_MISSING")
        self.assertFalse(result["release_authorized"])

    def test_one_byte_source_change_withdraws_even_if_theorem_text_stays(self):
        from experiments.annals_source_intent_v1.audit import locate_annals_source

        original = locate_annals_source().read_bytes()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "changed.lean"
            path.write_bytes(original + b"\n")
            result = assess(path)
        self.assertEqual(result["terminal"], "NAMED_OBSTRUCTION")
        self.assertEqual(result["obstruction"], "SOURCE_DIGEST_DRIFT")
        self.assertFalse(result["release_authorized"])

    def test_unrelated_true_lean_statement_does_not_bind_to_claim(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "unrelated.lean"
            path.write_text("theorem unrelated : True := by trivial\n")
            result = assess(path)
        self.assertEqual(result["terminal"], "NAMED_OBSTRUCTION")
        self.assertEqual(result["obstruction"], "SOURCE_DIGEST_DRIFT")

    def test_baseline_with_all_the_same_facts_also_finds_counterexample(self):
        # Conventional, independent hand-derived baseline with full model access.
        support = (frozenset(), frozenset({0}))
        family = {frozenset({0})}
        probabilities = {support[0]: Fraction(1, 2), support[1]: Fraction(1, 2)}
        event_probability = sum((p for sample, p in probabilities.items()
                                 if sample in family), Fraction(0))
        maximal_minimal_size = min(map(len, family))
        ordinary_baseline_detects_false_unguarded = (
            maximal_minimal_size == 1 and event_probability > 0 and 0 == 0
        )
        self.assertTrue(ordinary_baseline_detects_false_unguarded)
        self.assertEqual(finite_singleton_countermodel()["critical_probability"], event_probability)


if __name__ == "__main__":
    unittest.main()
