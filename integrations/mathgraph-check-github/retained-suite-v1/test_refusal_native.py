"""Focused controls for raw process forwarding and invocation identity."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("refusal_native", HERE / "refusal-native.py")
NATIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NATIVE)


class ProcessEvidenceTests(unittest.TestCase):
    def run_fixture(self, case, missing=False, shorten_sleep=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "tmp").mkdir()
        argument = f"tmp/yaml_suite_test_{case['id']}_0.yaml"
        (root / argument).write_text("[\n")
        python = str(Path(sys.executable).resolve())
        if not missing:
            fixture = root / ".lake/build/bin/tryparse"
            fixture.parent.mkdir(parents=True)
            source = NATIVE.fixture_source(case, python)
            if shorten_sleep:
                self.assertEqual(source.count("time.sleep(3)"), 1)
                source = source.replace("time.sleep(3)", "time.sleep(0.01)")
            fixture.write_text(source)
            fixture.chmod(0o755)
        proxy = root / "proxy.py"
        proxy.write_text(NATIVE.TIMEOUT_PROXY)
        env = {**os.environ, "MATHGRAPH_EA03_TIMEOUT": str(Path(shutil.which("timeout")).resolve()),
               "L4YAML_SUITE_PROTOCOL": "1"}
        result = subprocess.run([python, str(proxy), "1", ".lake/build/bin/tryparse", argument],
                                cwd=root, env=env, capture_output=True, text=True, timeout=10)
        process = json.loads((root / "process.json").read_text())
        invocation_path = root / "backend.json"
        invocation = json.loads(invocation_path.read_text()) if invocation_path.exists() else None
        return root, result, process, invocation

    def test_real_nonzero_child_preserves_raw_bytes_and_invocation(self):
        case = {"id": "control", "expect_fail": True, "behavior": "exit", "exit_code": 2,
                "stdout": "exact output\n", "stderr": "exact error\n"}
        root, result, process, invocation = self.run_fixture(case)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (2, case["stdout"], case["stderr"]))
        self.assertEqual(process["raw_returncode"], 2)
        self.assertIsNone(NATIVE.validate_process(case, process, invocation, True, root))
        changed = {**invocation, "input": "different"}
        self.assertEqual(NATIVE.validate_process(case, process, changed, True, root),
                         "BACKEND_INPUT_OR_ENVIRONMENT_CHANGED")

    def test_actual_missing_executable_retains_127_without_claiming_backend_execution(self):
        case = {"id": "missing", "expect_fail": True, "behavior": "missing", "exit_code": 127,
                "stdout": "", "stderr": ""}
        root, result, process, invocation = self.run_fixture(case, missing=True)
        self.assertEqual(result.returncode, 127)
        self.assertIsNone(invocation)
        self.assertIsNone(NATIVE.validate_process(case, process, invocation, True, root))

    def test_claimed_actual_deadline_needs_elapsed_process_evidence(self):
        case = {"id": "deadline", "expect_fail": True, "behavior": "exit", "exit_code": 124,
                "stdout": "", "stderr": ""}
        root, _, process, invocation = self.run_fixture(case)
        self.assertIsNone(NATIVE.validate_process(case, process, invocation, True, root))
        self.assertEqual(NATIVE.validate_process({**case, "behavior": "sleep"},
                                                {**process, "wall_seconds": 0.01}, invocation, True, root),
                         "ACTUAL_DEADLINE_NOT_OBSERVED")

    def test_sleeping_child_allowed_to_finish_cannot_impersonate_a_deadline(self):
        case = {"id": "natural_completion", "expect_fail": True, "behavior": "sleep", "exit_code": 124,
                "stdout": "", "stderr": ""}
        root, result, process, invocation = self.run_fixture(case, shorten_sleep=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(process["raw_returncode"], 0)
        self.assertEqual(process["exit_code"], 0)
        self.assertEqual(NATIVE.validate_process(case, process, invocation, True, root),
                         "CONTROLLED_EXIT_NOT_OBSERVED")


if __name__ == "__main__":
    unittest.main()
