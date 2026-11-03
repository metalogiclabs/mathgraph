"""Re-check the original Rust native evidence before admitting a route."""
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from brahe_export import export_brahe_boundary, verify_brahe_logs
from mathgraph_check.boundary_warrant import admitted_route, resolve_boundaries


@unittest.skipUnless(
    all(os.environ.get(x) for x in (
        "MATHGRAPH_BRAHE_ARTIFACT_ZIP", "MATHGRAPH_BRAHE_BASE_SOURCE",
        "MATHGRAPH_BRAHE_HEAD_SOURCE")),
    "Requires exact Brahe Actions artifact and two pinned source blobs",
)
class BraheNativeArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip = Path(os.environ["MATHGRAPH_BRAHE_ARTIFACT_ZIP"])
        cls.base = Path(os.environ["MATHGRAPH_BRAHE_BASE_SOURCE"])
        cls.head = Path(os.environ["MATHGRAPH_BRAHE_HEAD_SOURCE"])

    def test_real_base_fail_head_pass_is_native_not_formal(self):
        warrant, receipt, assessment = export_brahe_boundary(
            self.zip, self.base, self.head)
        self.assertEqual(warrant.verification.method, "native")
        self.assertEqual(warrant.obligation.authority, "PR_TEST_DECLARED; NOT_CUSTOMER_APPROVED")
        self.assertEqual(warrant.conclusion.status, "SUPPORTED")
        self.assertEqual(assessment["base_failures"], 4)
        self.assertEqual(assessment["head_failures"], 0)
        current = {d.key: d.sha256 for d in warrant.dependencies}
        result = resolve_boundaries([(warrant, receipt)], current)
        self.assertEqual(result.states[admitted_route(warrant, receipt)[0].id],
                         "WARRANTED_BOUNDED_NATIVE")

    def test_archive_tamper_is_rejected_without_trusting_written_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            changed = Path(td) / "fake-success.zip"
            with zipfile.ZipFile(self.zip) as zin, zipfile.ZipFile(changed, "w") as zout:
                for entry in zin.infolist():
                    body = zin.read(entry.filename)
                    if entry.filename == "brahe-retrospective-receipt.json":
                        body = body.replace(b"CANDIDATE_BOUNDED", b"WARRANTED_BOUNDED")
                    zout.writestr(entry, body)
            with self.assertRaisesRegex(ValueError, "ARTIFACT_IDENTITY_MISMATCH"):
                export_brahe_boundary(changed, self.base, self.head)

    def test_source_changed_or_transplant_wrong_cannot_admit(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_MISMATCH"):
            export_brahe_boundary(self.zip, self.head, self.base)
        with tempfile.TemporaryDirectory() as td:
            forged = Path(td) / "modified.rs"
            forged.write_bytes(self.head.read_bytes() + b"\n// modified source\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_MISMATCH"):
                export_brahe_boundary(self.zip, self.base, forged)

    def test_negative_control_requires_assertion_failure_not_compile_error(self):
        with zipfile.ZipFile(self.zip) as archive:
            stdout = archive.read("brahe-base.stdout").decode()
            stderr = archive.read("brahe-base.stderr").decode()
        assert verify_brahe_logs(stdout, stderr, 101, "base")["regressions"] == 4
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_NATIVE_REGRESSION"):
            verify_brahe_logs(stdout.replace(
                "test events::detection::tests::test_sscan_rejects_decreasing_detector_at_increasing_endpoint ... FAILED",
                "test events::detection::tests::test_sscan_rejects_decreasing_detector_at_increasing_endpoint ... ok",
            ), stderr, 101, "base")
        with self.assertRaisesRegex(ValueError, "NATIVE_SETUP_FAILURE"):
            verify_brahe_logs(stdout, stderr + "\nerror[E0432]: unresolved import\n",
                              101, "base")


if __name__ == "__main__":
    unittest.main()
