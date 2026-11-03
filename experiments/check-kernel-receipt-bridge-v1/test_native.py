"""Native Flash harness checks: pins, environment, and tampered export."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native


ROOT = Path(__file__).parent
POLICY = json.loads((ROOT / "policy.json").read_text())


def synthetic_export():
    lines = [
        {"meta": {"exporter": {"name": "lean4export", "version": "3.1.0"},
                  "format": {"version": "3.1.0"},
                  "lean": {"githash": POLICY["source"]["exporter"]["lean_githash"],
                           "version": "4.29.1"}}},
        {"in": 12, "str": {"pre": 0, "str": "bar"}},
        {"thm": {"all": [12], "levelParams": [], "name": 12,
                 "type": 15, "value": 16}},
    ]
    return ("\n".join(json.dumps(line) for line in lines) + "\n").encode()


def create_fixture(tmp):
    flash = Path(tmp)
    source = copy.deepcopy(POLICY)
    export = flash / "test_resources/ProofIrrelUnderBVar/export"
    export.parent.mkdir(parents=True)
    export.write_bytes(synthetic_export())
    config = flash / "test_resources/ProofIrrelUnderBVar/config.json"
    config.write_text(json.dumps({
        "export_file_path": "test_resources/ProofIrrelUnderBVar/export",
        "permitted_axioms": source["source"]["permitted_axioms"],
        "unpermitted_axiom_hard_error": True,
    }))
    source["source"]["export_sha256"] = hashlib.sha256(export.read_bytes()).hexdigest()
    source["source"]["config_sha256"] = hashlib.sha256(config.read_bytes()).hexdigest()
    return flash, source


class NativeHarnessTests(unittest.TestCase):
    def test_exact_checkout_requires_pinned_git_revision_and_verified_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            flash, policy = create_fixture(tmp)
            with patch("native.git_head", return_value=policy["checker"]["commit"]):
                verified = native.validate_checkout(flash, policy)
                self.assertEqual(verified["export_sha256"], policy["source"]["export_sha256"])
                self.assertEqual(verified["theorem"], "bar")
            with patch("native.git_head", return_value="0" * 40):
                with self.assertRaisesRegex(ValueError, "CHECKER_REVISION_MISMATCH"):
                    native.validate_checkout(flash, policy)
            (flash / policy["source"]["export_path"]).write_bytes(b"{}\n")
            with patch("native.git_head", return_value=policy["checker"]["commit"]):
                with self.assertRaisesRegex(ValueError, "EXPORT_SHA256_MISMATCH"):
                    native.validate_checkout(flash, policy)

    def test_export_metadata_axioms_and_theorem_target_are_checked(self):
        for variant in ("axioms", "target", "exporter"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                flash, policy = create_fixture(tmp)
                if variant == "axioms":
                    config = flash / policy["source"]["config_path"]
                    body = json.loads(config.read_text())
                    body["permitted_axioms"] = ["A"]
                    config.write_text(json.dumps(body))
                    policy["source"]["config_sha256"] = hashlib.sha256(config.read_bytes()).hexdigest()
                else:
                    export = flash / policy["source"]["export_path"]
                    body = export.read_bytes()
                    body = body.replace(b'"type": 15', b'"type": 1') if variant == "target" else body.replace(b'"version": "3.1.0"', b'"version": "9.9.9"', 1)
                    export.write_bytes(body)
                    policy["source"]["export_sha256"] = hashlib.sha256(body).hexdigest()
                with patch("native.git_head", return_value=policy["checker"]["commit"]):
                    code = {"axioms": "AXIOM_POLICY_MISMATCH",
                            "target": "THEOREM_IDENTITY_MISMATCH",
                            "exporter": "EXPORTER_METADATA_MISMATCH"}[variant]
                    with self.assertRaisesRegex(ValueError, code):
                        native.validate_checkout(flash, policy)

    def test_tampered_value_changes_export_and_keeps_original_unmodified(self):
        original = synthetic_export()
        mutated = native.mutated_export(original, POLICY["theorem"])
        self.assertNotEqual(original, mutated)
        self.assertEqual(json.loads(original.splitlines()[-1])["thm"]["value"], 16)
        self.assertEqual(json.loads(mutated.splitlines()[-1])["thm"]["value"], 0)
        self.assertEqual(json.loads(mutated.splitlines()[-1])["thm"]["type"], 15)

    def test_native_process_is_executed_without_shell_and_exit_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "checker"
            binary.write_bytes(b"fixed-binary-bytes")
            config = Path(tmp) / "config.json"
            config.write_text("{}")
            with patch("native.subprocess.run") as proc:
                proc.return_value.returncode = 1
                proc.return_value.stdout = b""
                proc.return_value.stderr = b"rejected"
                result = native.run_binary(binary, config, Path(tmp))
                proc.assert_called_once()
                self.assertEqual(proc.call_args.args[0], [str(binary), str(config)])
                self.assertEqual(proc.call_args.kwargs["cwd"], Path(tmp))
                self.assertNotIn("shell", proc.call_args.kwargs)
                self.assertEqual(result["exit_code"], 1)
                self.assertRegex(result["binary_sha256"], r"^[0-9a-f]{64}$")

    def test_current_candidate_reads_actual_binary_not_previous_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "sokonanoda"
            binary.write_bytes(b"current checker executable")
            current = native.measured_candidate_identity(binary, POLICY["consumer"], POLICY)
            self.assertEqual(current["binary_sha256"], hashlib.sha256(binary.read_bytes()).hexdigest())
            binary.write_bytes(b"changed binary")
            changed = native.measured_candidate_identity(binary, POLICY["consumer"], POLICY)
            self.assertNotEqual(current["binary_sha256"], changed["binary_sha256"])

    def test_saved_observation_cannot_supply_github_runner_context(self):
        valid = {
            "GITHUB_REPOSITORY": "metalogiclabs/mathgraph",
            "GITHUB_WORKFLOW_REF": "metalogiclabs/mathgraph/.github/workflows/check-kernel-receipt-bridge-v1.yml@refs/heads/research/check-kernel-warrant-bridge-20261104",
            "GITHUB_REF": "refs/heads/research/check-kernel-warrant-bridge-20261104",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_RUN_ID": "123456",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        self.assertEqual(native.ci_context(valid, POLICY)["run_id"], 123456)
        for key, value in (("GITHUB_WORKFLOW_REF", "attacker.yml"),
                           ("GITHUB_REF", "refs/heads/main"),
                           ("GITHUB_REPOSITORY", "other/repo"),
                           ("GITHUB_RUN_ID", "not-a-number")):
            with self.subTest(key=key):
                changed = {**valid, key: value}
                with self.assertRaisesRegex(ValueError, "UNTRUSTED_CI_CONTEXT"):
                    native.ci_context(changed, POLICY)
        with self.assertRaisesRegex(ValueError, "UNTRUSTED_CI_CONTEXT"):
            native.ci_context({}, POLICY)


if __name__ == "__main__":
    unittest.main()
