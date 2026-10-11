"""Independent expectations for the exact historical import boundary."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
PUBLIC = ROOT / "website/public/evidence/mg-l4yaml-source-check-20261010/record.json"
TRANSPORT = "7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703"
CONTENT = "f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb"
RESULT = "55ff4aa97dcc33deb2d319d41e4d91783492e7eff5c3048697f6a310cbcdab8b"
SOURCE_COMMIT = "62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
SUITE_COMMIT = "da267a5c4782e7361e82889e76c0dc7df0e1e870"
SCOPE = f"nasa-jpl/L4YAML@{SOURCE_COMMIT}:yaml/yaml-test-suite@{SUITE_COMMIT}:48-cases"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@pytest.fixture
def consumer():
    path = HERE / "consumer.py"
    assert path.is_file(), "independent supported-import consumer is absent"
    spec = importlib.util.spec_from_file_location("independent_import", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def policy():
    return (HERE / "fixtures/trust-policy.json").read_bytes()


def run_import(consumer, policy, record=None, **kwargs):
    return consumer.import_record(
        PUBLIC.read_bytes() if record is None else record,
        policy,
        hashlib.sha256(policy).hexdigest(),
        **kwargs,
    )


def test_schema_exists_and_public_copy_is_byte_identical():
    path = ROOT / "protocol/schemas/import-result-v1.schema.json"
    assert path.is_file(), "supported-import result schema is absent"
    assert path.read_bytes() == (ROOT / "website/public/schemas" / path.name).read_bytes()
    Draft202012Validator.check_schema(json.loads(path.read_bytes()))


def test_exact_record_result_and_deterministic_fixture(consumer, policy):
    assert (HERE / "fixtures/record.json").read_bytes() == PUBLIC.read_bytes()
    assert hashlib.sha256(PUBLIC.read_bytes()).hexdigest() == TRANSPORT
    result = run_import(consumer, policy)
    assert result == run_import(consumer, policy)
    assert result["schema"] == "mathgraph.import-result.v1"
    assert result["result_kind"] == "READ_ONLY_IMPORT_RESULT"
    assert result["record_id"] == "mg-l4yaml-source-check-20261010"
    assert result["record_sha256"] == TRANSPORT
    assert result["content_sha256"] == CONTENT
    assert result["epistemic_status"] == "WARRANTED_BOUNDED"
    assert result["source"]["commit"] == SOURCE_COMMIT
    assert result["source"]["external_suite_commit"] == SUITE_COMMIT
    assert result["verifier"] == "pinned-jpl-qualified-receipt-v1"
    assert result["assumptions"] == []
    assert result["scope"] == {
        "identity": SCOPE,
        "case_scope": "Pinned YAML-suite examples after specified source decoding",
        "source_cases": 48,
        "expected_accept": 31,
        "expected_reject": 17,
        "extra_controls": 4,
        "matched_external_labels": 48,
        "total_lean_guards": 52,
        "normalization": "yaml-suite-visible-space-only-v1",
    }
    assert result["evidence"]["test_commit"] == "988afbf9a6ec69488b63af5c7ff986fde26d673c"
    assert result["evidence"]["lean_source_sha256"] == "a9a16f54c053e3c3c5a9f56486508a04ac84d9eb9e18106271daddac488d5b62"
    assert result["evidence"]["archive_sha256"] == "61fc93815e3329c0490324f52897a94d3417044a5cf16a8e1e0f0109aa0e515e"
    assert result["evidence"]["proof_replay"] == "NOT_PERFORMED"
    assert result["lifecycle"] == "UNKNOWN"
    assert result["freshness"] == "NOT_CHECKED"
    assert result["current_applicability"] == "UNKNOWN"
    assert result["authorization"] == "READ_ONLY_NO_AUTOMATIC_AUTHORIZATION"
    assert result["unknowns"] == {
        "generalization": "UNKNOWN", "human_digestion": "UNKNOWN",
        "statement_fidelity": "UNKNOWN", "universal_yaml_correctness": "UNKNOWN",
        "whole_input_extraction_theorem": "UNKNOWN",
    }
    assert (HERE / "fixtures/result.json").read_bytes() == encoded(result) + b"\n"
    assert hashlib.sha256((HERE / "fixtures/result.json").read_bytes()).hexdigest() == RESULT
    validator = Draft202012Validator(json.loads((ROOT / "protocol/schemas/import-result-v1.schema.json").read_bytes()))
    validator.validate(result)
    for key, value in [("epistemic_status", "VERIFIED_PROOF"), ("authorization", "EXECUTE"), ("lifecycle", "CURRENT"), ("freshness", "CHECKED"), ("current_applicability", "APPLICABLE"), ("producer_verdict", "VERIFIED_PROOF")]:
        changed = {**result, key: value}
        assert not validator.is_valid(changed), key


def test_result_distinguishes_processing_authority_from_historical_evidence(consumer, policy):
    result = run_import(consumer, policy)
    assert result["processing_mode"] == "INDEPENDENT_OFFLINE_HISTORICAL_RECORD_POLICY_VALIDATION"
    assert result["consumer_authority"] == {
        "boundary": "EXACT_HISTORICAL_RECEIPT_AND_LOCAL_POLICY_ONLY",
        "kernel_replay": "NOT_PERFORMED",
        "kernel_admission": "NOT_PERFORMED",
        "current_truth": "NOT_ESTABLISHED",
    }
    assert result["source_suite_replay"] == "NOT_PERFORMED"
    assert result["evidence"]["authority"] == "LEAN_GUARDS_AND_COMPILED_TRYPARSE"
    assert result["evidence"]["proof_replay"] == "NOT_PERFORMED"


@pytest.mark.parametrize(("key", "promoted"), [
    ("processing_mode", "KERNEL_VERIFICATION"),
    ("consumer_authority", {
        "boundary": "EXACT_HISTORICAL_RECEIPT_AND_LOCAL_POLICY_ONLY",
        "kernel_replay": "PERFORMED", "kernel_admission": "NOT_PERFORMED",
        "current_truth": "NOT_ESTABLISHED",
    }),
    ("consumer_authority", {
        "boundary": "EXACT_HISTORICAL_RECEIPT_AND_LOCAL_POLICY_ONLY",
        "kernel_replay": "NOT_PERFORMED", "kernel_admission": "PERFORMED",
        "current_truth": "NOT_ESTABLISHED",
    }),
    ("consumer_authority", {
        "boundary": "EXACT_HISTORICAL_RECEIPT_AND_LOCAL_POLICY_ONLY",
        "kernel_replay": "NOT_PERFORMED", "kernel_admission": "NOT_PERFORMED",
        "current_truth": "ESTABLISHED",
    }),
    ("consumer_authority", {
        "boundary": "SOURCE_SUITE_EXECUTION", "kernel_replay": "NOT_PERFORMED",
        "kernel_admission": "NOT_PERFORMED", "current_truth": "NOT_ESTABLISHED",
    }),
    ("source_suite_replay", "PERFORMED"),
])
def test_schema_requires_processing_boundary_and_rejects_promotion(consumer, policy, key, promoted):
    result = run_import(consumer, policy)
    validator = Draft202012Validator(json.loads((ROOT / "protocol/schemas/import-result-v1.schema.json").read_bytes()))
    assert validator.is_valid(result)
    missing = {name: value for name, value in result.items() if name != key}
    assert not validator.is_valid(missing), f"missing {key} must be rejected"
    assert not validator.is_valid({**result, key: promoted})


@pytest.mark.parametrize("projection_schema", ["mathgraph.presentation-export.v1", "mathgraph.browser-result.v1"])
def test_presentation_and_browser_outputs_cannot_borrow_record_authority(consumer, policy, projection_schema):
    # These are explicitly synthetic presentation outputs, not evidence fixtures.
    original = json.loads(PUBLIC.read_bytes())
    presentation = {
        "schema": projection_schema, "id": original["id"],
        "record_id": original["id"], "record_schema": original["schema"],
        "record_sha256": TRANSPORT, "content_sha256": CONTENT,
        "source": original["source"], "evidence": original["evidence"],
        "epistemic_status": "WARRANTED_BOUNDED",
        "authorization": "READ_ONLY_NO_AUTOMATIC_AUTHORIZATION",
    }
    with pytest.raises(consumer.ImportError, match="UNEXPECTED_FIELD"):
        run_import(consumer, policy, encoded(presentation))
    # Copying the complete original fields and digests still cannot admit a
    # presentation schema or a browser projection disguised as the record schema.
    presentation = {**original, "schema": projection_schema}
    with pytest.raises(consumer.ImportError, match="UNSUPPORTED_RECORD_SCHEMA"):
        run_import(consumer, policy, encoded(presentation))
    presentation = {**original, "record_kind": "PRESENTATION_ONLY"}
    with pytest.raises(consumer.ImportError, match="UNSUPPORTED_RECORD_KIND"):
        run_import(consumer, policy, encoded(presentation))


def test_import_result_is_not_reimportable_evidence(consumer, policy):
    result = run_import(consumer, policy)
    assert result["record_sha256"] == TRANSPORT
    assert result["content_sha256"] == CONTENT
    with pytest.raises(consumer.ImportError, match="UNEXPECTED_FIELD"):
        run_import(consumer, policy, encoded(result))


@pytest.mark.parametrize("goal", ["universal_yaml_correctness", "current_applicability", "current_lifecycle", "execute"])
def test_unsupported_and_current_goals_are_typed_errors(consumer, policy, goal):
    with pytest.raises(consumer.ImportError, match="UNSUPPORTED_GOAL"):
        run_import(consumer, policy, goal=goal)


@pytest.mark.parametrize(("path", "value", "reason"), [
    (("schema",), "mathgraph.public-consequence-record.v2", "UNSUPPORTED_RECORD_SCHEMA"),
    (("record_kind",), "VERIFIED_PROOF", "UNSUPPORTED_RECORD_KIND"),
    (("id",), "other", "RECORD_ID_MISMATCH"),
    (("source", "commit"), "0" * 40, "SOURCE_PIN_MISMATCH"),
    (("source", "external_suite_commit"), "0" * 40, "SOURCE_PIN_MISMATCH"),
    (("evidence", "v2_normalized_native_parser", "source_commit"), "0" * 40, "EVIDENCE_MISMATCH"),
    (("evidence", "v2_normalized_native_parser", "lean_source_sha256"), "0" * 64, "EVIDENCE_MISMATCH"),
    (("content_sha256",), "0" * 64, "CONTENT_HASH_MISMATCH"),
    (("axes", "finite_executable", "source_cases"), 49, "FINITE_SCOPE_MISMATCH"),
    (("axes", "finite_executable", "source_cases"), True, "FINITE_SCOPE_MISMATCH"),
    (("axes", "finite_executable", "case_scope"), "All YAML", "FINITE_SCOPE_MISMATCH"),
    (("axes", "finite_executable", "authority"), "untrusted", "FINITE_SCOPE_MISMATCH"),
    (("axes", "finite_executable", "status"), "VERIFIED_PROOF", "FINITE_SCOPE_MISMATCH"),
    (("axes", "generalization", "status"), "VERIFIED_PROOF", "AXIS_MISMATCH"),
    (("axes", "global_truth_promotion"), True, "AXIS_MISMATCH"),
    (("admission", "status"), "VERIFIED_PROOF", "ADMISSION_MISMATCH"),
    (("admission", "automatic_api_warrant_promotion"), True, "ADMISSION_MISMATCH"),
    (("test_input_normalization", "decoder"), "arbitrary", "ASSUMPTION_CONTEXT_MISMATCH"),
    (("assumptions",), ["anything"], "UNEXPECTED_FIELD"),
    (("authorization",), "EXECUTE", "UNEXPECTED_FIELD"),
    (("epistemic_status",), "VERIFIED_PROOF", "UNEXPECTED_FIELD"),
])
def test_record_mutations_fail_before_digest_gate(consumer, policy, path, value, reason):
    record = json.loads(PUBLIC.read_bytes())
    node = record
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(consumer.ImportError, match=reason):
        run_import(consumer, policy, encoded(record))


def test_source_byte_and_self_rehashed_mutations_cannot_expand_trust(consumer, policy):
    with pytest.raises(consumer.ImportError, match="RECORD_BYTES_MISMATCH"):
        run_import(consumer, policy, PUBLIC.read_bytes() + b" ")
    changed = json.loads(PUBLIC.read_bytes())
    changed["title"] = "Forged source"
    with pytest.raises(consumer.ImportError, match="CONTENT_HASH_MISMATCH"):
        run_import(consumer, policy, encoded(changed))
    del changed["content_sha256"]
    changed["content_sha256"] = hashlib.sha256(encoded(changed)).hexdigest()
    forged_policy = json.loads(policy)
    forged_policy["record"]["content_sha256"] = changed["content_sha256"]
    forged_policy["record"]["sha256"] = hashlib.sha256(encoded(changed)).hexdigest()
    with pytest.raises(consumer.ImportError, match="UNAUTHORIZED_POLICY"):
        run_import(consumer, encoded(forged_policy), encoded(changed))


@pytest.mark.parametrize(("path", "value"), [
    (("admission", "verifier"), "arbitrary-verifier"),
    (("admission", "assumptions"), ["unchecked assumption"]),
    (("admission", "scope"), "all YAML"),
    (("admission", "outcome"), "VERIFIED_PROOF"),
    (("authorization",), "EXECUTE"),
    (("schema",), "mathgraph.import-trust-policy.v2"),
])
def test_even_self_pinned_policy_cannot_expand_authority(consumer, policy, path, value):
    mutated = json.loads(policy)
    node = mutated
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(consumer.ImportError, match="UNAUTHORIZED_POLICY"):
        run_import(consumer, encoded(mutated))


def test_external_policy_pin_is_required(consumer, policy):
    with pytest.raises(consumer.ImportError, match="POLICY_HASH_MISMATCH"):
        consumer.import_record(PUBLIC.read_bytes(), policy, "0" * 64)


@pytest.mark.parametrize(("raw", "reason"), [
    (b'{"schema":1,"schema":2}', "DUPLICATE_JSON_KEY"),
    (b'{"nested":{"x":1,"x":2}}', "DUPLICATE_JSON_KEY"),
    (b'{"x":NaN}', "NONFINITE_JSON_NUMBER"),
    (b'{"x":Infinity}', "NONFINITE_JSON_NUMBER"),
    (b'{"x":-Infinity}', "NONFINITE_JSON_NUMBER"),
    (b'{"x":1e999}', "NONFINITE_JSON_NUMBER"),
    (b'[]', "INVALID_ROOT_TYPE"), (b'null', "INVALID_ROOT_TYPE"),
    (b'\xff', "INVALID_JSON"), (b'\xef\xbb\xbf{}', "INVALID_JSON"),
    (b'{', "INVALID_JSON"),
    (b'{"x":' + b'[' * 2000 + b']' * 2000 + b'}', "INVALID_JSON"),
    (b' ' * 65537, "INPUT_TOO_LARGE"),
], ids=["duplicate", "nested-duplicate", "nan", "infinity", "negative-infinity", "float-overflow", "array", "null", "utf8", "bom", "syntax", "depth", "oversize"])
@pytest.mark.parametrize("target", ["record", "policy"])
def test_strict_bounded_json(consumer, policy, raw, reason, target):
    with pytest.raises(consumer.ImportError, match=reason):
        run_import(consumer, raw if target == "policy" else policy, raw if target == "record" else None)


def test_standalone_consumer_works_without_repository_imports(consumer, policy, tmp_path):
    standalone = tmp_path / "consumer.py"
    shutil.copyfile(HERE / "consumer.py", standalone)
    record = tmp_path / "record.json"
    record.write_bytes(PUBLIC.read_bytes())
    local_policy = tmp_path / "policy.json"
    local_policy.write_bytes(policy)
    args = ["--record", str(record), "--policy", str(local_policy), "--policy-sha256", hashlib.sha256(policy).hexdigest()]
    for script in [standalone, ROOT / "scripts/mathgraph_import_v1.py"]:
        process = subprocess.run([sys.executable, "-I", str(script), *args], cwd=tmp_path, capture_output=True)
        assert process.returncode == 0, process.stderr
        assert process.stderr == b""
        assert process.stdout == (HERE / "fixtures/result.json").read_bytes()


@pytest.mark.parametrize("path", ["https://example.test/record.json", "file:///tmp/record.json", "-", "/dev/zero"])
def test_cli_rejects_nonlocal_or_nonregular_inputs(consumer, policy, path):
    process = subprocess.run([
        sys.executable, str(HERE / "consumer.py"), "--record", path,
        "--policy", str(HERE / "fixtures/trust-policy.json"),
        "--policy-sha256", hashlib.sha256(policy).hexdigest(),
    ], capture_output=True, timeout=5)
    assert process.returncode == 1
    assert process.stdout == b""
    assert json.loads(process.stderr)["reason_code"] in {"LOCAL_PATH_REQUIRED", "REGULAR_FILE_REQUIRED"}
