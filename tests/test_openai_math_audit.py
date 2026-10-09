import json
import unittest

from openai_math_audit import FILES, THEOREM, audit, git_blob_sha

CHALLENGE = "namespace OAI\ntheorem exact_logarithmic_space_derandomization :\n  L = RL ∧ RL = BPL := by\n  sorry\n"
SOLUTION = "theorem exact_logarithmic_space_derandomization :\n     L=RL ∧ RL=BPL:=by\n   exact witness\n"
COMPARATOR = json.dumps({"solution_module": "OAI.Computability.Logspace.Equality", "theorem_names": [THEOREM], "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"]})
NOTICE = "Withdrawn on October 6, 2026. This withdrawal concerns the proof; it does not assert that the mathematical statement is false."
ROOT = NOTICE + " sign error I_{\\mathrm{new}}=-2m; Eliashberg-Murphy zero signed double-point count"
DEPENDENT = NOTICE + " relies on flawed stabilization-trace construction"

def fixtures():
    return {
        FILES[k][0]: v.encode() for k, v in {
            "weil": ROOT, "kuga_satake": DEPENDENT, "hodge_k3": DEPENDENT,
            "challenge": CHALLENGE, "solution": SOLUTION, "comparator": COMPARATOR,
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

if __name__ == "__main__":
    unittest.main()
