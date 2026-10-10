"""Fail-closed and positive controls for MathGraph Check's public preflight boundary."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mathgraph_check import ManifestError, check_manifest, render_markdown


def fixture(source=None, formal=None):
    return {
        "schema": "mathgraph.check.v0",
        "title": "Bounded derivative-loss claim",
        "source_contract_origin": "MANUAL_UNREVIEWED",
        "source": source or {
            "anchor": "arxiv:2610.08144v1#eq8.19",
            "dimensions": {"loss": 4, "dimension": 2},
        },
        "formal": formal or {
            "anchor": "openai/NavierStokesAndEuler@f9e8bc5#inverse",
            "dimensions": {"loss": 5, "dimension": 2},
        },
        "protected_dimensions": ["dimension", "loss"],
    }


class MathGraphCheckV0Tests(unittest.TestCase):
    def test_explicit_loss_separator_is_not_truth_promotion(self):
        r = check_manifest(fixture())
        self.assertEqual(r["diagnostic"], "CANDIDATE_CONTRACT_DIVERGENCE")
        self.assertEqual(r["comparison"]["mismatches"], ["loss"])
        self.assertFalse(r["epistemic"]["truth_promotion"])
        self.assertEqual(r["epistemic"]["informal_to_formal_fidelity"], "UNKNOWN")
        self.assertEqual(r["epistemic"]["formal_kernel_verification"], "UNKNOWN_NOT_RUN_BY_CHECK_V0")
        self.assertEqual(r["epistemic"]["verified_badge"], "NOT_ISSUED")

    def test_equal_dimensions_still_do_not_certify_meaning(self):
        d = fixture()
        d["formal"]["dimensions"]["loss"] = 4
        r = check_manifest(d)
        self.assertEqual(r["diagnostic"], "NO_DECLARED_SEPARATOR_FOUND")
        self.assertEqual(r["comparison"]["status"], "SCOPED_AGREEMENT_SEMANTICS_UNKNOWN")
        self.assertEqual(r["epistemic"]["informal_to_formal_fidelity"], "UNKNOWN")

    def test_missing_dimension_is_unknown(self):
        d = fixture()
        del d["formal"]["dimensions"]["loss"]
        r = check_manifest(d)
        self.assertEqual(r["diagnostic"], "UNKNOWN_INCOMPLETE_CONTRACT")
        self.assertEqual(r["comparison"]["missing_dimensions"], ["loss"])

    def test_bool_integer_are_not_equivalent(self):
        d = fixture()
        d["source"]["dimensions"]["loss"] = True
        d["formal"]["dimensions"]["loss"] = 1
        self.assertEqual(check_manifest(d)["comparison"]["mismatches"], ["loss"])

    def test_proof_route_not_confused_with_statement(self):
        d = fixture()
        d["formal"]["dimensions"]["loss"] = 4
        d["source"]["argument_route"] = "diagonalization"
        d["formal"]["argument_route"] = "sum_of_squares"
        r = check_manifest(d)
        self.assertEqual(r["diagnostic"], "CANDIDATE_CONTRACT_DIVERGENCE")
        self.assertEqual(r["comparison"]["mismatches"], [])
        self.assertEqual(r["findings"][0]["code"], "DECLARED_ARGUMENT_ROUTE_MISMATCH")

    def test_exact_local_files_can_be_pinned(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            d = fixture()
            for side, body in (("source", b"assert bound four"),
                               ("formal", b"theorem bound five")):
                (root / f"{side}.txt").write_bytes(body)
                d[side]["file"] = side + ".txt"
                d[side]["sha256"] = hashlib.sha256(body).hexdigest()
            r = check_manifest(d, base_dir=root)
            self.assertEqual(r["source_pins"]["source"]["status"], "LOCAL_SHA256_CHECKED")
            self.assertEqual(r["source_pins"]["formal"]["status"], "LOCAL_SHA256_CHECKED")
            self.assertFalse(r["epistemic"]["truth_promotion"])
            (root / "formal.txt").write_bytes(b"tampered")
            with self.assertRaisesRegex(ManifestError, "SHA256_MISMATCH"):
                check_manifest(d, base_dir=root)

    def test_relative_path_cannot_escape_manifest(self):
        d = fixture()
        d["source"]["file"] = "../outside"
        d["source"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ManifestError, "escapes"):
            check_manifest(d, base_dir=".")

    def test_user_cannot_self_declare_a_verified_proof(self):
        d = fixture()
        d["formal_verification"] = "WARRANTED"
        with self.assertRaisesRegex(ManifestError, "unsupported top-level"):
            check_manifest(d)

    def test_manual_contract_origin_is_mandatory(self):
        d = fixture()
        d["source_contract_origin"] = "INDEPENDENTLY_VERIFIED"
        with self.assertRaisesRegex(ManifestError, "MANUAL_UNREVIEWED"):
            check_manifest(d)

    def test_reject_invalid_values_and_scope(self):
        d = fixture()
        d["formal"]["dimensions"]["loss"] = 5.0
        with self.assertRaisesRegex(ManifestError, "unsupported value"):
            check_manifest(d)
        d = fixture()
        d["protected_dimensions"] = ["loss", "loss"]
        with self.assertRaisesRegex(ManifestError, "unique"):
            check_manifest(d)

    def test_stable_report_id_and_html_escaped_markdown(self):
        d = fixture()
        d["title"] = "<script>alert('oops')</script>"
        r = check_manifest(d)
        reordered = json.loads(json.dumps(d, sort_keys=True))
        self.assertEqual(check_manifest(reordered)["input_sha256"], r["input_sha256"])
        m = render_markdown(r)
        self.assertNotIn("<script>", m)
        self.assertIn("&lt;script&gt;", m)

    def test_cli_publishes_json_and_markdown_without_extra_dependencies(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            path = root / "claim.json"
            path.write_text(json.dumps(fixture()))
            result = subprocess.run([
                sys.executable, "-m", "mathgraph_check", str(path),
                "--json", str(root / "report.json"), "--markdown", str(root / "report.md"),
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            r = json.loads((root / "report.json").read_text())
            self.assertEqual(r["diagnostic"], "CANDIDATE_CONTRACT_DIVERGENCE")
            self.assertIn("Truth", (root / "report.md").read_text().replace("truth", "Truth"))
            self.assertFalse(r["epistemic"]["truth_promotion"])


if __name__ == "__main__":
    unittest.main()
