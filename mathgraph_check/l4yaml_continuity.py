"""Bounded, source-pinned semantic continuity over an *externally qualified* native audit.

The proof of qualification is NOT the JSON receipt's assertion. The CLI executes
the independent strict source-native verifier and only projects its successful
receipt into warrant_resolution. Direct callers of project_qualified_receipt
are responsible for independent qualification before invoking this projection.
No result here is a MathGraph mathematical terminal certificate or release
authorization, and a semantic mismatch is not a universal YAML theorem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from .warrant_resolution import Claim, Receipt, Route, compare_snapshots, resolve_graph

UPSTREAM = "https://github.com/nasa-jpl/L4YAML"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
DEFECT_CASES = frozenset((
    "same-name-seq", "same-name-seq-both-aliases", "same-name-map",
    "same-name-map-both-aliases", "same-name-string",
))
CONTROL_CASES = frozenset((
    "sibling-rebind", "nested-distinct", "noalias-same-name", "single-anchor", "no-alias",
))
CYCLE_CASES = frozenset(("selfcycle-policy", "rebound-selfcycle-policy"))
REFUSAL_CASES = frozenset(("undefined-alias-control",))
RECEIPT_STATES = {
    0: "BOUNDED_FIX_OBSERVED",
    5: "BOUNDED_DEFECT_REPRODUCED",
}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
RECEIPT_KEYS = frozenset(("source", "source_binding", "native", "verifier", "oracle"))


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _sha(value: object) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def _git_sha(value: object) -> bool:
    return isinstance(value, str) and bool(HEX40.fullmatch(value))


def _validate_qualification(record: dict, expected_head: str) -> tuple[int, dict]:
    """Guard projection shape; not a replacement for native verifier execution."""
    _require(isinstance(record, dict), "QUALIFICATION_NOT_OBJECT")
    source = record.get("source")
    counts = record.get("counts")
    hashes = record.get("artifact_sha256")
    _require(all(isinstance(x, dict) for x in (source, counts, hashes)), "INCOMPLETE_QUALIFICATION")
    _require(record.get("errors") == [], "VERIFIER_REPORTED_ERRORS")
    _require(source.get("repository") == UPSTREAM, "UNTRUSTED_SOURCE_REPOSITORY")
    _require(source.get("commit") == expected_head, "RECEIPT_SOURCE_MISMATCH")
    _require(source.get("tracked_checkout_clean") is True, "DIRTY_SOURCE_CHECKOUT")
    _require(source.get("toolchain") == TOOLCHAIN, "TOOLCHAIN_CHANGED")
    _require("4.35.0" in str(source.get("lean_version", "")), "LEAN_RUNTIME_CHANGED")
    files = source.get("source_files")
    _require(isinstance(files, dict) and "L4YAML/Spec/Types.lean" in files,
             "SOURCE_FILE_IDENTITY_MISSING")
    for data in files.values():
        _require(isinstance(data, dict) and _sha(data.get("sha256"))
                 and _git_sha(data.get("git_blob")), "INVALID_SOURCE_BLOB_IDENTITY")
    _require(counts.get("native_rows") == 13 and counts.get("acyclic_cases") == 10,
             "INCOMPLETE_NATIVE_SUITE")
    _require(counts.get("acyclic_controls_passed_both_pipelines") == 5,
             "NATIVE_CONTROLS_NOT_QUALIFIED")
    _require(counts.get("cycle_policy_observations") == 2
             and counts.get("undefined_alias_controls_refused") == 1,
             "EXCLUSIONS_OR_REFUSAL_CHANGED")
    defects = counts.get("defects_reproduced_both_pipelines")
    _require(type(defects) is int and 0 <= defects <= 5, "INVALID_DEFECT_COUNT")
    wanted = RECEIPT_STATES.get(defects, "BOUNDED_PARTIAL_DEFECT")
    _require(record.get("status") == wanted, "INCONSISTENT_VERIFICATION_RESULT")
    _require(set(record.get("defect_cases", [])) <= DEFECT_CASES
             and len(record.get("defect_cases", [])) == defects
             and len(set(record["defect_cases"])) == defects,
             "INVALID_DEFECT_CASES")
    _require(set(record.get("control_cases", [])) == CONTROL_CASES
             and len(record.get("control_cases", [])) == 5,
             "INVALID_CONTROL_CASES")
    cases = record.get("cases")
    _require(isinstance(cases, list) and len(cases) == 13, "INCOMPLETE_CASE_RECEIPTS")
    by_name = {r.get("case"): r for r in cases if isinstance(r, dict)}
    _require(len(by_name) == 13
             and set(by_name) == DEFECT_CASES | CONTROL_CASES | CYCLE_CASES | REFUSAL_CASES,
             "INVALID_CASE_MEMBERSHIP")
    for name in DEFECT_CASES | CONTROL_CASES:
        case = by_name[name]
        _require(case.get("category") == ("defect" if name in DEFECT_CASES else "control")
                 and type(case.get("agrees")) is bool, "INVALID_ACYCLIC_CASE")
        _require(case["agrees"] == (name not in record["defect_cases"]),
                 "DEFECT_CASE_CLASSIFICATION_MISMATCH")
    for name in CYCLE_CASES:
        _require(by_name[name].get("category") == "cycle_policy", "CYCLE_BOUNDARY_CHANGED")
    for name in REFUSAL_CASES:
        _require(by_name[name].get("category") == "refusal", "REFUSAL_BOUNDARY_CHANGED")
    _require(all(_sha(hashes.get(x)) for x in ("Probe.lean", "analyze.py", "oracle_results.json")),
             "INCOMPLETE_VERIFIER_ARTIFACT_DIGESTS")
    natives = [k for k in hashes if k.endswith(".jsonl")]
    stderrs = [k for k in hashes if k.endswith(".stderr") or k == "native_stderr.log"]
    _require(len(natives) == 1 and len(stderrs) == 1
             and _sha(hashes[natives[0]]) and hashes[stderrs[0]] == EMPTY_SHA256,
             "INVALID_NATIVE_PROVENANCE")
    return defects, {"raw_native_sha256": hashes[natives[0]],
                     "oracle_sha256": hashes["oracle_results.json"],
                     "probe_sha256": hashes["Probe.lean"],
                     "verifier_sha256": hashes["analyze.py"],
                     "empty_stderr_sha256": hashes[stderrs[0]]}


def project_qualified_receipt(
    record: dict, *, expected_head: str, current_head: str,
    withdrawn: frozenset[str] = frozenset(),
) -> dict:
    """Project an already independently validated native receipt; no trust amplification."""
    _require(_git_sha(expected_head) and _git_sha(current_head), "NON_IMMUTABLE_SOURCE_IDENTITY")
    _require(withdrawn <= {"source", "native", "verifier", "oracle"},
             "UNKNOWN_WITHDRAWAL_TARGET")
    defects, hashes = _validate_qualification(record, expected_head)
    documentary_scope = f"nasa-jpl/L4YAML@{expected_head}:source"
    formal_scope = f"nasa-jpl/L4YAML@{expected_head}:native-13-case"
    claims = [
        Claim("source_identity", "documentary", documentary_scope),
        Claim("native_controls", "formal", formal_scope),
        Claim("bounded_nonconformance", "formal", formal_scope),
        Claim("bounded_repair", "formal", formal_scope),
    ]
    receipts = [
        Receipt("source", "documentary", documentary_scope),
        Receipt("source_binding", "formal", formal_scope),
        *[Receipt(x, "formal", formal_scope) for x in ("native", "verifier", "oracle")],
    ]
    routes = [
        Route("source_identity", ("source",)),
        Route("native_controls", ("source_binding", "native", "verifier")),
        Route("bounded_nonconformance" if defects else "bounded_repair",
              ("source_binding", "native", "verifier", "oracle")),
    ]
    active = resolve_graph(claims, routes, receipts)
    effective = set(withdrawn)
    if "source" in effective:
        effective.add("source_binding")
    if current_head != expected_head:
        effective.update(RECEIPT_KEYS)
    closed = resolve_graph(claims, routes, receipts, withdrawn=frozenset(effective))
    evidence_ready = closed.states["source_identity"] == "SOURCE_DOCUMENTED"
    target = "bounded_nonconformance" if defects else "bounded_repair"
    semantics_ready = closed.states[target] == "WARRANTED_BOUNDED"
    status = ("BOUNDED_NONCONFORMANCE_OBSERVED" if defects else "BOUNDED_REPAIR_OBSERVED") \
        if evidence_ready and semantics_ready else "UNKNOWN"
    return {
        "schema": "mathgraph.check.l4yaml.semantic-continuity.v1",
        "status": status,
        "source": {
            "repository": UPSTREAM, "commit": expected_head, "current_head": current_head,
            "toolchain": record["source"]["toolchain"],
            "source_files": record["source"]["source_files"],
        },
        "scope": "13 source-native probes: ten acyclic cases, two cycle observations, one undefined alias refusal",
        "claims": dict(closed.states),
        "changes": compare_snapshots(active.states, closed.states),
        "evidence": hashes,
        "counts": record["counts"],
        "case_residuals": record["defect_cases"],
        "withdrawn": sorted(withdrawn),
        "review_state": "EVIDENCE_AVAILABLE_FOR_HUMAN_REVIEW" if status != "UNKNOWN" else "UNKNOWN",
        "decision_authority": "NOT_AUTHORIZED",
        "mathematical_terminal_form": None,
        "no_automatic_merging_or_deployment": True,
        "qualifier": "Strict external native verifier executed before projection; this projection alone cannot authenticate receipts",
    }


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native", "oracle", "stderr", "checkout", "lean", "verifier-script",
                 "receipt-out", "report-out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--current-head", help="Defaults to expected-head; override to model staleness")
    parser.add_argument("--withdraw", action="append", default=[])
    args = parser.parse_args(argv)
    _require(_git_sha(args.expected_head), "NON_IMMUTABLE_SOURCE_IDENTITY")
    # Native verifier independently authenticates Git source bytes, toolchain,
    # complete raw output, independent oracle and strict negative controls.
    command = [sys.executable, str(args.verifier_script), "--native", str(args.native),
               "--oracle", str(args.oracle), "--stderr", str(args.stderr),
               "--checkout", str(args.checkout), "--lean", str(args.lean),
               "--expected-head", args.expected_head, "--output", str(args.receipt_out)]
    run = subprocess.run(command, check=False)
    if run.returncode != 0:
        fallback = {
            "schema": "mathgraph.check.l4yaml.semantic-continuity.v1",
            "status": "UNKNOWN", "decision_authority": "NOT_AUTHORIZED",
            "reason": "EXTERNAL_NATIVE_QUALIFIER_DID_NOT_PASS",
            "source": {"expected_head": args.expected_head},
        }
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(fallback, indent=2) + "\n")
        return 1
    record = json.loads(args.receipt_out.read_text())
    result = project_qualified_receipt(
        record, expected_head=args.expected_head,
        current_head=args.current_head or args.expected_head,
        withdrawn=frozenset(args.withdraw),
    )
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "claims": result["claims"],
                      "report": str(args.report_out)}))
    return 0 if result["status"] != "UNKNOWN" else 2


if __name__ == "__main__":
    raise SystemExit(cli())
