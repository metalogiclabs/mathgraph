import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("metamorphic", Path(__file__).with_name("metamorphic.py"))
import sys
sys.path.insert(0, str(Path(__file__).parent))
metamorphic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metamorphic)

class MetamorphicTests(unittest.TestCase):
    def test_same_stdout_violation_with_equal_exit(self):
        with tempfile.TemporaryDirectory() as root:
            rows = metamorphic.run({"pairs": [{
                "id": "different-outputs", "relation": "same_stdout",
                "requirement": "controlled test only",
                "left": [sys.executable, "-c", "print('a')"],
                "right": [sys.executable, "-c", "print('b')"]
            }]}, root, 10)
            self.assertEqual(rows[0]["status"], "RELATION_VIOLATED")
            self.assertEqual(rows[0]["left"]["exit"], rows[0]["right"]["exit"])

    def test_equal_outputs_satisfy_relation(self):
        with tempfile.TemporaryDirectory() as root:
            rows = metamorphic.run({"pairs": [{
                "id": "same", "relation": "same_stdout",
                "requirement": "controlled test only",
                "left": [sys.executable, "-c", "print('a')"],
                "right": [sys.executable, "-c", "print('a')"]
            }]}, root, 10)
            self.assertEqual(rows[0]["status"], "RELATION_SATISFIED")

    def test_both_accept_rejects_equal_failures(self):
        with tempfile.TemporaryDirectory() as root:
            rows = metamorphic.run({"pairs": [{
                "id": "both-refuse", "relation": "both_accept",
                "requirement": "controlled acceptance relation",
                "left": [sys.executable, "-c", "raise SystemExit(1)"],
                "right": [sys.executable, "-c", "raise SystemExit(1)"]
            }]}, root, 10)
            self.assertEqual(rows[0]["status"], "RELATION_VIOLATED")
            self.assertEqual(rows[0]["left"]["exit"], 1)
            self.assertEqual(rows[0]["right"]["exit"], 1)

    def test_missing_executable_is_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            rows = metamorphic.run({"pairs": [{
                "id": "missing", "relation": "same_exit",
                "requirement": "controlled test only",
                "left": ["missing-mathgraph-command-2026"],
                "right": [sys.executable, "-c", "pass"]
            }]}, root, 10)
            self.assertEqual(rows[0]["status"], "UNKNOWN")

if __name__ == "__main__":
    unittest.main()
