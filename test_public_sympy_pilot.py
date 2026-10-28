import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from public_sympy_pilot import evaluate_candidate, source_task


class SympyPilotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "source"
        folder = self.root / "sympy/functions/elementary"
        folder.mkdir(parents=True)
        for dirname in ["sympy", "sympy/functions", "sympy/functions/elementary"]:
            (self.root / dirname / "__init__.py").write_text("")
        self.original = "class coth:\n    @classmethod\n    def eval(cls, arg):\n        return arg\n"
        self.target = folder / "hyperbolic.py"
        self.target.write_text(self.original)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "sympy/functions/elementary/hyperbolic.py"],
                       cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                        "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root,
                                            text=True).strip()
        self.output = Path(temp.name) / "result.json"
        self.proposal = Path(temp.name) / "proposal.json"

    def patched(self):
        return (patch("public_sympy_pilot.EXPECTED_HEAD", self.head),
                patch("public_sympy_pilot.EXPECTED_SHA256", hashlib.sha256(self.original.encode()).hexdigest()),
                patch("public_sympy_pilot.PROBE_CODE", "from sympy.functions.elementary.hyperbolic import coth\nassert coth.eval(2) == 3\nprint('SYMPY_NATIVE_ACCEPTANCE_PASSED')\n"))

    def candidate(self, code):
        self.proposal.write_text(json.dumps({"task_id": "sympy__sympy-13480",
                                              "source_commit": self.head,
                                              "status": "UNVERIFIED_PROPOSAL",
                                              "function_source": code}))

    def test_task_pins_decorated_method(self):
        task = source_task(self.root, self.head)
        self.assertIn("def eval", task.function_excerpt)
        self.assertEqual(task.source_file_sha256, hashlib.sha256(self.original.encode()).hexdigest())

    def test_proposed_classmethod_repair_qualifies_only_local_probe(self):
        self.candidate("def eval(cls, arg):\n    return arg + 1\n")
        head, digest, probe = self.patched()
        with head, digest, probe:
            result = evaluate_candidate(self.root, self.proposal, self.output, runtime_python=sys.executable)
        self.assertEqual(result["requirement_verdict"], "WARRANTED_LOCAL_BOUNDED")
        self.assertEqual(self.target.read_text(), self.original)

    def test_wrong_classmethod_repair_is_rejected(self):
        self.candidate("def eval(cls, arg):\n    return arg\n")
        head, digest, probe = self.patched()
        with head, digest, probe:
            result = evaluate_candidate(self.root, self.proposal, self.output, runtime_python=sys.executable)
        self.assertEqual(result["requirement_verdict"], "REJECTED")

    @unittest.skipUnless(os.environ.get("SYMPY_PINNED_UPSTREAM"),
                         "set SYMPY_PINNED_UPSTREAM for exact historical-source integration")
    def test_real_sympy_known_local_repair_against_numeric_oracle(self):
        pinned = Path(os.environ["SYMPY_PINNED_UPSTREAM"])
        task = source_task(pinned)
        self.assertIn("if cotm is S.ComplexInfinity:", task.function_excerpt)
        repaired = task.function_excerpt.replace("if cotm is S.ComplexInfinity:",
                                                 "if cothm is S.ComplexInfinity:")
        self.candidate(repaired)
        data = json.loads(self.proposal.read_text())
        data["source_commit"] = task.source_commit
        self.proposal.write_text(json.dumps(data))
        result = evaluate_candidate(pinned, self.proposal, self.output,
                                    runtime_python=os.environ.get("SYMPY_RUNTIME_PYTHON", "python3.9"))
        self.assertEqual(result["requirement_verdict"], "WARRANTED_LOCAL_BOUNDED")


if __name__ == "__main__":
    unittest.main()
