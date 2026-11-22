import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("probe", Path(__file__).with_name("probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class ProspectiveProbeTests(unittest.TestCase):
    def test_discrepancy_and_agreement(self):
        with tempfile.TemporaryDirectory() as root:
            cases = {"cases": [
                {"id": "agree", "command": ["python3", "-c", "print('yes')"], "expected": {"exit": 0}},
                {"id": "mismatch", "command": ["python3", "-c", "print('yes')"], "expected": {"exit": 1}},
            ]}
            rows = probe.evaluate(cases, root, 10)
            self.assertEqual([r["status"] for r in rows], ["AGREEMENT", "DISCREPANCY"])

    def test_missing_tool_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            cases = {"cases": [{"id": "missing", "command": ["missing-tool-mathgraph-2026"],
                                 "expected": {"exit": 0}}]}
            self.assertEqual(probe.evaluate(cases, root, 10)[0]["status"], "UNKNOWN")

    def test_output_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            cases = {"cases": [{"id": "output", "command": ["python3", "-c", "print('actual')"],
                                 "expected": {"exit": 0, "stdout_sha256": probe.sha(b"expected\\n")}}]}
            self.assertEqual(probe.evaluate(cases, root, 10)[0]["status"], "DISCREPANCY")

    def test_timeout_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            row = probe.execute(["python3", "-c", "import time; time.sleep(3)"], root, 1)
            self.assertEqual(row["kind"], "UNKNOWN")
            self.assertEqual(row["reason"], "TIMEOUT")

if __name__ == "__main__":
    unittest.main()
