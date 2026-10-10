"""Publication gate: pinned bytes, kernel-derived scenarios, and honest labels."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from mathgraph_check.living_warrants import verify_snapshot


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence/living_warrant_openai_jpl_20261010.json"
SCRIPT = ROOT / "scripts/publish_mathgraph_resolve_v1.py"
RECORD_ID = "mg-living-warrant-openai-jpl-20261010"
TRANSPORT = "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87"
PAYLOAD = "b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41"
JPL = "jpl.l4yaml.finite_parser_acceptance"
JPL_RECEIPT = "mathgraph.l4yaml.48-case-qualification"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"


def load_publisher():
    assert SCRIPT.is_file(), "Deterministic Resolve publisher is missing"
    spec = importlib.util.spec_from_file_location("resolve_publisher", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_scenarios():
    return load_publisher().build_scenarios(SOURCE.read_bytes())


def indexed(section):
    return {scenario["id"]: scenario for scenario in section["scenarios"]}


def test_publication_preserves_exact_qualified_snapshot_and_canonical_scenarios(tmp_path):
    publisher = load_publisher()
    publisher.publish(SOURCE, tmp_path)
    raw = SOURCE.read_bytes()
    assert len(raw) == 5290
    assert sha256(raw).hexdigest() == TRANSPORT
    payload = json.loads(raw)
    assert payload.pop("snapshot_sha256") == PAYLOAD
    assert sha256(canonical(payload)[:-1]).hexdigest() == PAYLOAD
    for target in [tmp_path / "src/data/resolve-record.json",
                   tmp_path / f"public/evidence/{RECORD_ID}/record.json"]:
        assert target.read_bytes() == raw
    generated = (tmp_path / "src/data/resolve-scenarios.json").read_bytes()
    assert generated == canonical(json.loads(generated))
    assert generated == (tmp_path / f"public/evidence/{RECORD_ID}/scenarios.json").read_bytes()
    publisher.publish(SOURCE, tmp_path)
    assert generated == (tmp_path / "src/data/resolve-scenarios.json").read_bytes()


@pytest.mark.parametrize("mutation", ["whitespace", "rehashed_claim", "truncated"])
def test_altered_source_is_rejected_before_any_output(tmp_path, mutation):
    publisher = load_publisher()
    raw = SOURCE.read_bytes()
    if mutation == "whitespace":
        raw += b"\n"
    elif mutation == "rehashed_claim":
        value = json.loads(raw)
        value["resolutions"]["openai.theorem.1"]["after"] = "WARRANTED_BOUNDED"
        value.pop("snapshot_sha256")
        value["snapshot_sha256"] = sha256(canonical(value)[:-1]).hexdigest()
        raw = canonical(value)
    else:
        raw = raw[:-1]
    source = tmp_path / "altered.json"
    source.write_bytes(raw)
    output = tmp_path / "website"
    with pytest.raises(ValueError, match="SOURCE_BYTES_MISMATCH"):
        publisher.publish(source, output)
    assert not output.exists()


def test_same_length_rehashed_source_is_rejected_by_external_transport_pin(tmp_path):
    publisher = load_publisher()
    original = SOURCE.read_bytes()
    value = json.loads(original)
    assert value["sources"]["openai"]["notice_date"] == "2026-10-07"
    value["sources"]["openai"]["notice_date"] = "2026-10-08"
    value.pop("snapshot_sha256")
    value["snapshot_sha256"] = sha256(canonical(value)[:-1]).hexdigest()
    substituted = canonical(value)

    # This forgery passes length, canonical encoding, and internal integrity;
    # only an externally fixed identity can reject its changed source notice.
    assert len(substituted) == len(original) == 5290
    assert substituted == canonical(json.loads(substituted))
    assert verify_snapshot(json.loads(substituted)) is True
    assert substituted != original
    assert sha256(substituted).hexdigest() != TRANSPORT

    source = tmp_path / "same-length-rehashed.json"
    source.write_bytes(substituted)
    output = tmp_path / "website"
    with pytest.raises(ValueError, match="^SOURCE_BYTES_MISMATCH$"):
        publisher.publish(source, output)
    assert not output.exists()


def test_historical_before_is_modeled_and_after_replays_exact_record():
    scenarios = load_scenarios()
    section = scenarios["PUBLISHED_RECORD"]
    assert section["classification"] == "PUBLISHED_RECORD"
    cases = indexed(section)
    before, after = cases["modeled-before"], cases["published-after"]
    assert before["basis"] == "MODELED_BEFORE"
    assert after["basis"] == "PUBLISHED_AFTER"
    assert before["withdrawn_evidence"] == []
    assert after["resolutions"] == json.loads(SOURCE.read_bytes())["resolutions"]
    for number in (1, 2, 3):
        support, theorem = f"openai.original_support.{number}", f"openai.theorem.{number}"
        assert before["states"][support] == "SOURCE_DOCUMENTED"
        assert after["states"][support] == "UNKNOWN"
        assert after["resolutions"][support]["after"] == "STALE"
        assert before["states"][theorem] == after["states"][theorem] == "UNKNOWN"
    assert before["states"][JPL] == after["states"][JPL] == "WARRANTED_BOUNDED"
    source_graph = json.loads(SOURCE.read_bytes())["derivation"]
    for field in ("claims", "receipts", "routes"):
        assert sorted(section["graph"][field], key=canonical) == sorted(source_graph[field], key=canonical)


def test_single_dependency_simulations_are_complete_and_localized():
    scenarios = load_scenarios()
    section = scenarios["PUBLISHED_RECORD"]
    cases = section["scenarios"]
    simulations = [case for case in cases if case["basis"] == "SIMULATION"]
    assert {tuple(case["withdrawn_evidence"]) for case in simulations} == {
        (JPL_RECEIPT,), *( (f"openai.original_publication_receipt.{n}",) for n in (1, 2, 3))
    }
    baseline = indexed(section)["modeled-before"]["states"]
    for case in simulations:
        assert case["baseline"] == "modeled-before"
        receipt = case["withdrawn_evidence"][0]
        affected = JPL if receipt == JPL_RECEIPT else f"openai.original_support.{receipt[-1]}"
        assert {claim for claim, status in case["states"].items() if status != baseline[claim]} == {affected}
        assert case["resolutions"][affected]["after"] == "STALE"
        assert case["states"][affected] == "UNKNOWN"


def test_synthetic_cases_are_kernel_tests_with_literal_expected_outcomes():
    scenarios = load_scenarios()
    section = scenarios["SYNTHETIC_CONFORMANCE"]
    assert section["classification"] == "SYNTHETIC_CONFORMANCE"
    assert section["historical_fact"] is False
    assert section["purpose"] == "KERNEL_TESTS"
    cases = indexed(section)
    assert cases["alternative-route"]["states"] == {"A": "UNKNOWN", "B": "WARRANTED_BOUNDED", "C": "WARRANTED_BOUNDED"}
    assert cases["localized-invalidation"]["states"] == {"A": "UNKNOWN", "B": "UNKNOWN", "C": "WARRANTED_BOUNDED"}
    assert cases["rootless-cycle"]["states"] == {"A": "UNKNOWN", "B": "UNKNOWN"}
    for case in cases.values():
        assert case["basis"] == "KERNEL_TEST"
        assert all(item["scope"] == "synthetic-conformance" for item in case["graph"]["claims"])


def test_scenarios_include_exact_provenance_and_maturity_boundaries():
    scenarios = load_scenarios()
    assert scenarios["record_id"] == RECORD_ID
    assert scenarios["transport_sha256"] == TRANSPORT
    assert scenarios["snapshot_sha256"] == PAYLOAD
    provenance = scenarios["provenance"]
    assert provenance["producer"]["commit"] == "040456fc8862c79c8b384ce63846628274b678be"
    assert provenance["producer"]["run_id"] == "38025044631"
    consumer = provenance["consumer"]
    assert consumer["commit"] == "9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3"
    assert consumer["run_id"] == "38025236380"
    assert consumer["implementation_independent"] is True
    assert consumer["same_owner"] is True
    assert consumer["independently_owned_adoption"] is False
    assert consumer["reruns_jpl_lean_proof"] is False
    assert scenarios["maturity"]["runtime_status"] == "IMMUTABLE_HISTORICAL_SNAPSHOT_NOT_CONTINUOUSLY_MONITORED"
    assert scenarios["maturity"]["action_policy"] == "READ_ONLY_PRECOMPUTED_SELECTION"


def test_all_section_scenario_ids_and_graph_arrays_are_sorted():
    scenarios = load_scenarios()
    for key in ("PUBLISHED_RECORD", "SYNTHETIC_CONFORMANCE"):
        section = scenarios[key]
        ids = [case["id"] for case in section["scenarios"]]
        assert ids == sorted(set(ids))
        graphs = [section["graph"]] if "graph" in section else [case["graph"] for case in section["scenarios"]]
        for graph in graphs:
            for field in ("claims", "receipts"):
                assert [item["id"] for item in graph[field]] == sorted(item["id"] for item in graph[field])
            assert graph["routes"] == sorted(graph["routes"], key=canonical)


def test_committed_assets_match_regeneration(tmp_path):
    publisher = load_publisher()
    publisher.publish(SOURCE, tmp_path)
    for relative in ("src/data/resolve-record.json", "src/data/resolve-scenarios.json",
                     f"public/evidence/{RECORD_ID}/record.json", f"public/evidence/{RECORD_ID}/scenarios.json"):
        assert (ROOT / "website" / relative).read_bytes() == (tmp_path / relative).read_bytes()


def test_cli_check_detects_changed_artifacts_without_rewriting(tmp_path):
    load_publisher()
    command = [sys.executable, str(SCRIPT), "--source", str(SOURCE), "--output-dir", str(tmp_path)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    assert subprocess.run(command + ["--check"], capture_output=True).returncode == 0
    target = tmp_path / "src/data/resolve-scenarios.json"
    target.write_bytes(b"{}\n")
    result = subprocess.run(command + ["--check"], capture_output=True)
    assert result.returncode != 0
    assert b"PUBLICATION_BYTES_MISMATCH" in result.stderr
    assert target.read_bytes() == b"{}\n"
