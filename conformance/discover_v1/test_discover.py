"""Contract, provenance, CLI and isolated-runtime checks for advisory Discover."""

import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "examples/evidence_packs/recursive_residual_transfer_v1_20260523"
FIXTURES = Path(__file__).parent / "fixtures"


def module(name="discover_v1"):
    assert (ROOT / "mathgraph_protocol" / f"{name}.py").is_file(), "Discover implementation missing"
    return importlib.import_module(f"mathgraph_protocol.{name}")


def candidate(identifier="route-a"):
    return {"candidate_id": identifier, "candidate_type": "replay_candidate",
            "source_ids": [], "title": "Replay candidate", "suggested_route": "bounded replay",
            "descension_target": "replay_validation", "advisory_only": True,
            "can_promote_truth": False, "expected_certificate_value": 0.5,
            "notes": "Not a VERIFIED_PROOF; cannot promote TRUE or FALSE."}


def request():
    return {"schema_version": "mathgraph.discover-request.v1", "request_id": "example",
            "policy": {"mode": "balanced", "beta": 1.0}, "top_k": 1,
            "candidates": [candidate()], "sources": [], "source_diagnostics": [],
            "reported_metrics": []}


def assert_boundary(result):
    assert result["schema_version"] == "mathgraph.discover-result.v1"
    assert result["advisory_only"] is True
    assert result["can_promote_truth"] is False
    assert result["verification_status"] == "NOT_CHECKED"
    assert result["attention_interpretation"] == "ALLOCATION_NOT_TRUTH_CONFIDENCE"
    assert "terminal_form" not in result


def test_ranks_without_interpreting_legitimate_disclaimers_as_promotion():
    result = module().discover(request())
    assert result["status"] == "OK"
    assert result["ranked_candidates"][0]["taste_score"] == 0.6
    assert result["ranked_candidates"][0]["attention_probability"] == 1.0
    assert_boundary(result)


@pytest.mark.parametrize("field,value", [
    ("schema_version", "mathgraph.discover-request.v2"), ("schema_version", []),
    ("top_k", True), ("top_k", -1), ("top_k", 1.0),
    ("unknown", 1), ("candidates", {}), ("request_id", ""),
])
def test_structural_request_errors(field, value):
    data = request()
    data[field] = value
    result = module().discover(data)
    assert result["status"] == "ERROR"
    assert_boundary(result)


@pytest.mark.parametrize("field,value", [
    ("verification_cost", -0.1), ("expected_reuse", True),
    ("novelty_score", float("nan")), ("novelty_score", float("inf")),
    ("novelty_score", "0.5"), ("novelty_score", 10**400),
    ("unknown", 0), ("terminal_form", "VERIFIED_PROOF"),
    ("can_promote_truth", 1), ("source_ids", ["missing"]),
])
def test_malformed_candidate_is_structural_error(field, value):
    data = request()
    data["candidates"][0][field] = value
    assert module().discover(data)["status"] == "ERROR"


@pytest.mark.parametrize("policy", [{"mode": [] , "beta": 1}, {"mode": "other", "beta": 1},
                                      {"mode": "balanced", "beta": True},
                                      {"mode": "balanced", "beta": -1},
                                      {"mode": "balanced", "beta": float("inf")}])
def test_invalid_policy(policy):
    data = request()
    data["policy"] = policy
    assert module().discover(data)["status"] == "ERROR"


def test_duplicate_ids_and_duplicate_keys():
    data = request()
    data["candidates"].append(candidate())
    assert module().discover(data)["reason_codes"] == ["DUPLICATE_ID"]
    for text in ['{"top_k":0,"top_k":1}', '{"policy":{"beta":1,"beta":2}}',
                 '{"top_k":NaN}', '{"top_k":1e999}', '[', 'null']:
        assert module().discover(text)["status"] == "ERROR"


def test_excessively_large_json_integer_returns_structural_error():
    result = module().discover('{"top_k":' + '1' * 5000 + '}')
    assert result["status"] == "ERROR"
    assert_boundary(result)


def test_multiple_invalid_numeric_fields_have_deterministic_error_priority():
    data = request()
    data["candidates"][0].update({"verification_cost": -1, "expected_reuse": "invalid"})
    code = "import sys; sys.path.insert(0, sys.argv[1]); from mathgraph_protocol.discover_v1 import discover, encode_result; sys.stdout.buffer.write(encode_result(discover(sys.argv[2])))"
    outputs = []
    for seed in range(1, 8):
        run = subprocess.run([sys.executable, "-S", "-c", code, str(ROOT), json.dumps(data)],
                             env={**os.environ, "PYTHONHASHSEED": str(seed)}, capture_output=True, check=True)
        outputs.append(run.stdout)
    assert len(set(outputs)) == 1
    assert json.loads(outputs[0])["reason_codes"] == ["INVALID_FIELD_TYPE"]


