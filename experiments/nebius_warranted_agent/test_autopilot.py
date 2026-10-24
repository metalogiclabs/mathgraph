"""Adversarial finite regression suite; unittest + standard library only."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import unittest

from autopilot import (SOURCE, TESTS, Proposal, ScriptedProvider, apply_code,
                       drive, execute_tests, qualify, snapshot, validate_repair_ast)

GOOD = '''def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))
'''


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "calculator.py").write_text(GOOD)
        (self.root / "test_calculator.py").write_text(TESTS)
        self.source = snapshot(self.root)
        self.receipt, self.output = execute_tests(self.root, self.source)
        self.assertEqual(self.receipt.exit_code, 0, self.output)

    def test_correct_receipt_warrants_only_declared_tests(self):
        self.assertEqual(qualify(self.root, self.source, self.receipt)[0], "WARRANTED")

    def test_no_receipt_is_unknown(self):
        self.assertEqual(qualify(self.root, self.source, None)[0], "UNKNOWN")

    def test_changed_artifact_with_previous_pass_is_rejected(self):
        (self.root / "calculator.py").write_text(GOOD + "\n# mutation\n")
        self.assertEqual(qualify(self.root, self.source, self.receipt)[0], "REJECTED")

    def test_changed_protected_tests_rejected(self):
        (self.root / "test_calculator.py").write_text("# removed tests")
        self.assertEqual(qualify(self.root, self.source, self.receipt)[0], "REJECTED")

    def test_foreign_revision_rejected(self):
        self.assertEqual(qualify(self.root, "different", self.receipt)[0], "REJECTED")

    def test_altered_runner_rejected(self):
        self.assertEqual(qualify(self.root, self.source, replace(self.receipt, runner="echo okay"))[0], "REJECTED")

    def test_nonzero_exit_rejected(self):
        self.assertEqual(qualify(self.root, self.source, replace(self.receipt, exit_code=1))[0], "REJECTED")

    def test_incomplete_run_unknown(self):
        r = replace(self.receipt, outcome="timeout", exit_code=None)
        self.assertEqual(qualify(self.root, self.source, r)[0], "UNKNOWN")

    def test_changed_while_testing_rejected(self):
        r = replace(self.receipt, after_sha256="wrong")
        self.assertEqual(qualify(self.root, self.source, r)[0], "REJECTED")

    def test_nonregular_file_rejected(self):
        (self.root / "calculator.py").unlink()
        self.assertEqual(qualify(self.root, self.source, self.receipt)[0], "REJECTED")

    def test_failing_tests_never_warrant(self):
        (self.root / "calculator.py").write_text(SOURCE)
        receipt, _ = execute_tests(self.root, self.source)
        self.assertEqual(qualify(self.root, self.source, receipt)[0], "REJECTED")

    def test_protect_test_bytes_on_patch(self):
        (self.root / "test_calculator.py").write_text("tampered")
        p = Proposal(GOOD, "scripted", "none", "digest", None, "now")
        with self.assertRaisesRegex(ValueError, "protected test"):
            apply_code(self.root, p, hashlib.sha256(TESTS.encode()).hexdigest())

    def test_reject_import_side_effect_and_unsafe_builtin(self):
        for code in [
            "import os\n" + GOOD,
            "def clamp(value, minimum, maximum):\n    return open('/tmp/x')\n",
            "def clamp(value, minimum, maximum):\n    return __import__('os')\n",
            "def clamp(value, minimum, maximum):\n    return value.__class__\n",
            "def clamp(value, minimum, maximum):\n    exec('x=1')\n    return value\n",
        ]:
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    validate_repair_ast(code)

    def test_scripted_two_repair_attempts_then_withdrawal(self):
        report = drive(ScriptedProvider())
        self.assertEqual(report["final_state"], "WARRANTED")
        self.assertEqual([(e["step"], e["state"]) for e in report["events"]], [
            ("initial_failure", "REJECTED"),
            ("repair_attempt", "REJECTED"),
            ("repair_attempt", "WARRANTED"),
            ("post_test_mutation", "REJECTED"),
            ("reacquire", "WARRANTED"),
        ])
        self.assertEqual(report["events"][2]["proposal"]["provider"], "SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS")

    def test_inadequate_attempt_budget_never_authorizes(self):
        report = drive(ScriptedProvider(), max_attempts=1)
        self.assertEqual(report["final_state"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
