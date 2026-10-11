"""Independent tests for the published Resolve bundle/policy transport contract."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUNDLE_PATH = ROOT / "conformance/resolve_v1/fixtures/bundle.json"
POLICY_PATH = ROOT / "conformance/resolve_v1/trust-policy.json"
BUNDLE_SHA256 = "957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62"
POLICY_SHA256 = "09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a"
MEMBER_SHA256 = {
    "history.md": "41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e",
    "jpl-record.json": "7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703",
    "record.json": "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87",
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ProtocolConsumerTests(unittest.TestCase):
    def load_consumer(self):
        path = HERE / "consumer.py"
        self.assertTrue(path.exists(), "independent protocol consumer is missing")
        spec = importlib.util.spec_from_file_location("resolve_protocol_v1_consumer", path)
        consumer = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = consumer
        spec.loader.exec_module(consumer)
        return consumer

    def inputs(self):
        return BUNDLE_PATH.read_bytes(), POLICY_PATH.read_bytes()

    def assert_reason(self, code, bundle, policy, policy_pin=None):
        consumer = self.load_consumer()
        if policy_pin is None:
            policy_pin = digest(policy)
        with self.assertRaises(consumer.ProtocolError) as caught:
            consumer.validate(bundle, policy, policy_pin)
        self.assertEqual(caught.exception.reason_code, code)

    def test_accepts_exact_immutable_bundle_and_policy_without_semantic_replay(self):
        consumer = self.load_consumer()
        bundle, policy = self.inputs()
        self.assertEqual(digest(bundle), BUNDLE_SHA256)
        self.assertEqual(digest(policy), POLICY_SHA256)
        report = consumer.validate(bundle, policy, POLICY_SHA256)
        self.assertEqual(
            report,
            {
                "accepted": True,
                "admission_ids": [
                    "mathgraph.l4yaml.48-case-qualification",
                    "openai.original_publication_receipt.1",
                    "openai.original_publication_receipt.2",
                    "openai.original_publication_receipt.3",
                ],
                "bundle_schema": "mathgraph.resolve-bundle.v1",
                "member_sha256": MEMBER_SHA256,
                "policy_schema": "mathgraph.resolve-trust-policy.v1",
                "schema": "mathgraph.resolve-protocol-validation-report.v1",
                "semantic_replay": "NOT_PERFORMED",
            },
        )

    def test_rejects_duplicate_keys_before_structural_validation(self):
        bundle, policy = self.inputs()
        self.assert_reason("DUPLICATE_JSON_KEY", b'{"schema":"mathgraph.resolve-bundle.v1","schema":"other"}', policy)
        self.assert_reason("DUPLICATE_JSON_KEY", bundle, b'{"schema":"x","schema":"y"}')

    def test_rejects_nonfinite_numbers_before_structural_validation(self):
        bundle, policy = self.inputs()
        for number in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            malformed = b'{"number":' + number + b"}"
            with self.subTest(number=number, input="bundle"):
                self.assert_reason("NONFINITE_JSON_NUMBER", malformed, policy)
            with self.subTest(number=number, input="policy"):
                self.assert_reason("NONFINITE_JSON_NUMBER", bundle, malformed)

    def test_normalizes_integer_conversion_limit_through_api(self):
        bundle, policy = self.inputs()
        original_limit = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(640)
            malformed = b'{"number":' + b"1" * 641 + b"}"
            self.assert_reason("INVALID_JSON", malformed, policy)
            self.assert_reason("INVALID_JSON", bundle, malformed)
        finally:
            sys.set_int_max_str_digits(original_limit)

    def test_normalizes_nesting_limit_through_api(self):
        bundle, policy = self.inputs()
        depth = sys.getrecursionlimit() + 100
        malformed = b'{"nested":' + b"[" * depth + b"0" + b"]" * depth + b"}"
        self.assert_reason("INVALID_JSON", malformed, policy)
        self.assert_reason("INVALID_JSON", bundle, malformed)

    def test_normalizes_parser_limits_through_cli(self):
        bundle, policy = self.inputs()
        malformed_inputs = {
            "integer": b'{"number":' + b"1" * 641 + b"}",
            "nesting": b'{"nested":' + b"[" * 10000 + b"0" + b"]" * 10000 + b"}",
        }
        for limit, malformed in malformed_inputs.items():
            for input_name in ("bundle", "policy"):
                with self.subTest(limit=limit, input=input_name), tempfile.TemporaryDirectory() as tmp:
                    directory = Path(tmp)
                    shutil.copyfile(HERE / "consumer.py", directory / "consumer.py")
                    (directory / "bundle.json").write_bytes(malformed if input_name == "bundle" else bundle)
                    policy_bytes = malformed if input_name == "policy" else policy
                    (directory / "policy.json").write_bytes(policy_bytes)
                    result = subprocess.run(
                        [sys.executable, "-I", "-S", "-X", "int_max_str_digits=640", "consumer.py",
                         "--bundle", "bundle.json", "--policy", "policy.json",
                         "--policy-sha256", digest(policy_bytes)],
                        cwd=directory,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, b"")
                    self.assertEqual(result.stderr, b'{"accepted":false,"reason_code":"INVALID_JSON"}\n')

    def test_rejects_extra_fields_and_missing_fields(self):
        bundle_raw, policy_raw = self.inputs()
        bundle = json.loads(bundle_raw)
        bundle["trust_policy_sha256"] = POLICY_SHA256
        self.assert_reason("UNEXPECTED_FIELD", canonical(bundle), policy_raw)
        policy = json.loads(policy_raw)
        policy["admissions"]["mathgraph.l4yaml.48-case-qualification"]["note"] = "not in v1"
        changed = canonical(policy)
        self.assert_reason("UNEXPECTED_FIELD", bundle_raw, changed)
        bundle = json.loads(bundle_raw)
        del bundle["members"]["history.md"]
        self.assert_reason("MISSING_MEMBER", canonical(bundle), policy_raw)
        policy = json.loads(policy_raw)
        del policy["provenance"]
        changed = canonical(policy)
        self.assert_reason("MISSING_FIELD", bundle_raw, changed)

    def test_rejects_bad_base64_and_independent_size_or_hash_substitution(self):
        bundle_raw, policy = self.inputs()
        bundle = json.loads(bundle_raw)
        bundle["members"]["history.md"]["data"] = "***="
        self.assert_reason("INVALID_BASE64", canonical(bundle), policy)
        bundle = json.loads(bundle_raw)
        bundle["members"]["history.md"]["size"] += 1
        self.assert_reason("MEMBER_SIZE_MISMATCH", canonical(bundle), policy)
        bundle = json.loads(bundle_raw)
        bundle["members"]["history.md"]["sha256"] = "0" * 64
        self.assert_reason("MEMBER_HASH_MISMATCH", canonical(bundle), policy)

    def test_rejects_unsupported_bundle_and_policy_versions(self):
        bundle_raw, policy_raw = self.inputs()
        bundle = json.loads(bundle_raw)
        bundle["schema"] = "mathgraph.resolve-bundle.v2"
        self.assert_reason("UNSUPPORTED_BUNDLE_VERSION", canonical(bundle), policy_raw)
        policy = json.loads(policy_raw)
        policy["schema"] = "mathgraph.resolve-trust-policy.v2"
        changed = canonical(policy)
        self.assert_reason("UNSUPPORTED_POLICY_VERSION", bundle_raw, changed)

    def test_rejects_unknown_semantic_kinds(self):
        bundle, policy_raw = self.inputs()
        policy = json.loads(policy_raw)
        policy["admissions"]["mathgraph.l4yaml.48-case-qualification"]["kind"] = "experimental"
        changed = canonical(policy)
        self.assert_reason("UNKNOWN_SEMANTIC_KIND", bundle, changed)

    def test_rejects_non_string_semantic_kinds_through_api_and_cli(self):
        bundle, policy_raw = self.inputs()
        for kind in ([], {}):
            policy = json.loads(policy_raw)
            policy["admissions"]["mathgraph.l4yaml.48-case-qualification"]["kind"] = kind
            changed = canonical(policy)
            with self.subTest(kind=kind, interface="api"):
                self.assert_reason("INVALID_FIELD_TYPE", bundle, changed)
            with self.subTest(kind=kind, interface="cli"), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                shutil.copyfile(HERE / "consumer.py", directory / "consumer.py")
                (directory / "bundle.json").write_bytes(bundle)
                (directory / "policy.json").write_bytes(changed)
                result = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "consumer.py",
                        "--bundle",
                        "bundle.json",
                        "--policy",
                        "policy.json",
                        "--policy-sha256",
                        digest(changed),
                    ],
                    cwd=directory,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(
                    json.loads(result.stderr),
                    {"accepted": False, "reason_code": "INVALID_FIELD_TYPE"},
                )
                self.assertNotIn(b"Traceback", result.stderr)

    def test_rejects_wrong_source_scope_verifier_and_assumptions(self):
        bundle, policy_raw = self.inputs()
        mutations = {
            "ADMISSION_SOURCE_MISMATCH": ("source", "history.md"),
            "ADMISSION_SCOPE_MISMATCH": ("scope", "all-yaml"),
            "ADMISSION_VERIFIER_MISMATCH": ("verifier", "self-reported-v1"),
            "ADMISSION_ASSUMPTIONS_MISMATCH": ("assumptions", ["network available"]),
        }
        for reason, (field, value) in mutations.items():
            policy = json.loads(policy_raw)
            policy["admissions"]["mathgraph.l4yaml.48-case-qualification"][field] = value
            changed = canonical(policy)
            with self.subTest(reason=reason):
                self.assert_reason(reason, bundle, changed)

    def test_rejects_rehashed_but_unauthorized_member_bytes(self):
        bundle_raw, policy_raw = self.inputs()
        bundle = json.loads(bundle_raw)
        policy = json.loads(policy_raw)
        member = bundle["members"]["record.json"]
        record = json.loads(base64.b64decode(member["data"]))
        record["interpretation"]["integrity_only"] = True
        replacement = canonical(record)
        member.update(data=base64.b64encode(replacement).decode(), size=len(replacement), sha256=digest(replacement))
        policy["members"]["record.json"].update(size=len(replacement), sha256=digest(replacement))
        changed_policy = canonical(policy)
        self.assert_reason("UNAUTHORIZED_MEMBER", canonical(bundle), changed_policy)

    def test_rejects_rewritten_provenance_even_when_bundle_and_policy_match(self):
        bundle_raw, policy_raw = self.inputs()
        bundle = json.loads(bundle_raw)
        policy = json.loads(policy_raw)
        for value in (bundle, policy):
            value["provenance"]["producer"]["commit"] = "0" * 40
        changed_policy = canonical(policy)
        self.assert_reason("UNAUTHORIZED_PROVENANCE", canonical(bundle), changed_policy)

    def test_root_schemas_are_authoritative_byte_identical_public_projections(self):
        for name in ["resolve-bundle-v1.schema.json", "resolve-trust-policy-v1.schema.json"]:
            root = ROOT / "protocol/schemas" / name
            public = ROOT / "website/public/schemas" / name
            self.assertTrue(root.exists(), root)
            self.assertEqual(root.read_bytes(), public.read_bytes())
            schema = json.loads(root.read_bytes())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["$id"], f"https://mathgraph.org/schemas/{name}")

    def test_consumer_runs_in_isolation_with_only_the_standard_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            shutil.copyfile(HERE / "consumer.py", directory / "consumer.py")
            shutil.copyfile(BUNDLE_PATH, directory / "bundle.json")
            shutil.copyfile(POLICY_PATH, directory / "policy.json")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "consumer.py",
                    "--bundle",
                    "bundle.json",
                    "--policy",
                    "policy.json",
                    "--policy-sha256",
                    POLICY_SHA256,
                ],
                cwd=directory,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(path.name for path in directory.iterdir()), ["bundle.json", "consumer.py", "policy.json"])
            self.assertEqual(json.loads(result.stdout), self.load_consumer().validate(*self.inputs(), POLICY_SHA256))


if __name__ == "__main__":
    unittest.main()
