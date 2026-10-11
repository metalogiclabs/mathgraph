"""Portable descriptors cannot self-qualify or authorize execution."""

import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


def module():
    assert (ROOT / "mathgraph_protocol/capability_v1.py").is_file(), "capability evaluator missing"
    return importlib.import_module("mathgraph_protocol.capability_v1")


def artifact(identifier):
    return {"id": identifier, "locator": "urn:example:" + identifier,
            "sha256": "a" * 64, "size_bytes": 10, "media_type": "application/json"}


def contract():
    return {"schema_version": "mathgraph.capability-contract.v1", "id": "urn:example:capability",
            "version": "1", "profile": "urn:example:finite:v1",
            "claim": {"id": "urn:example:claim", "kind": "bounded-constructor", "scope": "eight states"},
            "inputs": [{"type_id": "urn:example:input", "schema": artifact("input-schema")}],
            "outputs": [{"type_id": "urn:example:output", "schema": artifact("output-schema")}],
            "preconditions": ["Declared finite carrier"], "guarantees": ["Bounded witness"],
            "assumptions": ["Exact action language"], "boundary": artifact("boundary"),
            "implementation": artifact("implementation"), "evidence": [artifact("evidence")],
            "limitations": ["No claim outside this carrier"], "extensions": []}


def assert_unknown(result, validation="VALID"):
    assert result["validation"] == validation
    assert result["qualification"] == "UNKNOWN"
    assert result["qualification_receipt"] is None
    assert result["trust_policy"] is None
    assert result["freshness"] == "NOT_CHECKED"
    assert result["revocation"] == "NOT_CHECKED"
    assert result["supersession"] == "NOT_CHECKED"
    assert result["current_applicability"] == "UNKNOWN"
    assert result["action_authorization"] == "NONE"
    assert "terminal_form" not in result


def test_structurally_valid_descriptor_remains_unqualified_and_unmutated():
    data = contract()
    before = copy.deepcopy(data)
    result = module().evaluate_contract(data)
    assert_unknown(result)
    assert result["contract"] == {"id": "urn:example:capability", "version": "1", "profile": "urn:example:finite:v1"}
    assert result["reason_codes"] == ["UNSUPPORTED_PROFILE", "NO_ADMITTED_RECEIPT"]
    assert data == before


@pytest.mark.parametrize("field,value,code", [
    ("id", " ", "INVALID_TEXT"), ("version", "", "INVALID_TEXT"),
    ("profile", [], "INVALID_TEXT"), ("limitations", [], "LIMITATIONS_REQUIRED"),
    ("limitations", [""], "INVALID_TEXT"), ("schema_version", "other", "UNSUPPORTED_VERSION"),
    ("qualification", "QUALIFIED_BOUNDED", "UNKNOWN_FIELD"),
    ("status", "VERIFIED", "UNKNOWN_FIELD"), ("verified", True, "UNKNOWN_FIELD"),
    ("terminal_form", "VERIFIED_PROOF", "UNKNOWN_FIELD"),
])
def test_structural_rejection_is_not_a_refutation(field, value, code):
    data = contract()
    data[field] = value
    result = module().evaluate_contract(data)
    assert_unknown(result, "INVALID")
    assert result["reason_codes"] == [code]
    assert result["contract"] is None


@pytest.mark.parametrize("field", ["sha256", "size_bytes", "locator", "media_type", "id"])
def test_artifact_pins_are_required(field):
    data = contract()
    del data["boundary"][field]
    assert module().evaluate_contract(data)["validation"] == "INVALID"


@pytest.mark.parametrize("value", ["a" * 63, "A" * 64, "g" * 64, 12, None])
def test_malformed_digests(value):
    data = contract()
    data["implementation"]["sha256"] = value
    assert module().evaluate_contract(data)["reason_codes"] == ["INVALID_DIGEST"]


@pytest.mark.parametrize("value", [True, -1, 1.5, "10"])
def test_artifact_size_is_exact_nonnegative_integer(value):
    data = contract()
    data["evidence"][0]["size_bytes"] = value
    assert module().evaluate_contract(data)["reason_codes"] == ["INVALID_SIZE"]


