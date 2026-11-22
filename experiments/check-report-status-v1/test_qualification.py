"""Actual Git candidate provenance and qualification failure controls."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "status_qualification", Path(__file__).with_name("qualify.py"))
Q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q)


class CandidateProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "subject"
        self.repo.mkdir()
        self.git("init", "-q")
        path = self.repo / Q.SOURCE_PATH
        path.parent.mkdir(parents=True)
        self.source = ("-- Committed test source\n" + Q.ORIGINAL_CONDITION + "\n").encode()
        path.write_bytes(self.source)
        (self.repo / "unrelated.txt").write_text("original unrelated content\n")
        self.git("add", ".")
        self.git("-c", "user.name=Qualification Test", "-c",
                 "user.email=qualification@example.invalid", "commit", "-qm", "original")
        self.original = self.git("rev-parse", "HEAD")
        self.original_blob = self.git("rev-parse", self.original + ":" + Q.SOURCE_PATH)
        self.candidate_source = self.source.replace(
            Q.ORIGINAL_CONDITION.encode(), Q.CANDIDATE_CONDITION.encode())
        self.pins = mock.patch.multiple(
            Q, ORIGINAL=self.original, ORIGINAL_BLOB=self.original_blob,
            ORIGINAL_SOURCE_SHA=hashlib.sha256(self.source).hexdigest(),
            CANDIDATE_SOURCE_SHA=hashlib.sha256(self.candidate_source).hexdigest())
        self.pins.start()
        self.addCleanup(self.pins.stop)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def test_candidate_has_actual_parent_and_only_one_changed_file_without_checkout(self):
        (self.repo / "unrelated.txt").write_text("caller staged content\n")
        self.git("add", "unrelated.txt")
        source_path = self.repo / Q.SOURCE_PATH
        source_path.write_text("caller uncommitted source\n")
        before = Q.repository_state(self.repo)
        status_before = self.git("status", "--porcelain", "--untracked-files=all")
        first_out = self.root / "first"
        second_out = self.root / "second"
        first_out.mkdir()
        second_out.mkdir()
        first = Q.prepare_candidate(self.repo, first_out)
        second = Q.prepare_candidate(self.repo, second_out)
        self.assertEqual(first["commit"], second["commit"])
        self.assertEqual(first["parent"], self.original)
        self.assertEqual(self.git("rev-list", "--parents", "-n", "1", first["commit"]),
                         first["commit"] + " " + self.original)
        self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r",
                                  self.original, first["commit"]), Q.SOURCE_PATH)
        self.assertEqual(Q.repository_state(self.repo), before)
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), status_before)
        self.assertEqual(source_path.read_text(), "caller uncommitted source\n")
        self.assertEqual((first_out / "candidate.lean").read_bytes(), self.candidate_source)
        self.assertIn("Synthetic local qualification candidate", (first_out / "candidate-commit.txt").read_text())
        self.assertIn(Q.CANDIDATE_CONDITION, (first_out / "candidate.patch").read_text())

    def test_wrong_original_pin_cannot_create_an_admitted_candidate(self):
        out = self.root / "wrong"
        out.mkdir()
        with mock.patch.object(Q, "ORIGINAL_SOURCE_SHA", "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "ORIGINAL_SOURCE_MISMATCH"):
                Q.prepare_candidate(self.repo, out)
        self.assertFalse((out / "candidate.json").exists())


class VerifierQualificationTests(unittest.TestCase):
    def test_new_status_inputs_must_be_committed_and_clean(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
            git("init", "-q")
            for name in Q.REQUIRED_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("committed qualification input\n")
            git("add", ".")
            git("-c", "user.name=Qualification Test", "-c",
                "user.email=qualification@example.invalid", "commit", "-qm", "verifier")
            identity = Q.verifier_identity(root)
            self.assertEqual(identity["commit"], git("rev-parse", "HEAD"))
            self.assertEqual(identity["qualifier_sha256"], hashlib.sha256(
                (root / Q.QUALIFIER_PATH).read_bytes()).hexdigest())
            new_dependency = root / "experiments/check-report-status-v1/untracked-helper.py"
            new_dependency.write_text("uncommitted dependency\n")
            with self.assertRaisesRegex(RuntimeError, "NOT_COMMITTED_AND_CLEAN"):
                Q.verifier_identity(root)
            new_dependency.unlink()
            (root / Q.STATUS_REFERENCE_PATH).write_text("changed status oracle\n")
            with self.assertRaisesRegex(RuntimeError, "NOT_COMMITTED_AND_CLEAN"):
                Q.verifier_identity(root)

    def test_equal_corpus_does_not_hide_changed_status_method(self):
        original = {"method": {"id": Q.STATUS_PROFILE, "corpus_sha256": "fixed",
                               "files": {"local-report-native.py": "one"}}}
        changed = copy.deepcopy(original)
        changed["method"]["files"]["local-report-native.py"] = "two"
        Q.require_same_method([original, copy.deepcopy(original)])
        with self.assertRaisesRegex(RuntimeError, "METHOD_CHANGED_BETWEEN_RUNS"):
            Q.require_same_method([original, changed])

    def test_failure_before_native_execution_still_retains_progress_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "result"
            with mock.patch.object(Q, "verifier_identity", side_effect=RuntimeError("UNCOMMITTED_TEST_INPUT")):
                code = Q.main(["--repo", temp, "--out", str(out), "--lean", "/unused/lean"])
            self.assertEqual(code, 2)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["engineering_qualification"], "FAILED")
            self.assertIn("UNCOMMITTED_TEST_INPUT", summary["failure"])
            self.assertEqual(summary["runs"], {})
            self.assertEqual(summary["protocol"]["human_trial"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
