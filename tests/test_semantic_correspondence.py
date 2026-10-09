"""Frozen semantic-separator fixtures from arXiv:2610.08144v1.

The sources and protected scopes were extracted by manual PDF/Lean inspection.
These tests do not authenticate the source extraction or prove source mathematics.
"""
import unittest

from mathgraph.semantic_correspondence import (
    ArgumentStatus, ClaimContract, ContractStatus, compare_protected_contracts,
)
from mathgraph.semantic_validation import (
    FormalClaim, InformalClaim, SemanticValidationEvidence,
    SemanticValidationStatus, validate_claim_translation,
)

PAPER = "arxiv:2610.08144v1"
LEAN = "openai/NavierStokesAndEuler@f9e8bc5"


class SemanticCorrespondenceRegression(unittest.TestCase):
    def test_legacy_evidence_presence_does_not_establish_equivalence(self):
        legacy = validate_claim_translation(
            InformalClaim("p8.19", "Inverse estimate loses four derivatives"),
            FormalClaim("inverse", "Inverse estimate loses five derivatives", "Lean4"),
            evidence=(SemanticValidationEvidence("paper", "source_document_reference"),),
        )
        # This is the observed historical behavior, NOT proof of equivalence.
        # Observe but do not freeze the older permissive behavior as a requirement.
        # A future conservative change to the legacy gate must not fail this test.
        if legacy.status == SemanticValidationStatus.VALIDATED:
            self.assertTrue(legacy.ok)
        audit = compare_protected_contracts(
            ClaimContract(PAPER + "#eq8.19", {"loss": 4, "torus_dimension": 2}),
            ClaimContract(LEAN + "#norm_derivativeWord_inverse_le",
                          {"loss": 5, "torus_dimension": 2}),
            ("torus_dimension", "loss"),
        )
        self.assertEqual(audit.status, ContractStatus.DIVERGENT)
        self.assertEqual(audit.mismatches, ("loss",))
        self.assertFalse(audit.can_promote_truth)

    def test_pressure_flux_added_gradient_dependency(self):
        audit = compare_protected_contracts(
            ClaimContract(PAPER + "#eq10.19",
                          {"rhs_dependencies": ("B_R",), "spatial_dimension": 3},
                          "L3/2_Riesz_transform"),
            ClaimContract(LEAN + "#exists_uniform_actual_pressure_flux_bound",
                          {"rhs_dependencies": ("A_R", "B_R"), "spatial_dimension": 3},
                          "L2_Riesz_transform_with_Sobolev"),
            ("spatial_dimension", "rhs_dependencies"),
        )
        self.assertEqual(audit.status, ContractStatus.DIVERGENT)
        self.assertEqual(audit.mismatches, ("rhs_dependencies",))
        self.assertEqual(audit.argument_status, ArgumentStatus.DIFFERENT)
        self.assertFalse(audit.can_promote_truth)

    def test_empty_infimum_hidden_presupposition(self):
        audit = compare_protected_contracts(
            ClaimContract(PAPER + "#example4.1",
                          {"least_witness_must_exist": True,
                           "empty_set_has_default": False}),
            ClaimContract(PAPER + "#example4.3-Lean-sInf",
                          {"least_witness_must_exist": False,
                           "empty_set_has_default": True}),
            ("least_witness_must_exist", "empty_set_has_default"),
        )
        self.assertEqual(audit.status, ContractStatus.DIVERGENT)
        self.assertEqual(len(audit.mismatches), 2)

    def test_same_theorem_different_proof_is_not_faithful_argument(self):
        audit = compare_protected_contracts(
            ClaimContract(PAPER + "#example2.2",
                          {"goal": "symmetric_trace_square_nonnegative",
                           "domain": "real_symmetric_matrix"},
                          "orthonormal_diagonalization"),
            ClaimContract(PAPER + "#figure2",
                          {"goal": "symmetric_trace_square_nonnegative",
                           "domain": "real_symmetric_matrix"},
                          "direct_sum_of_squares"),
            ("domain", "goal"),
        )
        self.assertEqual(audit.status, ContractStatus.AGREES)
        self.assertEqual(audit.argument_status, ArgumentStatus.DIFFERENT)
        self.assertFalse(audit.can_promote_truth)

    def test_missing_critical_dimension_stays_unknown(self):
        audit = compare_protected_contracts(
            ClaimContract("independent:page", {"bound": "4"}),
            ClaimContract("pinned:code", {}),
            ("bound",),
        )
        self.assertEqual(audit.status, ContractStatus.UNKNOWN)
        self.assertEqual(audit.missing_dimensions, ("bound",))
        self.assertFalse(audit.can_promote_truth)

    def test_scope_cannot_be_empty(self):
        with self.assertRaises(ValueError):
            compare_protected_contracts(
                ClaimContract("a", {"x": 1}),
                ClaimContract("b", {"x": 1}),
                (),
            )

    def test_a_matching_numeric_contract_is_not_a_semantic_certificate(self):
        audit = compare_protected_contracts(
            ClaimContract("source", {"loss": 4}),
            ClaimContract("formal", {"loss": 4}),
            ("loss",),
        )
        self.assertEqual(audit.status, ContractStatus.AGREES)
        self.assertFalse(audit.can_promote_truth)


if __name__ == "__main__":
    unittest.main()
