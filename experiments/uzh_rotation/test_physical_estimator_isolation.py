import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from physical_estimator_isolation import IsolationError, command, execute

class EstimatorIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = []
        for name in ("estimator.py", "camera.csv", "gyro.csv", "frozen_map.json"):
            f = self.root / name
            f.write_text("{}\n")
            self.inputs.append(f)
        self.encoder = self.root / "encoder.csv"
        self.encoder.write_text("GROUND TRUTH SHOULD NOT BE MOUNTED\n")

    def test_allowlist_excludes_encoder_and_workspace(self):
        args = command(*self.inputs)
        text = " ".join(args)
        for flag in ("--network none", "--read-only", "--cap-drop ALL",
                     "--security-opt no-new-privileges", "--user 65534:65534"):
            self.assertIn(flag, text)
        self.assertNotIn(str(self.encoder), text)
        self.assertNotIn(str(self.root) + ":/", text)
        self.assertEqual(text.count("type=bind,src="), 4)

    def test_successful_mocked_json_output(self):
        with patch("physical_estimator_isolation.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, '{"heading":0.1}', '')
            self.assertEqual(execute(*self.inputs), {"heading": 0.1})

    def test_failed_process_must_not_authorize(self):
        with patch("physical_estimator_isolation.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 1, "", "denied")
            with self.assertRaises(IsolationError):
                execute(*self.inputs)

    def test_non_json_must_not_authorize(self):
        with patch("physical_estimator_isolation.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "PASS", "")
            with self.assertRaises(IsolationError):
                execute(*self.inputs)

    def test_missing_input_refuses(self):
        self.inputs[1].unlink()
        with self.assertRaises(FileNotFoundError):
            command(*self.inputs)

    @unittest.skipUnless(os.environ.get("RUN_DOCKER_ISOLATION_TEST") == "1",
                         "real Docker isolation test runs in dedicated CI job")
    def test_real_container_allows_camera_gyro_map_but_denies_encoder(self):
        self.inputs[0].write_text(
            "import json,sys,os\n"
            "assert all(os.path.isfile(p) for p in sys.argv[1:])\n"
            "print(json.dumps({'has_encoder':os.path.exists('/encoder.csv'),"
            "'has_workspace':os.path.exists('/workspace')}))\n"
        )
        result = execute(*self.inputs, timeout=120)
        self.assertEqual(result, {"has_encoder": False, "has_workspace": False})
        self.inputs[0].write_text("open('/encoder.csv').read()\n")
        with self.assertRaises(IsolationError):
            execute(*self.inputs, timeout=120)

if __name__ == "__main__":
    unittest.main()
