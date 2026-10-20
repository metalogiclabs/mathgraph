#!/usr/bin/env python3
"""Independent-of-Strata observation adapter over MathGraph's existing resolver.

Pinned source/tool outputs MUST be checked before caller admits documentary receipts.
Do not interpret MathGraph closure as independently checking CVC5 or Lean proofs.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import sys

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, compare_snapshots, resolve_graph

ROOT = pathlib.Path(__file__).resolve().parent
E = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "evidence"
PROTOCOL = json.loads((ROOT / "protocol.json").read_text())
BASE = PROTOCOL["base_sha"]
FIX = PROTOCOL["repair_sha"]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_artifacts() -> dict:
    manifest = json.loads((E / "result_manifest.json").read_text())
    if manifest.get("base_revision") != BASE or manifest.get("repair_revision") != FIX:
        raise AssertionError("UPSTREAM_PIN_MISMATCH")
    for name, sha in manifest["files_sha256"].items():
        target = (ROOT / name) if name in ("BugBefore.lean", "OracleClaimFalse.smt2", "OracleClaimTrue.smt2", "protocol.json") else (E / name)
        if not target.is_file() or digest(target) != sha:
            raise AssertionError(f"SOURCE_OR_EVIDENCE_BYTES_MISMATCH:{name}")
    for role in ("base", "repair"):
        if manifest.get(f"{role}_toolchain") != PROTOCOL["lean_toolchain"]:
            raise AssertionError(f"TOOLCHAIN_MISMATCH:{role}")
    return manifest


def assert_observed_boundaries() -> dict:
    base = (E / "base_bug_lean.txt").read_text()
    control = (E / "base_control_lean.txt").read_text()
    repair = (E / "repair_bad_expected_rejection.txt").read_text()
    good = (E / "repair_good_lean.txt").read_text()
    proof = re.search(r"'Strata\.oops' depends on axioms:\s*\[(.*?)\]", base, flags=re.S)
    if not proof:
        raise AssertionError("NO_NAMED_BASE_FALSE_PROOF_DEPENDENCY_REPORT")
    axioms = [x.strip() for x in proof.group(1).split(",")]
    if any("sorryAx" in x for x in axioms):
        raise AssertionError("BASE_FALSE_PROOF_USES_SORRY")
    if not any("_genSMTVCs_tcbBridge" in x for x in axioms):
        raise AssertionError("NO_DECLARED_BRIDGE_IN_FALSE_THEOREM")
    if not re.search(r"Strata\.oops\s*:\s*False", base):
        raise AssertionError("NO_CHECKED_FALSE_DECLARATION")
    if "_genSMTVCs_tcbBridge" not in control or "sorryAx" in control:
        raise AssertionError("UNRELATED_CONTROL_INCOMPLETE")
    # The repair must fail on the actual discrepancy, not an absent module or syntax error.
    if "error" not in repair.lower() or "smtUDiv" not in repair:
        raise AssertionError("REPAIR_DID_NOT_REFUSE_BUG_WITH_CORRECT_SMT_SEMANTICS")
    if "error:" in good or "error(lean" in good or "sorryAx" in good:
        raise AssertionError("REPAIR_GOOD_TEST_NOT_VALID")
    if (E / "oracle_bad.txt").read_text().strip() != "unsat":
        raise AssertionError("SMT_ORACLE_FALSE_CASE_NOT_UNSAT")
    if (E / "oracle_good.txt").read_text().strip() != "sat":
        raise AssertionError("SMT_ORACLE_CORRECT_CASE_NOT_SAT")
    return {"false_theorem_checked_under_bridge": True, "false_theorem_axioms": axioms,
            "control_valid": True, "fixed_bad_probe_refused": True,
            "fixed_positive_native_test_valid": True,
            "smt_oracle_invalid_claim": "unsat", "smt_oracle_valid_claim": "sat"}


SCOPE = "Strata@0bbe12d_to_4016549:QF_BV:8bits:closed-case"
NAMES = (
    "base.false_theorem_admitted_by_bridge",
    "base.declared_bridge_axiom_dependency",
    "independent.smt_div_zero_semantics",
    "repair.corrected_vc_provable",
    "repair.false_vc_rejected",
    "unrelated.baseline_min_control",
    "cross_representation_semantic_mismatch",
    "universal_strata_soundness",
)
CLAIMS = tuple(Claim(n, "documentary", SCOPE) for n in NAMES)
RECEIPTS = tuple(Receipt(n, "documentary", SCOPE) for n in (
    "base_lean", "oracle_script_authority", "repair_positive", "repair_reject",
    "control_lean", "comparison_calculation",
))
ROUTES = (
    Route(NAMES[0], ("base_lean",)),
    Route(NAMES[1], ("base_lean",)),
    Route(NAMES[2], ("oracle_script_authority",)),
    Route(NAMES[3], ("repair_positive",)),
    Route(NAMES[4], ("repair_reject",)),
    Route(NAMES[5], ("control_lean",)),
    Route(NAMES[6], ("comparison_calculation",), (NAMES[0], NAMES[2])),
    # No route can qualify a universal claim for an exposed finite counterexample.
)

FILES = {
    "base_lean": E / "base_bug_lean.txt",
    "oracle_script_authority": ROOT / "OracleClaimFalse.smt2",
    "repair_positive": E / "repair_good_lean.txt",
    "repair_reject": E / "repair_bad_expected_rejection.txt",
    "control_lean": E / "base_control_lean.txt",
    "comparison_calculation": E / "oracle_good.txt",
}


def physical_snapshot(locked_hashes: dict[str, str]):
    missing = set()
    for receipt, path in FILES.items():
        if not path.is_file():
            missing.add(receipt)
            continue
        key = path.relative_to(E).as_posix() if path.is_relative_to(E) else path.relative_to(ROOT).as_posix()
        if digest(path) != locked_hashes[key]:
            raise AssertionError(f"MODIFIED_AUTHORITY_REJECTED:{key}")
    return dict(resolve_graph(CLAIMS, ROUTES, RECEIPTS, withdrawn=frozenset(missing)).states)


def replay_withdrawal(manifest: dict) -> dict:
    locked = manifest["files_sha256"]
    before = physical_snapshot(locked)
    assert before[NAMES[-1]] == "UNKNOWN"  # no universal promotion
    assert all(before[n] == "SOURCE_DOCUMENTED" for n in NAMES[:-1])
    expected = {
        "oracle_script_authority": {NAMES[2], NAMES[6]},
        "base_lean": {NAMES[0], NAMES[1], NAMES[6]},
        "repair_positive": {NAMES[3]},
        "repair_reject": {NAMES[4]},
        "control_lean": {NAMES[5]},
    }
    results = {}
    for receipt, lost_expected in expected.items():
        source = FILES[receipt]
        temp = source.with_name(source.name + ".physically_withdrawn")
        if temp.exists():
            raise AssertionError("TEMPORARY_WITHDRAWAL_COLLISION")
        before_hash = digest(source)
        source.rename(temp)
        try:
            after = physical_snapshot(locked)
            lost = {name for name in before if before[name] != "UNKNOWN" and after[name] == "UNKNOWN"}
            if lost != lost_expected:
                raise AssertionError(f"NONLOCAL_WITHDRAWAL:{receipt}:{sorted(lost)} != {sorted(lost_expected)}")
            if after[NAMES[-1]] != "UNKNOWN":
                raise AssertionError("UNIVERSAL_CLAIM_FALSIFIED_WARRANTED")
            results[receipt] = {"physically_moved": True, "lost_exactly": sorted(lost),
                                "differential": compare_snapshots(before, after)}
        finally:
            temp.rename(source)
            if digest(source) != before_hash:
                raise AssertionError("FAILED_TO_RESTORE_ORIGINAL_SOURCE_BYTES")
        if physical_snapshot(locked) != before:
            raise AssertionError("FULL_CLOSURE_NOT_RESTORED")
        results[receipt]["restored_exact_original_bytes"] = True
    # Malicious tampering must be refused rather than accepted as new semantics.
    altered = FILES["oracle_script_authority"]
    raw = altered.read_bytes()
    try:
        altered.write_bytes(raw + b"\n; corruption control\n")
        try:
            physical_snapshot(locked)
        except AssertionError as exc:
            if "MODIFIED_AUTHORITY_REJECTED" not in str(exc):
                raise
        else:
            raise AssertionError("CORRUPTED_AUTHORITY_WAS_ACCEPTED")
    finally:
        altered.write_bytes(raw)
    if physical_snapshot(locked) != before:
        raise AssertionError("CORRUPTION_RESTORATION_CHANGED_WARRANTS")
    return {"baseline": before, "physical_cases": results,
            "tamper_rejected": True, "restoration_exact": True}


def main():
    manifest = assert_frozen_artifacts()
    observed = assert_observed_boundaries()
    withdrawal = replay_withdrawal(manifest)
    final = {
        "schema": "mathgraph.strata-bridge-retrospective-result.v1",
        "status": "WARRANTED_BOUNDED_EXPOSED_SOURCE_REPLAY",
        "scientific": "REJECTED_BOUNDED_BASE_SEMANTIC_CORRESPONDENCE",
        "method_transfer": "CANDIDATE_CROSS_DOMAIN_REPLAY_NOT_PROSPECTIVE",
        "pin": {"base": BASE, "repair": FIX, "toolchain": PROTOCOL["lean_toolchain"]},
        "observations": observed,
        "withdrawal": withdrawal,
        "limitations": [
            "Earlier Strata issue #1488 and PR #1490 are public and source was exposed before this frozen protocol.",
            "The original False theorem is kernel-checked relative to its per-theorem trusted bridge axiom, not a failure of Lean kernel soundness.",
            "This tests one bit-vector division-by-zero case, one datatype refusal, and one unrelated control, not all Strata semantics.",
            "PR #1490 still has a per-theorem bridge axiom; repair is not an axiom-free proof of general correspondence.",
            "Physical withdrawal changes a local oracle-script file and observation-to-receipt admission, not upstream publisher status.",
            "MathGraph's unchanged resolver propagates externally admitted documentary receipts; it does not verify GitHub, CVC5, SMT-LIB or Lean independently.",
        ],
        "artifact_manifest_sha256": digest(E / "result_manifest.json"),
    }
    (E / "RESULT.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": final["status"], "base_false_theorem_axioms": observed["false_theorem_axioms"],
                      "withdrawal_lost": {k: v["lost_exactly"] for k,v in withdrawal["physical_cases"].items()},
                      "tamper_rejected": True, "restoration_exact": True}, indent=2))


if __name__ == "__main__":
    main()