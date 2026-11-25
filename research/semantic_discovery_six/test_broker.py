"""Standard-library tests for the arm-neutral access broker; no trial data."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("trial_access_broker", Path(__file__).with_name("broker.py"))
broker_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(broker_module)
Broker = broker_module.Broker


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = self.parent / "arm"
        self.root.mkdir()
        (self.root / "inputs").mkdir()
        for case in ("case-1", "case-2"):
            (self.root / "inputs" / f"{case}.json").write_text(json.dumps({"synthetic_case": case}))
        (self.root / "work").mkdir()
        (self.root / "results").mkdir()
        self.broker = Broker(self.root)

    def request(self, action, case="case-1", *, path=None, value=None, raw=None):
        payload = raw if raw is not None else (json.dumps(value).encode() if value is not None else b"")
        return self.broker.request(action, case, path=path, payload=payload)

    def events(self):
        return [json.loads(line) for line in (self.root / "journal.jsonl").read_text().splitlines()]

    def test_per_case_budget_and_failed_attempt_cost(self):
        missing, code = self.request("read", path="work/missing.json")
        self.assertEqual(code, 1)
        self.assertEqual(missing["credits"], 1)
        for _ in range(23):
            self.assertEqual(self.request("list")[1], 0)
        denied, code = self.request("write", value={"path": "work/denied", "content": "x"})
        self.assertEqual(code, 1)
        self.assertEqual(denied["error_code"], "budget_exceeded")
        self.assertEqual(denied["credits"], 0)
        self.assertFalse((self.root / "work/denied").exists())
        self.assertEqual(self.request("list", "case-2")[1], 0)
        self.assertEqual(sum(event["credits"] for event in self.events() if event["case"] == "case-1"), 24)
        self.assertEqual(len(self.events()), 52)

    def test_shared_budget_is_twelve_and_survives_new_broker(self):
        for _ in range(12):
            self.assertEqual(self.request("list", "shared")[1], 0)
        self.broker = Broker(self.root)
        response, code = self.request("finalize", "shared", raw=b"{}")
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "budget_exceeded")
        self.assertFalse((self.root / "results/final.json").exists())

    def test_missing_source_is_a_logged_failure(self):
        response, code = self.request("read", "not-present", path="inputs/not-present.json")
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "unassigned_case")
        start, end = self.events()
        self.assertEqual((start["phase"], end["phase"]), ("start", "end"))
        self.assertEqual(start["credits"], 0)
        self.assertEqual(end["output_bytes"], 0)
        self.assertFalse(end["ok"])
        self.assertEqual(end["exit"], 1)
        self.assertGreaterEqual(end["wall_end_ns"], end["wall_start_ns"])
        self.assertGreaterEqual(end["monotonic_end_ns"], end["monotonic_start_ns"])

    def test_traversal_symlinks_and_input_writes_fail_closed(self):
        private = self.parent / "private"
        private.mkdir()
        (private / "secret.txt").write_text("secret")
        (self.root / "work/link").symlink_to(private, target_is_directory=True)
        for path in ("../private/secret.txt", str(private / "secret.txt"), "work/link/secret.txt"):
            response, code = self.request("read", path=path)
            self.assertEqual(code, 1, path)
            self.assertNotIn("content", response)
        for path in ("work/../../private/changed", "work/link/changed", "inputs/case.json"):
            self.assertEqual(self.request("write", value={"path": path, "content": "bad"})[1], 1, path)
        self.assertFalse((private / "changed").exists())
        listing, code = self.request("list")
        self.assertEqual(code, 0)
        self.assertFalse(any("secret" in item["path"] or "link" in item["path"] for item in listing["files"]))

    def test_journal_open_failure_prevents_operation(self):
        (self.root / "journal.jsonl").mkdir()
        response, code = self.request("write", value={"path": "work/never", "content": "x"})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "journal_unavailable")
        self.assertFalse((self.root / "work/never").exists())

    def test_start_record_failure_prevents_operation(self):
        with mock.patch.object(self.broker, "_append_journal", side_effect=OSError("disk failure")):
            response, code = self.request("write", value={"path": "work/never", "content": "x"})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "journal_unavailable")
        self.assertFalse((self.root / "work/never").exists())

    def test_end_record_failure_preserves_durable_reservation(self):
        append = self.broker._append_journal

        def fail_end(journal, event):
            if event["phase"] == "end":
                raise OSError("disk failure")
            append(journal, event)

        with mock.patch.object(self.broker, "_append_journal", side_effect=fail_end):
            response, code = self.request("list")
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "journal_write_failed")
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.events()[0]["credits"], 1)
        self.assertEqual(self.request("list")[0]["used"], 2)

    def test_corrupt_journal_never_admits_actions(self):
        (self.root / "journal.jsonl").write_text("not JSON\n")
        response, code = self.request("write", value={"path": "work/never", "content": "x"})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "journal_corrupt")
        self.assertEqual(response["credits"], 0)
        self.assertFalse((self.root / "work/never").exists())

    def test_finalize_is_exclusive_and_hash_locked(self):
        response, code = self.request("finalize", raw=b'{"answer": "UNKNOWN"}')
        self.assertEqual(code, 0)
        final = self.root / "results/final.json"
        content = final.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        self.assertEqual(response["sha256"], digest)
        self.assertEqual((self.root / "results/.final.lock").read_text().strip(), digest)
        self.assertEqual((self.root / "results/final.sha256").read_text(), digest + "  final.json\n")
        second, code = self.request("finalize", raw=b'{"answer": "changed"}')
        self.assertEqual(code, 1)
        self.assertEqual(second["error_code"], "final_locked")
        for name in broker_module.FINAL_NAMES:
            self.assertEqual(self.request("write", value={"path": "results/" + name, "content": "bad"})[1], 1)
        self.assertEqual(final.read_bytes(), content)

    def test_run_saves_full_output_and_charges_all_bytes(self):
        argv = [sys.executable, "-c", "import sys; sys.stdout.write('x'*9000); sys.stderr.write('y'*500)"]
        raw = json.dumps({"argv": argv}).encode()
        response, code = self.request("run", raw=raw)
        self.assertEqual(code, 0)
        self.assertTrue(response["truncated"])
        self.assertLessEqual(len(response["stdout"]) + len(response["stderr"]), 8000)
        self.assertEqual((self.root / response["stdout_path"]).read_bytes(), b"x" * 9000)
        self.assertEqual((self.root / response["stderr_path"]).read_bytes(), b"y" * 500)
        start, end = self.events()
        self.assertEqual(start["credits"], 4)
        self.assertEqual(end["argv"], argv)
        self.assertEqual(end["input_bytes"], len(raw))
        self.assertEqual(end["output_bytes"], 9500)
        self.assertEqual(end["written_bytes"], 9500)
        self.assertEqual(end["response_bytes"], len(broker_module.json_bytes(response)))
        self.assertGreaterEqual(end["run_seconds"], 0)

    def test_run_timeout_and_nonzero_exit_are_logged(self):
        response, code = self.request("run", value={"argv": [sys.executable, "-c", "import time; time.sleep(2)"], "timeout": 0.02})
        self.assertEqual(code, 1)
        self.assertEqual(response["exit"], 124)
        self.assertEqual(response["error_code"], "timeout")
        self.assertTrue((self.root / response["stdout_path"]).exists())
        response, code = self.request("run", value={"argv": [sys.executable, "-c", "raise SystemExit(7)"]})
        self.assertEqual(code, 1)
        self.assertEqual(response["exit"], 7)
        self.assertEqual(self.events()[-1]["exit"], 7)
        self.assertEqual(self.events()[-1]["reserved_credits"], 4)

    def test_run_allows_work_script_and_rejects_outside_operands(self):
        (self.root / "work/probe.py").write_text("print('ok')\n")
        response, code = self.request("run", value={"argv": [sys.executable, "probe.py"]})
        self.assertEqual(code, 0)
        self.assertEqual(response["stdout"], "ok\n")
        outside = self.parent / "other.py"
        outside.write_text("raise RuntimeError('must not run')\n")
        for operand in (str(outside), "../../other.py"):
            response, code = self.request("run", value={"argv": [sys.executable, operand]})
            self.assertEqual(code, 1)
            self.assertEqual(response["error_code"], "path_escape")
        response, code = self.request("run", value={"argv": [sys.executable, "probe.py"], "timeout": 61})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "invalid_timeout")

    def test_read_binary_and_write_account_for_exact_bytes(self):
        content = "λ\n"
        raw = json.dumps({"path": "work/utf8.txt", "content": content}).encode()
        response, code = self.request("write", raw=raw)
        self.assertEqual(code, 0)
        self.assertEqual(self.events()[-1]["input_bytes"], len(raw))
        self.assertEqual(self.events()[-1]["written_bytes"], len(content.encode("utf-8")))
        response, code = self.request("read", path="work/utf8.txt")
        self.assertEqual(code, 0)
        self.assertEqual(response["content"], content)
        self.assertEqual(self.events()[-1]["output_bytes"], len(content.encode("utf-8")))
        (self.root / "work/raw").write_bytes(b"\xff")
        response, code = self.request("read", path="work/raw")
        self.assertEqual(code, 0)
        self.assertEqual(response["encoding"], "base64")
        self.assertEqual(response["content"], "/w==")

    def test_case_aliases_and_cross_case_source_access_are_rejected(self):
        for alias in ("new-budget", "case-1.json", "../case-1"):
            response, code = self.request("list", alias)
            self.assertEqual(code, 1)
            self.assertEqual(response["credits"], 0)
        for case, path in (("shared", "inputs/case-1.json"),
                           ("case-1", "inputs/case-2.json")):
            response, code = self.request("read", case, path=path)
            self.assertEqual(code, 1)
            self.assertEqual(response["error_code"], "case_input_denied")
        response, code = self.request("run", value={"argv": [sys.executable, "../inputs/case-2.json"]})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "case_input_denied")
        response, code = self.request("read", path="inputs/case-1.json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(response["content"])["synthetic_case"], "case-1")
        for case in ("shared", "case-1"):
            response, code = self.request("list", case)
            paths = {item["path"] for item in response["files"]}
            self.assertEqual(code, 0)
            self.assertNotIn("inputs/case-2.json", paths)
            if case == "shared":
                self.assertNotIn("inputs/case-1.json", paths)

    def test_every_request_payload_is_retained_with_hash(self):
        raw = b'{"path":"work/request.txt", "content":"v1"}'
        response, code = self.request("write", raw=raw)
        self.assertEqual(code, 0)
        self.request("read", path="work/no-source")
        for event in self.events():
            if event["phase"] != "end":
                continue
            descriptor_artifact = event["request_artifact"]
            descriptor_content = (self.root / descriptor_artifact["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(descriptor_content).hexdigest(), descriptor_artifact["sha256"])
            descriptor = json.loads(descriptor_content)
            retained_payload = (self.root / descriptor["payload"]["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(retained_payload).hexdigest(), descriptor["payload"]["sha256"])
            self.assertEqual(retained_payload, raw if event["action"] == "write" else b"")
            if event["action"] == "read":
                self.assertEqual(descriptor["path"], "work/no-source")

    def test_write_versions_retain_old_and_new_contents(self):
        target = self.root / "work/version.txt"
        target.write_text("v0")
        for new in ("v1", "v2"):
            self.assertEqual(self.request("write", value={"path": "work/version.txt", "content": new})[1], 0)
        for event, prior, new in ((self.events()[1], b"v0", b"v1"), (self.events()[3], b"v1", b"v2")):
            version = json.loads((self.root / event["write_version"]["path"]).read_bytes())
            self.assertEqual((self.root / version["prior"]["path"]).read_bytes(), prior)
            self.assertEqual((self.root / version["new"]["path"]).read_bytes(), new)
        self.assertEqual(target.read_bytes(), b"v2")
        denied, code = self.request("write", value={"path": "results/.broker-audit/alter", "content": "bad"})
        self.assertEqual(code, 1)
        self.assertEqual(denied["error_code"], "reserved_path")

    def test_run_snapshots_retain_code_input_and_result_mutations(self):
        code = ("from pathlib import Path\n"
                "Path('probe.py').write_text('changed code')\n"
                "Path('../results/prior.txt').write_text('changed result')\n"
                "Path('created.txt').write_text('created')\n")
        (self.root / "work/probe.py").write_text(code)
        (self.root / "results/prior.txt").write_text("prior result")
        response, exit_code = self.request("run", value={"argv": [sys.executable, "probe.py"]})
        self.assertEqual(exit_code, 0)
        event = self.events()[-1]
        before = json.loads((self.root / event["snapshots"]["before"]["path"]).read_bytes())
        after = json.loads((self.root / event["snapshots"]["after"]["path"]).read_bytes())
        for snapshot in (before, after):
            self.assertTrue(snapshot["complete"])
            self.assertIn("inputs/case-1.json", snapshot["entries"])
            self.assertNotIn("inputs/case-2.json", snapshot["entries"])
            self.assertFalse(any(path.startswith("results/.broker-audit") for path in snapshot["entries"]))
        for snapshot, path, expected in ((before, "work/probe.py", code.encode()),
                                          (after, "work/probe.py", b"changed code"),
                                          (before, "results/prior.txt", b"prior result"),
                                          (after, "results/prior.txt", b"changed result"),
                                          (after, "work/created.txt", b"created")):
            entry = snapshot["entries"][path]
            self.assertEqual((self.root / entry["path"]).read_bytes(), expected)
            self.assertEqual(entry["sha256"], hashlib.sha256(expected).hexdigest())

    def test_pre_run_snapshot_limit_prevents_execution(self):
        with mock.patch.object(broker_module, "SNAPSHOT_MAX_BYTES", 1):
            response, code = self.request("run", value={"argv": [sys.executable, "-c", "open('must-not-exist', 'w').close()"]})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "snapshot_limit")
        self.assertFalse((self.root / "work/must-not-exist").exists())
        artifact = self.events()[-1]["snapshots"]["before"]
        snapshot = json.loads((self.root / artifact["path"]).read_bytes())
        self.assertFalse(snapshot["complete"])

    def test_post_run_snapshot_limit_is_a_recorded_failure(self):
        with mock.patch.object(broker_module, "SNAPSHOT_MAX_BYTES", 70):
            response, code = self.request("run", value={"argv": [sys.executable, "-c", "open('large', 'wb').write(b'x'*100)"]})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "snapshot_limit")
        self.assertEqual(response["process_exit"], 0)
        artifact = self.events()[-1]["snapshots"]["after"]
        snapshot = json.loads((self.root / artifact["path"]).read_bytes())
        self.assertFalse(snapshot["complete"])

    def test_timeout_kills_descendant_group_before_snapshot(self):
        child = ("from pathlib import Path; import time; "
                 "Path('child-ready').write_text('ready'); time.sleep(0.15); "
                 "Path('escaped-mutation').write_text('bad')")
        parent = ("import subprocess, sys, time; "
                  f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
                  "time.sleep(0.2)")
        response, code = self.request("run", value={"argv": [sys.executable, "-c", parent], "timeout": 0.08})
        self.assertEqual(code, 1)
        self.assertEqual(response["error_code"], "timeout")
        self.assertTrue((self.root / "work/child-ready").exists())
        self.assertTrue(self.events()[-1]["group_kill_sent"])
        time.sleep(0.18)
        self.assertFalse((self.root / "work/escaped-mutation").exists())
        snapshot = json.loads((self.root / self.events()[-1]["snapshots"]["after"]["path"]).read_bytes())
        self.assertNotIn("work/escaped-mutation", snapshot["entries"])

    def test_cli_uses_json_stdin_and_emits_accounted_json(self):
        prefix = [sys.executable, str(Path(__file__).with_name("broker.py")),
                  "--arm-root", str(self.root), "--case", "case-1"]
        created = subprocess.run(prefix + ["write"], input=b'{"path":"work/cli.txt","content":"cli"}',
                                 capture_output=True, timeout=5, check=False)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertTrue(json.loads(created.stdout)["ok"])
        read = subprocess.run(prefix + ["read", "work/cli.txt"], capture_output=True,
                              timeout=5, check=False)
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(json.loads(read.stdout)["content"], "cli")
        self.assertEqual(self.events()[-1]["response_bytes"], len(read.stdout))


if __name__ == "__main__":
    unittest.main()
