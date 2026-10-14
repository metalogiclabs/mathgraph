import json
import unittest

from openai_math_audit import FILES, PAPER_AND_BUILD, THEOREM, EXPECTED_MATHLIB, EXPECTED_LEAN, audit, git_blob_sha

CHALLENGE = "namespace OAI\ntheorem exact_logarithmic_space_derandomization :\n  L = RL ∧ RL = BPL := by\n  sorry\n"
SOLUTION = "theorem exact_logarithmic_space_derandomization :\n     L=RL ∧ RL=BPL:=by\n   exact witness\n"
COMPARATOR = json.dumps({"solution_module": "OAI.Computability.Logspace.Equality", "theorem_names": [THEOREM], "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"]})
NOTICE = "Withdrawn on October 6, 2026. This withdrawal concerns the proof; it does not assert that the mathematical statement is false."
ROOT = NOTICE + " sign error I_{\\mathrm{new}}=-2m; Eliashberg-Murphy zero signed double-point count"
DEPENDENT = NOTICE + " relies on flawed stabilization-trace construction"

PAPER_INTRO = ("We use machines with finitely many work tapes, and fresh independent fair bits. "
    "All randomized running-time bounds hold on every random tape. "
    "visiting a blank work cell counts toward space. "
    "at least $1/2$ on yes inputs, and at most $1/3$ and at least $2/3$ otherwise.")
PAPER_MODEL = "Configuration reduction for exact acceptance probability."
BUILD_MANIFEST = json.dumps({"packages": [{"name": "mathlib", "rev": EXPECTED_MATHLIB}]})
BUILD_LAKEFILE = "require mathlib from git\n" + EXPECTED_MATHLIB

def fixtures():
    return {
        FILES[k][0]: v.encode() for k, v in {
            "weil": ROOT, "kuga_satake": DEPENDENT, "hodge_k3": DEPENDENT,
            "challenge": CHALLENGE + "\nabbrev CoinTape := ℕ → Bool\ndef LogSpace := True\ndef RL : Set Language := none\ndef BPL : Set Language := none\ndef polynomialClock := 0\n", "solution": SOLUTION, "comparator": COMPARATOR,
            "paper_intro": PAPER_INTRO, "paper_model": PAPER_MODEL,
            "lean_toolchain": EXPECTED_LEAN, "lake_manifest": BUILD_MANIFEST, "lakefile": BUILD_LAKEFILE,
        }.items()
    }

def run_fixture(data):
    return audit(lambda path: data[path], check_hashes=False)

class OpenAIMathEvidenceAuditTests(unittest.TestCase):
    def test_git_blob_hash_is_content_bound(self):
        self.assertEqual(git_blob_sha(b"test content\n"), "d670460b4b4aece5915caf5c68d12f560a9fe3e4")

    def test_source_limited_success_does_not_claim_proof(self):
        result = run_fixture(fixtures())
        self.assertEqual(result["logspace"]["status"], "UNKNOWN_INDEPENDENT_LEAN_REPLAY")
        self.assertEqual(result["withdrawals"]["hodge_k3"]["depends_on"], "weil")

    def test_missing_dependency_fails(self):
        d = fixtures()
        d[FILES["hodge_k3"][0]] = NOTICE.encode()
        with self.assertRaisesRegex(ValueError, "DECLARED_DEPENDENCY_MISSING"):
            run_fixture(d)

    def test_missing_root_sign_witness_fails(self):
        d = fixtures()
        d[FILES["weil"][0]] = NOTICE.encode()
        with self.assertRaisesRegex(ValueError, "ROOT_WITNESS_MISSING"):
            run_fixture(d)

    def test_solution_sorry_fails(self):
        d = fixtures()
        d[FILES["solution"][0]] += b"\nsorry\n"
        with self.assertRaisesRegex(ValueError, "SOLUTION_FILE_CONTAINS_UNVERIFIED_SYNTAX"):
            run_fixture(d)

    def test_undeclared_axiom_change_fails(self):
        d = fixtures()
        c = json.loads(d[FILES["comparator"][0]])
        c["permitted_axioms"].append("new_axiom")
        d[FILES["comparator"][0]] = json.dumps(c).encode()
        with self.assertRaisesRegex(ValueError, "AXIOM_POLICY_CHANGED"):
            run_fixture(d)

    def test_wrong_blob_is_rejected(self):
        d = fixtures()
        with self.assertRaisesRegex(ValueError, "PIN_MISMATCH"):
            audit(lambda path: d[path], check_hashes=True)

    def test_paper_vs_formal_scope_negative(self):
        d = fixtures()
        path = FILES["paper_intro"][0]
        d[path] = d[path].replace(b"fresh independent fair bits", b"unspecified randomness")
        with self.assertRaisesRegex(ValueError, "PAPER_SCOPE_TEXT_CHANGED"):
            run_fixture(d)

    def test_toolchain_drift_negative(self):
        d = fixtures()
        d[FILES["lean_toolchain"][0]] = b"leanprover/lean4:v4.35.0-rc4"
        with self.assertRaisesRegex(ValueError, "LEAN_TOOLCHAIN_DRIFT"):
            run_fixture(d)

    def test_manifest_mathlib_drift_negative(self):
        d = fixtures()
        m = json.loads(d[FILES["lake_manifest"][0]])
        m["packages"][0]["rev"] = "0" * 40
        d[FILES["lake_manifest"][0]] = json.dumps(m).encode()
        with self.assertRaisesRegex(ValueError, "MATHLIB_LOCK_DRIFT"):
            run_fixture(d)

    def test_lakefile_mathlib_drift_negative(self):
        d = fixtures()
        d[FILES["lakefile"][0]] = b"require mathlib from git\nchanged"
        with self.assertRaisesRegex(ValueError, "MATHLIB_DECLARED_PIN_DRIFT"):
            run_fixture(d)

    def test_missing_formal_model_anchor_negative(self):
        d = fixtures()
        key = FILES["challenge"][0]
        d[key] = d[key].replace(b"def polynomialClock", b"def otherClock")
        with self.assertRaisesRegex(ValueError, "FORMAL_MODEL_SURFACE_CHANGED"):
            run_fixture(d)

if __name__ == "__main__":
    unittest.main()