@pytest.mark.parametrize("change,code", [
    ({"descension_target": "accept_truth"}, "INVALID_DESCENSION_TARGET"),
    ({"can_promote_truth": True}, "TRUTH_PROMOTION_FORBIDDEN"),
    ({"advisory_only": False}, "ADVISORY_ONLY_REQUIRED"),
])
def test_semantic_rejection_all_invalid_and_partial(change, code):
    data = request()
    data["candidates"][0].update(change)
    result = module().discover(data)
    assert result["status"] == "UNKNOWN"
    assert result["rejected_candidates"][0]["reason_codes"] == [code]
    assert result["ranked_candidates"] == []
    data["candidates"].append(candidate("valid"))
    result = module().discover(data)
    assert result["status"] == "PARTIAL"
    assert result["ranked_candidates"][0]["candidate_id"] == "valid"
    assert_boundary(result)


def test_empty_zero_selection_and_deterministic_ties():
    data = request()
    data["candidates"] = []
    assert module().discover(data)["status"] == "UNKNOWN"
    data["candidates"] = [candidate("b"), candidate("a")]
    data["top_k"] = 0
    result = module().discover(data)
    assert result["status"] == "OK"
    assert [row["candidate_id"] for row in result["ranked_candidates"]] == ["a", "b"]
    assert [row["attention_probability"] for row in result["ranked_candidates"]] == [0.5, 0.5]
    assert not any(row["selected"] for row in result["ranked_candidates"])
    data["candidates"].reverse()
    assert module().discover(data) == result


def test_arithmetic_overflow_is_machine_readable_error():
    data = request()
    data["policy"]["beta"] = 1e308
    data["candidates"][0]["expected_certificate_value"] = 1e308
    assert module().discover(data)["reason_codes"] == ["NUMERIC_OVERFLOW"]


def test_source_adapter_exact_pins_missing_material_and_fixture():
    data = module("discover_sources_v1").request_from_recursive_transfer(PACK)
    assert data == json.loads((FIXTURES / "request.json").read_text())
    artifact_sources = [source for source in data["sources"] if source["bundle"]]
    assert sum(source["availability"] == "PRESENT" for source in artifact_sources) == 9
    ledger = next(source for source in artifact_sources if source["source_id"] == "sqlite_ledger")
    assert ledger["sha256"] == "4f8e9ec5d88e80ccafa22efdf970c102fd29d18145a3d33abc62a45d68a264dd"
    assert ledger["size_bytes"] == 458752
    assert ledger["availability"] == "MISSING"
    assert ledger["required_for_full_replay"] is True
    assert any("FULL_REPLAY_UNAVAILABLE" in text for text in data["source_diagnostics"])
    metrics = {item["name"]: item["value"] for item in data["reported_metrics"]}
    assert metrics["compact_transfer_gain_vs_generic_positive"] == 234.166667
    result = module().discover(data)
    assert result["status"] == "PARTIAL"
    assert result["sources"] == data["sources"]
    assert result["reported_metrics"] == data["reported_metrics"]
    assert module().encode_result(result) == (FIXTURES / "result.json").read_bytes()
    assert_boundary(result)


@pytest.mark.parametrize("target", ["manifest.json", "metrics.json", "source_summary", "gate_results"])
def test_source_digest_mismatch(tmp_path, target):
    copied = tmp_path / PACK.name
    shutil.copytree(PACK, copied)
    if target.endswith(".json"):
        path = copied / target
    else:
        manifest = json.loads((copied / "manifest.json").read_text())
        path = copied / "source_artifacts" / next(row["filename"] for row in manifest["artifacts"] if row["role"] == target)
    with path.open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError, match="SOURCE_(SIZE|DIGEST)_MISMATCH"):
        module("discover_sources_v1").request_from_recursive_transfer(copied)


def test_same_size_artifact_tamper_is_digest_error(tmp_path):
    copied = tmp_path / PACK.name
    shutil.copytree(PACK, copied)
    path = next((copied / "source_artifacts").glob("*recursive_transfer_summary.json"))
    payload = path.read_bytes()
    path.write_bytes(b" " + payload[1:])
    with pytest.raises(ValueError, match="SOURCE_DIGEST_MISMATCH"):
        module("discover_sources_v1").request_from_recursive_transfer(copied)


