"""Qualify a bounded event-time Compose counterfactual on untouched JPL parser trees.

This script intentionally does not promote a tree approximation to a graph
identity/cycle theorem. It reports a family-level oracle comparison.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def parse_output(obj):
    require(isinstance(obj, dict) and obj.get("status") in ("ok", "error"),
            "BAD_NATIVE_RECORD")
    if obj["status"] == "error":
        require(set(obj) == {"status", "error"} and isinstance(obj["error"], str),
                "BAD_NATIVE_ERROR")
        return {"native_error": obj["error"]}
    require(set(obj) == {"status", "value"} and isinstance(obj["value"], str),
            "BAD_NATIVE_VALUE")
    return json.loads(obj["value"])


def signature(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)


def run(oracle_file: Path, alias_file: Path, ordinary_file: Path,
        cycle_file: Path, report_file: Path, candidate: str) -> dict:
    require(len(candidate) == 40 and all(c in "0123456789abcdef" for c in candidate),
            "BAD_CANDIDATE_SHA")
    oracle_bytes = oracle_file.read_bytes()
    oracle = json.loads(oracle_bytes)
    cases = oracle["cases"]
    require(len(cases) == 532, "ORACLE_COUNT_DRIFT")
    require(len(set(row["input"] for row in cases)) == 532, "ORACLE_DUPLICATE_INPUT")
    native = {}
    input_digests = {}
    native_digests = {}
    for suite, file in (("anchor", alias_file), ("ordinary", ordinary_file)):
        records = [json.loads(s) for s in file.read_text().splitlines() if s]
        expected_cases = [c for c in cases if c["suite"] == suite]
        require(len(records) == len(expected_cases), "INCOMPLETE_NATIVE_CASES")
        for original, record in zip(expected_cases, records):
            require(set(record) == {"input", "original_legacy", "original_indexed",
                                    "event_legacy", "event_indexed"},
                    "NATIVE_FIELDS_CHANGED")
            require(record["input"] == original["input"], "INPUT_IDENTITY_MISMATCH")
            require(record["input"] not in native, "DUPLICATE_NATIVE_INPUT")
            native[record["input"]] = record
        native_digests[suite] = hashlib.sha256(file.read_bytes()).hexdigest()
        input_digests[suite] = hashlib.sha256(
            "".join(json.dumps(c["input"], ensure_ascii=False) + "\n" for c in expected_cases).encode()
        ).hexdigest()
        require(input_digests[suite] == oracle["input_manifest_sha256"][suite],
                "ORACLE_INPUT_MANIFEST_MISMATCH")

    groups = defaultdict(lambda: {"cases": 0, "original_matched": 0,
                                  "event_matched": 0, "improved": 0, "regressed": 0})
    before_match = after_match = improvements = regressions = 0
    for entry in cases:
        record = native[entry["input"]]
        parsed = {k: parse_output(record[k]) for k in
                  ("original_legacy", "original_indexed", "event_legacy", "event_indexed")}
        require(signature(parsed["original_legacy"]) == signature(parsed["original_indexed"]),
                "ORIGINAL_NATIVE_PATHS_DISAGREE")
        require(signature(parsed["event_legacy"]) == signature(parsed["event_indexed"]),
                "EVENT_NATIVE_PATHS_DISAGREE")
        old = signature(parsed["original_legacy"]) == signature(entry["expected"])
        new = signature(parsed["event_legacy"]) == signature(entry["expected"])
        g = groups[f"{entry['suite']}.{entry['family']}"]
        g["cases"] += 1
        g["original_matched"] += int(old)
        g["event_matched"] += int(new)
        g["improved"] += int(new and not old)
        g["regressed"] += int(old and not new)
        before_match += old
        after_match += new
        improvements += new and not old
        regressions += old and not new

    cycle_rows = [json.loads(s) for s in cycle_file.read_text().splitlines() if s]
    expected_cycle_cases = {"&x [*x]", "&x {a: *x}", "[*x]",
                            "---\n&x 1\n---\n*x\n"}
    require({r["input"] for r in cycle_rows} == expected_cycle_cases,
            "CYCLIC_AND_REFUSAL_CONTROL_DRIFT")
    probes = []
    for record in cycle_rows:
        require(set(record) == {"input", "original_legacy", "original_indexed",
                                "event_legacy", "event_indexed"}, "BAD_CONTROL_FIELDS")
        statuses = {kind: record[kind]["status"] for kind in record if kind != "input"}
        require(len(set(statuses.values())) == 1, "INTERVENTION_CHANGED_PARSE_ACCEPTANCE")
        # JSON cannot demonstrate graph identity, so even an accepted cycle remains UNKNOWN.
        if record["input"] in ("&x [*x]", "&x {a: *x}"):
            require(statuses["original_legacy"] == "ok", "CYCLE_SYNTAX_REFUSED")
        else:
            require(statuses["original_legacy"] == "error", "BAD_ALIAS_ACCEPTED")
        probes.append({"input": record["input"], "parsing": statuses["original_legacy"],
                       "cycle_graph_identity": "UNKNOWN"})

    require(before_match == 427, "ORIGINAL_CONTROL_BASELINE_CHANGED")
    require(improvements > 0, "NO_CAUSAL_SEPARATION_OBSERVED")
    # A regression remains legitimate research evidence, but not a complete repair.
    state = "CANDIDATE_PARTIAL" if regressions or after_match < 532 else "FINITE_VALUE_REPAIR_CANDIDATE"
    result = {
        "schema": "mathgraph.l4yaml.event-time-compose-experiment.v1",
        "candidate_commit": candidate,
        "source_modified": False,
        "status": state,
        "cases": 532, "original_matched": before_match, "event_matched": after_match,
        "improved": improvements, "regressed": regressions,
        "mismatched_after": 532 - after_match,
        "families": dict(sorted(groups.items())),
        "cycle_and_refusal_controls": probes,
        "evidence_sha256": {"oracle": hashlib.sha256(oracle_bytes).hexdigest(),
                            **{f"native_{k}": v for k, v in native_digests.items()}},
        "warrant": "BOUNDED_EXPERIMENT_ONLY",
        "cycle_graph_identity": "UNKNOWN",
        "universal_semantics": "UNKNOWN",
        "release_authority": "NOT_AUTHORIZED",
    }
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in
                      ("status", "original_matched", "event_matched",
                       "improved", "regressed", "mismatched_after")}, sort_keys=True))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--oracle", type=Path, required=True)
    p.add_argument("--anchor", type=Path, required=True)
    p.add_argument("--ordinary", type=Path, required=True)
    p.add_argument("--cycle", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    args = p.parse_args()
    run(args.oracle, args.anchor, args.ordinary, args.cycle,
        args.report, args.candidate)
