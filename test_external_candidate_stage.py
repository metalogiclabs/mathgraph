import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from external_candidate_stage import stage_function_candidate


class CandidateStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        self.target = self.root / "module.py"
        self.original = ("class JSONField:\n"
                         "    def prepare_value(self, value):\n"
                         "        return str(value)\n\n"
                         "class Other:\n"
                         "    def prepare_value(self, value):\n"
                         "        return value\n")
        self.target.write_text(self.original)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "module.py"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                        "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                            cwd=self.root, text=True).strip()
        self.digest = hashlib.sha256(self.original.encode()).hexdigest()
        self.output = Path(self.temp.name) / "staged.py"
        self.proposal = "def prepare_value(self, value):\n    return str(value, encoding='utf8')\n"

    def stage(self, **overrides):
        args = dict(root=self.root, expected_head=self.head, source_file="module.py",
                    expected_sha256=self.digest, qualified_name="JSONField.prepare_value",
                    function_source=self.proposal, destination=self.output)
        args.update(overrides)
        return stage_function_candidate(**args)

    def test_stages_exact_method_without_mutating_source_or_sibling(self):
        receipt = self.stage()
        self.assertEqual(receipt["status"], "STAGED_UNTRUSTED_NOT_EXECUTED")
        self.assertEqual(self.target.read_text(), self.original)
        self.assertIn("return str(value, encoding='utf8')", self.output.read_text())
        self.assertIn("class Other:\n    def prepare_value(self, value):\n        return value", self.output.read_text())
        self.assertEqual(receipt["candidate_sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_fails_closed_on_wrong_source_digest(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_FILE_HASH_MISMATCH"):
            self.stage(expected_sha256="0" * 64)
        self.assertFalse(self.output.exists())

    def test_fails_closed_on_wrong_head(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_HEAD_MISMATCH"):
            self.stage(expected_head="0" * 40)
        self.assertFalse(self.output.exists())

    def test_rejects_ambiguous_or_nonfunction_payloads(self):
        for source in ["def prepare_value(self, value):\n    pass\n\nprint('side effect')\n",
                       "def different(self, value):\n    pass\n",
                       "def prepare_value(self, value):\n    return (\n",
                       "@staticmethod\ndef prepare_value(self, value):\n    pass\n"]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    self.stage(function_source=source)
                self.assertFalse(self.output.exists())

    def test_rejects_ambiguous_target_or_path_escape(self):
        with self.assertRaisesRegex(ValueError, "TARGET_FUNCTION_NOT_UNIQUE"):
            self.stage(qualified_name="prepare_value")
        with self.assertRaisesRegex(ValueError, "SOURCE_PATH_ESCAPE"):
            self.stage(source_file="../outside.py")

    def test_rejects_output_inside_source_checkout(self):
        with self.assertRaisesRegex(ValueError, "STAGING_MUST_BE_OUTSIDE_SOURCE"):
            self.stage(destination=self.root / "candidate.py")
        self.assertFalse((self.root / "candidate.py").exists())


if __name__ == "__main__":
    unittest.main()
