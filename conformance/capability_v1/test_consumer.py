"""Independent finite replay, admission boundaries, and hostile input controls."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def consumer():
    path = HERE / "consumer.py"
    assert path.is_file(), "independent finite consumer missing"
    spec = importlib.util.spec_from_file_location("finite_consumer", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def inputs():
    return [(HERE / path).read_bytes() for path in (
        "fixtures/finite-representation-refinement-v1.json",
        "fixtures/capability-contract.json", "trust-policy.json")]


def evaluate(values=None, policy_pin=None):
    mod = consumer()
    values = inputs() if values is None else values
    return mod.qualify(*values, policy_pin or hashlib.sha256(values[2]).hexdigest())


def test_exact_finite_replay_qualifies_only_the_pinned_boundary():
    result = evaluate()
    evaluation, receipt = result["evaluation"], result["receipt"]
    assert evaluation["qualification"] == "QUALIFIED_BOUNDED"
    assert evaluation["validation"] == "VALID"
    assert evaluation["action_authorization"] == "NONE"
    assert evaluation["current_applicability"] == "UNKNOWN"
    assert all(evaluation[key] == "NOT_CHECKED" for key in ("freshness", "revocation", "supersession"))
    assert receipt["basis"] == "same-owner implementation-independent qualification"
    facts = receipt["replay"]
    assert facts["old_closure_masks"] == [0, 105, 150, 255]
    assert facts["obstruction_pairs"] == [[1, 4], [1, 7], [2, 4], [2, 7]]
    assert facts["successful_named_refinements"] == ["bit0"]
    assert facts["discovery_mask"] == 144
    assert facts["reuse_mask"] == 246
    assert facts["refined_closure_size"] == 16
    assert facts["retained_closure_masks"] == [0, 105, 150, 255]
    assert facts["boolean_refinements_tested"] == 256
    assert facts["successful_refinements"] == 32
    assert facts["failed_refinements"] == 224
    assert facts["successful_partition_classes"] == 8
    assert facts["successful_cell_count_distribution"] == {"3": 4, "4": 28}
    assert all(facts["checks"].values())
    assert facts["discovery_witness"] == [{"observations": [0, 0], "output": 0},
                                            {"observations": [0, 1], "output": 0},
                                            {"observations": [1, 0], "output": 0},
                                            {"observations": [1, 1], "output": 1}]
    assert "terminal_form" not in evaluation


def fixture_mutations():
    return [
        ("missing state", lambda d: d["states"].pop()),
        ("duplicate state", lambda d: d["states"].__setitem__(7, d["states"][0])),
        ("state bool", lambda d: d["states"][0].__setitem__(0, False)),
        ("changed target", lambda d: d["targets"]["discovery"]["vector"].__setitem__(0, 1)),
        ("changed refinement", lambda d: d["features"]["bit0"].__setitem__(0, 1)),
        ("incomplete policies", lambda d: d["coverage"].__setitem__("policy_masks", [0, 255])),
        ("incomplete refinements", lambda d: d["coverage"].__setitem__("refinement_masks", [0, 128])),
        ("sham substitution", lambda d: d.__setitem__("sham_refinement", "bit0")),
        ("lost retention", lambda d: d.__setitem__("refined_features", ["bit0"])),
        ("missing retention witness", lambda d: d["retained_targets"].pop()),
        ("fake ablation", lambda d: d.__setitem__("ablated_features", ["bit0"])),
        ("reuse same source", lambda d: d["targets"]["reuse"].__setitem__("source", d["targets"]["discovery"]["source"])),
        ("reuse same target", lambda d: d["targets"]["reuse"].__setitem__("vector", d["targets"]["discovery"]["vector"])),
        ("gate injection", lambda d: d.__setitem__("gates", {"all_passed": True})),
        ("verdict injection", lambda d: d.__setitem__("qualification", "QUALIFIED_BOUNDED")),
        ("circular receipt", lambda d: d.__setitem__("qualification_receipt", {"sha256": "a" * 64})),
    ]


@pytest.mark.parametrize("name,mutate", fixture_mutations(), ids=lambda x: x if isinstance(x, str) else None)
def test_replay_rejects_semantic_mutations_even_without_pin_checks(name, mutate):
    mod = consumer()
    fixture = json.loads(inputs()[0])
    mutate(fixture)
    with pytest.raises(mod.Rejected):
        mod.replay(fixture)


@pytest.mark.parametrize("index,path,value", [
    (0, ("selected_refinement",), "bit1"),
    (1, ("claim", "scope"), "all finite and infinite worlds"),
    (1, ("implementation", "sha256"), "a" * 64),
    (1, ("assumptions",), []),
    (1, ("profile",), "unsupported-profile"),
    (1, ("qualification",), "QUALIFIED_BOUNDED"),
    (1, ("evidence",), [{"id": "self-qualified-receipt"}]),
    (2, ("verifier", "sha256"), "b" * 64),
    (2, ("transport",), "https-fetch-and-execute"),
    (2, ("profile",), "unsupported-profile"),
    (2, ("qualification",), "QUALIFIED_BOUNDED"),
])
def test_changes_to_any_pinned_input_fail_closed(index, path, value):
    values = inputs()
    original_pin = hashlib.sha256(values[2]).hexdigest()
    data = json.loads(values[index])
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    values[index] = encode(data)
    result = evaluate(values, original_pin)
    assert result["evaluation"]["qualification"] == "UNKNOWN"
    assert result["receipt"] is None
    assert result["evaluation"]["action_authorization"] == "NONE"


@pytest.mark.parametrize("document", [b'{"id":1,"id":2}', b'{"nested":{"x":0,"x":1}}',
                                      b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'[]'])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_malformed_json_is_never_qualified(document, index):
    values = inputs()
    values[index] = document
    assert evaluate(values)["receipt"] is None


@pytest.mark.parametrize("field", ["contract", "fixture", "verifier"])
@pytest.mark.parametrize("value", [True, 1.0, -1])
def test_policy_sizes_cannot_exploit_python_number_equality(field, value):
    values = inputs()
    policy = json.loads(values[2])
    policy[field]["size_bytes"] = value
    values[2] = encode(policy)
    assert evaluate(values)["receipt"] is None


def test_rebound_policy_cannot_authorize_unsupported_transport_or_verifier():
    for path, value in [("transport", "remote"), ("profile", "other")]:
        values = inputs()
        policy = json.loads(values[2])
        policy[path] = value
        values[2] = encode(policy)
        assert evaluate(values)["receipt"] is None
    values = inputs()
    policy = json.loads(values[2])
    policy["verifier"]["sha256"] = "b" * 64
    values[2] = encode(policy)
    assert evaluate(values)["receipt"] is None


@pytest.mark.parametrize("index,field,value", [
    (1, "profile", "unsupported-profile"),
    (1, "assumptions", ["different assumptions"]),
    (2, "transport", "unsupported-transport"),
    (0, "selected_refinement", "bit1"),
])
def test_structural_validity_is_independent_of_pin_or_semantic_qualification(index, field, value):
    values = inputs()
    original_pin = hashlib.sha256(values[2]).hexdigest()
    data = json.loads(values[index])
    data[field] = value
    values[index] = encode(data)
    result = evaluate(values, original_pin)
    assert result["evaluation"]["validation"] == "VALID"
    assert result["evaluation"]["contract_sha256"] == hashlib.sha256(values[1]).hexdigest()
    assert result["evaluation"]["qualification"] == "UNKNOWN"
    assert result["receipt"] is None


@pytest.mark.parametrize("field,value,reason", [
    ("claim", {"id": "urn:mathgraph:claim:finite-representation-refinement:v1",
               "kind": "bounded-finite-representation-refinement", "scope": "universal invention"}, "SCOPE_MISMATCH"),
    ("assumptions", [], "ASSUMPTIONS_MISMATCH"),
    ("profile", "unsupported", "UNSUPPORTED_PROFILE"),
    ("qualification", "QUALIFIED_BOUNDED", "INVALID_FIELDS"),
    ("extensions", [{"id": "receipt", "critical": True, "version": "1",
                      "payload": {"qualified": True}}], "UNSUPPORTED_EXTENSION"),
])
def test_rebinding_a_policy_does_not_expand_the_implemented_profile(field, value, reason):
    values = inputs()
    contract = json.loads(values[1])
    contract[field] = value
    values[1] = encode(contract)
    policy = json.loads(values[2])
    policy["contract"]["sha256"] = hashlib.sha256(values[1]).hexdigest()
    policy["contract"]["size_bytes"] = len(values[1])
    values[2] = encode(policy)
    result = evaluate(values)
    assert result["receipt"] is None
    assert result["evaluation"]["reason_codes"] == [reason]


def test_rehashed_self_receipt_cannot_replace_original_source_evidence():
    values = inputs()
    contract = json.loads(values[1])
    contract["evidence"][0]["locator"] = "conformance/capability_v1/receipt.json"
    values[1] = encode(contract)
    policy = json.loads(values[2])
    policy["contract"].update(sha256=hashlib.sha256(values[1]).hexdigest(), size_bytes=len(values[1]))
    values[2] = encode(policy)
    result = evaluate(values)
    assert result["receipt"] is None
    assert result["evaluation"]["reason_codes"] == ["SOURCE_MISMATCH"]


def test_committed_admission_is_recomputed_and_byte_bound():
    mod = consumer()
    result = evaluate()
    for key in ("receipt", "evaluation"):
        assert encode(result[key]) == (HERE / f"{key}.json").read_bytes()
    registry_path = ROOT / "protocol/registries/capabilities-v1.json"
    assert registry_path.read_bytes() == (ROOT / "website/public/capabilities/index-v1.json").read_bytes()
    registry = json.loads(registry_path.read_bytes())
    assert len(registry["qualified_entries"]) == 1
    entry = registry["qualified_entries"][0]
    for field in ("contract", "evaluation", "qualification_receipt", "trust_policy"):
        ref = entry[field]
        raw = (ROOT / ref["locator"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ref["sha256"]
        assert len(raw) == ref["size_bytes"]
    assert entry["qualification_receipt"] == result["evaluation"]["qualification_receipt"]
    assert entry["trust_policy"] == result["evaluation"]["trust_policy"]


def test_schema_and_provenance_correspondence_without_importing_producer_logic():
    jsonschema = pytest.importorskip("jsonschema")
    fixture, contract, policy = map(json.loads, inputs())
    result = evaluate()
    for value, schema in [(contract, "protocol/schemas/capability-contract-v1.schema.json"),
                          (result["evaluation"], "protocol/schemas/capability-evaluation-v1.schema.json"),
                          (fixture, "conformance/capability_v1/fixtures/finite-profile.schema.json")]:
        jsonschema.validate(value, json.loads((ROOT / schema).read_bytes()))
    for ref in [contract["implementation"], *contract["evidence"],
                contract["inputs"][0]["schema"], contract["outputs"][0]["schema"]]:
        raw = (ROOT / ref["locator"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ref["sha256"]
        assert len(raw) == ref["size_bytes"]


def test_standalone_cli_with_only_four_files_and_no_package_imports(tmp_path):
    mod = consumer()
    sources = [(HERE / "consumer.py", "consumer.py"),
               (HERE / "trust-policy.json", "trust-policy.json"),
               (HERE / "fixtures/capability-contract.json", "capability-contract.json"),
               (HERE / "fixtures/finite-representation-refinement-v1.json", "finite.json")]
    for source, name in sources:
        shutil.copyfile(source, tmp_path / name)
    pin = hashlib.sha256(inputs()[2]).hexdigest()
    command = [sys.executable, "-I", "-S", "consumer.py", "--fixture", "finite.json",
               "--contract", "capability-contract.json", "--policy", "trust-policy.json",
               "--policy-sha256", pin, "--audit-imports"]
    first = subprocess.run(command, cwd=tmp_path, capture_output=True)
    second = subprocess.run(command, cwd=tmp_path, capture_output=True)
    assert first.returncode == 0, first.stderr
    assert first.stdout == second.stdout == encode(evaluate())
    audit = json.loads(first.stderr)
    assert audit["nonstdlib_modules"] == []
    assert audit["isolated"] and audit["no_site"]
    bad = subprocess.run(command[:-2] + ["0" * 64], cwd=tmp_path, capture_output=True)
    assert bad.returncode == 1
    assert json.loads(bad.stdout)["receipt"] is None


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS backend; Linux workflow exercises Docker")
def test_enforced_offline_isolation_replays_only_four_pinned_files():
    runner = HERE / "run_isolated.py"
    assert runner.is_file(), "four-input isolation harness missing"
    pin = hashlib.sha256(inputs()[2]).hexdigest()
    run = subprocess.run([sys.executable, str(runner), "--backend", "macos", "--policy-sha256", pin],
                         capture_output=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert run.stdout == encode(evaluate())
    metadata = json.loads(run.stderr)
    assert metadata["probe"]["network_denied"]
    assert metadata["probe"]["repository_unavailable"]
    assert metadata["probe"]["inputs"] == ["capability-contract.json", "consumer.py", "finite.json", "trust-policy.json"]
    assert metadata["replays_identical"]
    assert metadata["import_audit"]["nonstdlib_modules"] == []