@pytest.mark.parametrize("field", ["inputs", "outputs", "evidence", "extensions"])
def test_duplicate_ids(field):
    data = contract()
    if field == "extensions":
        data[field] = [{"id": "urn:example:ext", "version": "1", "critical": False, "payload": {}}]
    data[field].append(copy.deepcopy(data[field][0]))
    assert module().evaluate_contract(data)["reason_codes"] == ["DUPLICATE_ID"]


@pytest.mark.parametrize("document,code", [
    ('{"id":"one","id":"two"}', "DUPLICATE_KEY"),
    ('{"x":{"id":1,"id":2}}', "DUPLICATE_KEY"),
    ('{"x":NaN}', "INVALID_NUMBER"), ('{"x":1e999}', "INVALID_NUMBER"),
    ('[', "INVALID_JSON"), ('null', "INVALID_FIELD_TYPE"),
])
def test_strict_parsing(document, code):
    result = module().evaluate_contract(document)
    assert_unknown(result, "INVALID")
    assert result["reason_codes"] == [code]


def test_unsupported_extensions_are_never_interpreted_as_qualification():
    data = contract()
    data["extensions"] = [{"id": "urn:unknown", "version": "1", "critical": True,
                           "payload": {"status": "VERIFIED"}}]
    result = module().evaluate_contract(data)
    assert_unknown(result)
    assert "UNSUPPORTED_CRITICAL_EXTENSION" in result["reason_codes"]
    data["extensions"][0]["critical"] = False
    result = module().evaluate_contract(data)
    assert_unknown(result)
    assert "NONCRITICAL_EXTENSION_IGNORED" in result["reason_codes"]


@pytest.mark.parametrize("field,value,code", [
    ("id", "urn:other", "IDENTITY_MISMATCH"),
    ("version", "2", "IDENTITY_MISMATCH"),
    ("profile", "urn:other", "PROFILE_MISMATCH"),
    ("claim", {"id": "urn:example:claim", "kind": "bounded-constructor", "scope": "nine states"}, "CLAIM_SCOPE_MISMATCH"),
    ("assumptions", ["Different action language"], "ASSUMPTIONS_MISMATCH"),
    ("implementation", artifact("other-source"), "SOURCE_MISMATCH"),
    ("boundary", artifact("other-boundary"), "BOUNDARY_MISMATCH"),
    ("guarantees", ["Unbounded guarantee"], "CONTRACT_MISMATCH"),
])
def test_exact_consumer_binding_mismatches_remain_unknown(field, value, code):
    expected = contract()
    changed = contract()
    changed[field] = value
    result = module().evaluate_contract(changed, expected_contract=expected)
    assert_unknown(result)
    assert code in result["reason_codes"]


def test_identical_expected_contract_is_not_an_admitted_receipt():
    result = module().evaluate_contract(contract(), expected_contract=contract())
    assert_unknown(result)
    assert not any("MISMATCH" in reason for reason in result["reason_codes"])


@pytest.mark.parametrize("before,after", [(True, 1), (1, True), (False, 0), (0, False),
                                          (True, 1.0), (1.0, True), (False, 0.0), (0.0, False)])
def test_exact_snapshot_binding_distinguishes_nested_booleans_and_numbers(before, after):
    expected = contract()
    expected["extensions"] = [{"id": "urn:ext", "version": "1", "critical": False,
                               "payload": {"nested": [{"value": before}]}}]
    supplied = copy.deepcopy(expected)
    supplied["extensions"][0]["payload"]["nested"][0]["value"] = after
    result = module().evaluate_contract(supplied, expected_contract=expected)
    assert_unknown(result)
    assert "CONTRACT_MISMATCH" in result["reason_codes"]


