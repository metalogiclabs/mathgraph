"""Qualification provenance controls; no fabricated native observations."""
from pathlib import Path
import copy
import hashlib
import subprocess
import tempfile
import unittest

from qualify import REQUIRED_FILES, require_same_method, verifier_identity


class QualificationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        for name in REQUIRED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("qualification fixture\n")
        self.git("add", ".")
        self.git("-c", "user.name=Check Test", "-c", "user.email=check-test@example.invalid",
                 "commit", "-qm", "committed verifier inputs")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def test_clean_inputs_have_actual_commit_tree_and_qualifier_identity(self):
        identity = verifier_identity(self.root)
        self.assertEqual(identity["commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(identity["tree"], self.git("rev-parse", "HEAD^{tree}"))
        self.assertEqual(identity["qualifier_sha256"],
                         hashlib.sha256((self.root / REQUIRED_FILES[2]).read_bytes()).hexdigest())

    def test_dirty_input_cannot_borrow_committed_verifier_identity(self):
        (self.root / REQUIRED_FILES[1]).write_text("changed native method\n")
        with self.assertRaisesRegex(RuntimeError, "NOT_COMMITTED_AND_CLEAN"):
            verifier_identity(self.root)

    def test_untracked_checker_dependency_is_not_in_frozen_commit(self):
        (self.root / REQUIRED_FILES[0]).with_name("new-helper.mjs").write_text("new method\n")
        with self.assertRaisesRegex(RuntimeError, "NOT_COMMITTED_AND_CLEAN"):
            verifier_identity(self.root)

    def test_equal_plan_and_corpus_do_not_hide_a_changed_driver(self):
        original = {"method": {"plan_sha256": "plan", "corpus_sha256": "corpus",
                              "files": {"local-report-native.py": "original"}}}
        changed = copy.deepcopy(original)
        changed["method"]["files"]["local-report-native.py"] = "changed"
        require_same_method([original, copy.deepcopy(original)])
        with self.assertRaisesRegex(RuntimeError, "METHOD_CHANGED_BETWEEN_RUNS"):
            require_same_method([original, changed])


if __name__ == "__main__":
    unittest.main()