def test_duplicate_source_ids_and_injected_source_fields():
    data = json.loads((FIXTURES / "request.json").read_text())
    data["sources"].append(copy.deepcopy(data["sources"][0]))
    assert module().discover(data)["reason_codes"] == ["DUPLICATE_ID"]
    data["sources"].pop()
    data["sources"][0]["verified"] = True
    assert module().discover(data)["reason_codes"] == ["UNKNOWN_FIELD"]


def test_missing_copied_artifact_is_explicit_not_success(tmp_path):
    copied = tmp_path / PACK.name
    shutil.copytree(PACK, copied)
    next((copied / "source_artifacts").glob("*gate_results.csv")).unlink()
    data = module("discover_sources_v1").request_from_recursive_transfer(copied)
    source = next(row for row in data["sources"] if row["source_id"] == "gate_results")
    assert source["availability"] == "MISSING"
    assert "MISSING_LOCAL_ARTIFACT: gate_results" in data["source_diagnostics"]


def test_schema_projection_and_fixture_versions():
    for kind in ("request", "result"):
        root = ROOT / f"protocol/schemas/discover-{kind}-v1.schema.json"
        assert root.is_file(), "normative schema missing"
        assert root.read_bytes() == (ROOT / f"website/public/schemas/{root.name}").read_bytes()
        schema = json.loads(root.read_text())
        assert schema["properties"]["schema_version"]["const"] == f"mathgraph.discover-{kind}.v1"
        assert schema["additionalProperties"] is False


@pytest.mark.parametrize("status", ["OK", "PARTIAL", "UNKNOWN", "ERROR"])
def test_cli_exit_semantics(tmp_path, status):
    data = request()
    if status == "PARTIAL":
        data["candidates"].append({**candidate("invalid"), "can_promote_truth": True})
    elif status == "UNKNOWN":
        data["candidates"] = []
    elif status == "ERROR":
        data["top_k"] = True
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data))
    run = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "scripts/mathgraph_discover_v1.py"), "--request", str(path)], capture_output=True)
    assert run.returncode == (1 if status == "ERROR" else 0), run.stderr
    assert json.loads(run.stdout)["status"] == status


def test_cli_missing_file_is_json_error(tmp_path):
    run = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "scripts/mathgraph_discover_v1.py"), "--request", str(tmp_path / "missing")], capture_output=True)
    assert run.returncode == 1
    assert json.loads(run.stdout)["status"] == "ERROR"
    assert b"Traceback" not in run.stderr


def test_isolated_package_without_network_or_other_mathgraph_modules(tmp_path):
    shutil.copytree(ROOT / "mathgraph_protocol", tmp_path / "mathgraph_protocol", ignore=shutil.ignore_patterns("__pycache__"))
    assert (FIXTURES / "request.json").is_file(), "pinned request missing"
    code = '''
import sys, pathlib
sys.path.insert(0, sys.argv[1])
def audit(event, args):
    if event.startswith("socket.") or event.startswith("subprocess.") or event in {"os.system", "os.posix_spawn"}:
        raise RuntimeError("network and process execution denied")
sys.addaudithook(audit)
import socket
try:
    socket.socket()
except RuntimeError as error:
    assert str(error) == "network and process execution denied"
else:
    raise AssertionError("network audit guard is not active")
class Guard:
    def find_spec(self, fullname, *args):
        if fullname.split(".")[0] in {"mathgraph", "numpy", "pandas", "matplotlib", "requests", "website", "adapters"}:
            raise ImportError("forbidden dependency: " + fullname)
sys.meta_path.insert(0, Guard())
from mathgraph_protocol.discover_v1 import discover, encode_result
from mathgraph_protocol.discover_sources_v1 import request_from_recursive_transfer
payload = pathlib.Path(sys.argv[2]).read_bytes()
derived = request_from_recursive_transfer(sys.argv[3])
assert encode_result(discover(derived)) == encode_result(discover(payload))
first, second = encode_result(discover(payload)), encode_result(discover(payload))
assert first == second
sys.stdout.buffer.write(first)
'''
    run = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(tmp_path), str(FIXTURES / "request.json"), str(PACK)], cwd=tmp_path, capture_output=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout == (FIXTURES / "result.json").read_bytes()