def test_evaluation_binds_exact_descriptor_bytes_without_normalization():
    data = contract()
    data["id"] = "URN:Example:Capability"
    payload = json.dumps(data, indent=4).encode() + b"\n\n"
    result = module().evaluate_contract(payload)
    assert result["contract"]["id"] == "URN:Example:Capability"
    assert result["contract_sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["contract_size_bytes"] == len(payload)


def test_nonfinite_extension_payload_cannot_bypass_dictionary_validation():
    data = contract()
    data["extensions"] = [{"id": "urn:ext", "version": "1", "critical": False,
                           "payload": {"value": float("nan")}}]
    assert module().evaluate_contract(data)["validation"] == "INVALID"


def test_registry_empty_qualified_entries_and_separate_experimental_candidates():
    path = ROOT / "protocol/registries/capabilities-v1.json"
    assert path.is_file(), "versioned registry missing"
    registry = json.loads(path.read_bytes())
    module().validate_registry(registry)
    assert registry["qualified_entries"] == []
    assert registry["experimental_candidates"]
    assert all(row["status"] == "EXPERIMENTAL" for row in registry["experimental_candidates"])
    assert path.read_bytes() == (ROOT / "website/public/capabilities/index-v1.json").read_bytes()
    registry["experimental_candidates"].append(copy.deepcopy(registry["experimental_candidates"][0]))
    with pytest.raises(module().CapabilityValidationError, match="DUPLICATE_ID"):
        module().validate_registry(registry)


def test_registry_cannot_replace_receipts_with_qualification_labels():
    data = {"schema_version": "mathgraph.capability-registry.v1", "id": "urn:registry", "version": "1",
            "qualified_entries": [{"id": "urn:cap", "version": "1", "profile": "urn:profile",
                                   "qualification": "QUALIFIED_BOUNDED"}], "experimental_candidates": []}
    with pytest.raises(module().CapabilityValidationError):
        module().validate_registry(data)


def test_normative_schema_public_projections_and_closed_descriptor():
    for kind in ("contract", "evaluation", "registry"):
        path = ROOT / f"protocol/schemas/capability-{kind}-v1.schema.json"
        assert path.is_file(), "normative schema missing"
        assert path.read_bytes() == (ROOT / "website/public/schemas" / path.name).read_bytes()
        schema = json.loads(path.read_bytes())
        assert schema["additionalProperties"] is False
        assert schema["properties"]["schema_version"]["const"] == f"mathgraph.capability-{kind}.v1"


def test_schema_validation_cannot_turn_a_status_label_into_qualification():
    jsonschema = pytest.importorskip("jsonschema")  # Development-only schema cross-check.
    schemas = {}
    for kind in ("contract", "evaluation", "registry"):
        path = ROOT / f"protocol/schemas/capability-{kind}-v1.schema.json"
        assert path.is_file(), "normative schema missing"
        schemas[kind] = json.loads(path.read_bytes())
        jsonschema.Draft202012Validator.check_schema(schemas[kind])
    jsonschema.validate(contract(), schemas["contract"])
    result = module().evaluate_contract(contract())
    jsonschema.validate(result, schemas["evaluation"])
    invalid = module().evaluate_contract('{"id":1,"id":2}')
    jsonschema.validate(invalid, schemas["evaluation"])
    result["qualification"] = "QUALIFIED_BOUNDED"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(result, schemas["evaluation"])
    result["qualification_receipt"] = artifact("receipt")
    result["trust_policy"] = artifact("policy")
    jsonschema.validate(result, schemas["evaluation"])  # Structure is not admission.
    result["validation"] = "INVALID"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(result, schemas["evaluation"])
    bad = contract()
    bad["qualification"] = "VERIFIED"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schemas["contract"])
    registry = json.loads((ROOT / "protocol/registries/capabilities-v1.json").read_bytes())
    jsonschema.validate(registry, schemas["registry"])


def test_registry_candidate_source_pins_match_local_source_bytes():
    path = ROOT / "protocol/registries/capabilities-v1.json"
    assert path.is_file(), "versioned registry missing"
    for row in json.loads(path.read_bytes())["experimental_candidates"]:
        source = row["source"]
        raw = (ROOT / source["locator"]).read_bytes()
        assert len(raw) == source["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]


@pytest.mark.parametrize("mode", ["valid", "invalid", "duplicate", "missing"])
def test_isolated_cli_exit_semantics(tmp_path, mode):
    data = contract()
    if mode == "invalid":
        data["status"] = "VERIFIED"
    path = tmp_path / "contract.json"
    if mode != "missing":
        path.write_text('{"id":1,"id":2}' if mode == "duplicate" else json.dumps(data))
    run = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "scripts/mathgraph_capability_v1.py"),
                          "--contract", str(path)], capture_output=True)
    assert run.returncode == (0 if mode == "valid" else 1), run.stderr
    result = json.loads(run.stdout)
    assert_unknown(result, "VALID" if mode == "valid" else "INVALID")
    assert b"Traceback" not in run.stderr


