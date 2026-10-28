import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from public_external_pilot import evaluate_candidate, source_task


class PublicPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        (self.root / "django/forms").mkdir(parents=True)
        (self.root / "django/__init__.py").write_text("")
        (self.root / "django/forms/__init__.py").write_text("")
        self.original = ("import json\nclass JSONField:\n"
                         "    def prepare_value(self, value):\n"
                         "        return json.dumps(value)\n")
        self.target = self.root / "django/forms/fields.py"
        self.target.write_text(self.original)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "django/forms/fields.py"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                        "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root,
                                            text=True).strip()
        self.path = Path(self.temp.name) / "proposal.json"
        self.output = Path(self.temp.name) / "receipt.json"

    def proposal(self, code):
        self.path.write_text(json.dumps({"task_id": "django__django-13512",
                                         "source_commit": self.head,
                                         "function_source": code,
                                         "status": "UNVERIFIED_PROPOSAL"}))

    def test_task_extracts_source_method_not_neighbour(self):
        task = source_task(self.root, self.head)
        self.assertIn("def prepare_value", task.function_excerpt)
        self.assertIn("json.dumps(value)", task.function_excerpt)
        self.assertEqual(task.source_file_sha256, hashlib.sha256(self.original.encode()).hexdigest())

    def test_correct_candidate_passes_requirement_and_restores_original(self):
        self.proposal("def prepare_value(self, value):\n    return json.dumps(value, ensure_ascii=False)\n")
        with patch("public_external_pilot.EXPECTED_HEAD", self.head), patch(
                "public_external_pilot.EXPECTED_SHA256", hashlib.sha256(self.original.encode()).hexdigest()):
            result = evaluate_candidate(self.root, self.path, self.output)
        self.assertEqual(result["requirement_verdict"], "WARRANTED_LOCAL_BOUNDED")
        self.assertEqual(self.target.read_text(), self.original)

    def test_wrong_candidate_rejected_even_with_zero_exit(self):
        self.proposal("def prepare_value(self, value):\n    return json.dumps(value)\n")
        with patch("public_external_pilot.EXPECTED_HEAD", self.head), patch(
                "public_external_pilot.EXPECTED_SHA256", hashlib.sha256(self.original.encode()).hexdigest()):
            result = evaluate_candidate(self.root, self.path, self.output)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["requirement_verdict"], "REJECTED")

    def test_mismatched_proposal_cannot_modify_checkout(self):
        self.proposal("def prepare_value(self, value):\n    return 'x'\n")
        data = json.loads(self.path.read_text())
        data["source_commit"] = "0" * 40
        self.path.write_text(json.dumps(data))
        with patch("public_external_pilot.EXPECTED_HEAD", self.head), patch(
                "public_external_pilot.EXPECTED_SHA256", hashlib.sha256(self.original.encode()).hexdigest()):
            with self.assertRaisesRegex(ValueError, "PROPOSAL_IDENTITY_MISMATCH"):
                evaluate_candidate(self.root, self.path, self.output)
        self.assertEqual(self.target.read_text(), self.original)


if __name__ == "__main__":
    unittest.main()
