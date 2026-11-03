"""The historical native Lean result must be re-admitted, never label-copied."""
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from boundary_export import export_l4_boundary
from mathgraph_check.boundary_warrant import admitted_route, resolve_boundaries


@unittest.skipUnless(os.environ.get("MATHGRAPH_L4_CLAIM_ARTIFACT_ZIP"),
                     "Requires exact GitHub Actions artifact #13214576201")
class NativeArtifactBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = Path(os.environ["MATHGRAPH_L4_CLAIM_ARTIFACT_ZIP"])

    def test_exact_artifact_admits_strong_consumer_and_retains_weak_rejection(self):
        warrant, receipt, checks = export_l4_boundary(self.artifact)
        self.assertEqual(warrant.verification.method, "formal")
        self.assertEqual(warrant.verification.assumptions, ("propext",))
        self.assertEqual(warrant.obligation.authority, "UPSTREAM_PR_DECLARED; RETROSPECTIVE_NOT_NEW_DISCOVERY")
        self.assertEqual(warrant.conclusion.status, "SUPPORTED")
        self.assertEqual(checks["weak_offering"], "REJECTED_AS_SUPPORT_FOR_STRONG_OBLIGATION")
        self.assertEqual(checks["axiom_free_claim"], "REJECTED")
        current = {x.key: x.sha256 for x in warrant.dependencies}
        result = resolve_boundaries([(warrant, receipt)], current)
        self.assertEqual(result.states[admitted_route(warrant, receipt)[0].id],
                         "WARRANTED_BOUNDED")

    def test_modified_artifact_is_unknown_even_if_it_contains_success_labels(self):
        with tempfile.TemporaryDirectory() as td:
            changed = Path(td) / "claimed-success.zip"
            with zipfile.ZipFile(self.artifact) as zin, zipfile.ZipFile(changed, "w") as zout:
                for entry in zin.infolist():
                    data = zin.read(entry.filename)
                    if entry.filename == "claim-results/assessment.json":
                        data = data.replace(b"WARRANTED_BOUNDED", b"WARRANTED_BOUNDEx")
                    zout.writestr(entry, data)
            with self.assertRaisesRegex(ValueError, "ARTIFACT_IDENTITY_MISMATCH"):
                export_l4_boundary(changed)

    def test_only_recorded_proof_assumptions_are_exported(self):
        warrant, _, checks = export_l4_boundary(self.artifact)
        self.assertNotIn("sorryAx", warrant.verification.assumptions)
        self.assertEqual(checks["whole_generator_correctness"], "UNKNOWN")
        self.assertFalse(checks["fresh_discovery"])


if __name__ == "__main__":
    unittest.main()
