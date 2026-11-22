import importlib.util
import subprocess
import json
import sys
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

    def test_exact_revision_and_clean_tree_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            repo = folder / "repo"
            repo.mkdir()
            def git(*args):
                p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                return p.stdout.strip()
            git("init", "-q")
            (repo / "marker.txt").write_text("unchanged")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-qm", "fixture")
            revision = git("rev-parse", "HEAD")
            spec_path = folder / "spec.json"
            spec_path.write_text(json.dumps({
                "schema": "mathgraph.prospective-probes.v0",
                "cases": [{"id": "known", "command": [sys.executable, "-c", "print('ok')"],
                           "expected": {"exit": 0}}]
            }))
            script = Path(__file__).with_name("probe.py")
            def invoke(rev, out):
                return subprocess.run([sys.executable, str(script), "--repo", str(repo),
                    "--revision", rev, "--spec", str(spec_path), "--out", str(out)],
                    capture_output=True, text=True)
            passed = invoke(revision, folder / "good")
            self.assertEqual(passed.returncode, 0, passed.stderr)
            receipt = json.loads((folder / "good" / "result.json").read_text())
            self.assertEqual(receipt["source_revision"], revision)
            self.assertTrue(receipt["source_stable"])
            self.assertEqual(receipt["status"], "BOUNDED_AGREEMENT")
            refused = invoke("0" * 40, folder / "wrong")
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse((folder / "wrong").exists())
            (repo / "untracked.txt").write_text("dirty")
            dirty = invoke(revision, folder / "dirty")
            self.assertNotEqual(dirty.returncode, 0)
            self.assertFalse((folder / "dirty").exists())

    def test_timeout_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            row = probe.execute(["python3", "-c", "import time; time.sleep(3)"], root, 1)
            self.assertEqual(row["kind"], "UNKNOWN")
            self.assertEqual(row["reason"], "TIMEOUT")

if __name__ == "__main__":
    unittest.main()
