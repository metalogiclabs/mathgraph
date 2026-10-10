import unittest

from openai_math_audit import git_blob_sha
from openai_math_logspace_imports import audit, strip_comments


def fixtures():
    return {
        "Equality": b"import OAI.Computability.Logspace.Alpha\nimport Mathlib\n\nnamespace A\nend A\n",
        "Alpha": b"import OAI.Computability.Logspace.Beta\n-- sorry\n/- outer axiom /- nested admit -/ unsafe -/\n",
        "Beta": b"import Mathlib.NumberTheory.Bertrand\n",
    }


def evaluate(files):
    manifest = {name: git_blob_sha(data) for name, data in files.items()}
    return audit(manifest, lambda name: files[name])


class LogspaceImportAuditTests(unittest.TestCase):
    def test_closure_terminates_with_no_false_comment_signals(self):
        r = evaluate(fixtures())
        self.assertEqual(r["modules_in_import_closure"], 3)
        self.assertEqual(r["status"], "STATIC_IMPORT_CLOSURE_NO_LEXICAL_RISK_SIGNALS")
        self.assertEqual(r["main_theorem_status"], "UNKNOWN_INDEPENDENT_LEAN_REPLAY")

    def test_linguistic_sorry_is_not_considered_proof(self):
        d = fixtures()
        d["Alpha"] += b"theorem fake : True := by sorry\n"
        r = evaluate(d)
        self.assertEqual(r["status"], "STATIC_IMPORT_CLOSURE_WITH_RISK_SIGNALS")
        self.assertIn("sorry", [x["token"] for x in r["modules"]["Alpha"]["lexical_risk_signals"]])

    def test_module_insertion_fails_when_not_in_pinned_tree(self):
        d = fixtures()
        d["Alpha"] = b"import OAI.Computability.Logspace.Nonexistent\n"
        with self.assertRaisesRegex(ValueError, "MISSING_PINNED_MODULE"):
            evaluate(d)

    def test_mutated_blob_rejected(self):
        d = fixtures()
        manifest = {name: git_blob_sha(src) for name, src in d.items()}
        d["Beta"] += b" \n"
        with self.assertRaisesRegex(ValueError, "BLOB_SHA_MISMATCH"):
            audit(manifest, lambda name: d[name])

    def test_unexpected_external_import_requires_review(self):
        d = fixtures()
        d["Alpha"] += b"import SomeUntrusted.NewModule\n"
        self.assertEqual(evaluate(d)["status"], "STATIC_IMPORT_CLOSURE_WITH_RISK_SIGNALS")

    def test_nested_comments_and_line_positions(self):
        s = "theorem x := by trivial\n/- axiom /- sorry -/ admit -/\n-- unsafe\n"
        clean = strip_comments(s)
        self.assertNotIn("sorry", clean)
        self.assertNotIn("axiom", clean)
        self.assertEqual(clean.count("\n"), s.count("\n"))

    def test_unterminated_nested_comment_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UNTERMINATED_BLOCK_COMMENT"):
            strip_comments("import Mathlib\n/- unknown")

    def test_cycles_terminate(self):
        d = fixtures()
        d["Beta"] += b"import OAI.Computability.Logspace.Equality\n"
        self.assertEqual(evaluate(d)["modules_in_import_closure"], 3)


if __name__ == "__main__":
    unittest.main()