@pytest.mark.parametrize("field", ["claim", "inputs", "outputs", "preconditions", "guarantees",
                                  "assumptions", "boundary", "implementation", "evidence", "extensions"])
def test_required_fields_cannot_be_omitted(field):
    data = contract()
    del data[field]
    assert module().evaluate_contract(data)["reason_codes"] == ["MISSING_FIELD"]


def test_conflicting_artifact_identity_and_nested_status_are_rejected():
    data = contract()
    data["implementation"]["id"] = "boundary"
    assert module().evaluate_contract(data)["reason_codes"] == ["CONFLICTING_ARTIFACT_ID"]
    data = contract()
    data["claim"]["verified"] = True
    assert module().evaluate_contract(data)["reason_codes"] == ["UNKNOWN_FIELD"]


def test_cli_exact_binding_invalid_arguments_and_registry_cross_index_duplicates(tmp_path):
    expected = tmp_path / "expected.json"
    supplied = tmp_path / "supplied.json"
    data = contract()
    expected.write_text(json.dumps(data))
    data["claim"]["scope"] = "Changed scope"
    supplied.write_text(json.dumps(data))
    command = [sys.executable, "-I", "-S", str(ROOT / "scripts/mathgraph_capability_v1.py")]
    run = subprocess.run(command + ["--contract", str(supplied), "--expected-contract", str(expected)], capture_output=True)
    assert run.returncode == 0, run.stderr
    assert "CLAIM_SCOPE_MISMATCH" in json.loads(run.stdout)["reason_codes"]
    run = subprocess.run(command + ["--execute"], capture_output=True)
    assert run.returncode == 1
    assert json.loads(run.stdout)["reason_codes"] == ["INVALID_ARGUMENTS"]
    registry = json.loads((ROOT / "protocol/registries/capabilities-v1.json").read_bytes())
    candidate = registry["experimental_candidates"][0]
    registry["qualified_entries"].append({key: candidate[key] for key in ("id", "version", "profile")})
    registry["qualified_entries"][0].update({key: artifact(key) for key in
                                          ("contract", "evaluation", "qualification_receipt", "trust_policy")})
    with pytest.raises(module().CapabilityValidationError, match="DUPLICATE_ID"):
        module().validate_registry(registry)


def test_isolated_evaluator_performs_no_io_or_process_execution(tmp_path):
    import shutil
    shutil.copytree(ROOT / "mathgraph_protocol", tmp_path / "mathgraph_protocol",
                    ignore=shutil.ignore_patterns("__pycache__"))
    code = '''
import sys
sys.path.insert(0, sys.argv[1])
class Guard:
    def find_spec(self, fullname, *args):
        if fullname.split(".")[0] in {"mathgraph", "numpy", "pandas", "requests", "adapters", "jsonschema"}:
            raise ImportError("forbidden dependency: " + fullname)
sys.meta_path.insert(0, Guard())
from mathgraph_protocol.capability_v1 import evaluate_contract, encode_result
def audit(event, args):
    if event == "open" or event.startswith("socket.") or event.startswith("subprocess.") or event in {"os.system", "os.posix_spawn"}:
        raise RuntimeError("I/O and execution denied")
sys.addaudithook(audit)
try:
    open("forbidden-write", "w")
except RuntimeError:
    pass
else:
    raise AssertionError("audit guard not active")
first = encode_result(evaluate_contract(sys.argv[2]))
assert first == encode_result(evaluate_contract(sys.argv[2]))
sys.stdout.buffer.write(first)
'''
    data = contract()
    data["implementation"]["locator"] = "https://example.invalid/do-not-fetch"
    run = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(tmp_path), json.dumps(data)],
                         cwd=tmp_path, capture_output=True)
    assert run.returncode == 0, run.stderr
    assert_unknown(json.loads(run.stdout))
