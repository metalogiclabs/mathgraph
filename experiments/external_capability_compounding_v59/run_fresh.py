#!/usr/bin/env python3
"""V59 prospective fresh test of compiled finite-model neighborhoods.

Frozen after successful opened-data calibration run 34960757212 and before any
row >= 2756 is semantically inspected.

Phase A: Wrong Book 3000 rows 2756:2820 (64 untouched problems)
Phase B: Wrong Book 3500 rows 2756:2820 (64 untouched problems)

Initial executable memory is the exact 18-capability V58 final archive.
The calibrated developmental operator is fixed:
  top 3 retained parents by source-law violation,
  same carrier,
  Hamming radius <= 4,
  300 ms Z3 per parent,
  total neighborhood solver budget <= 900 ms.

Terminal truth boundary remains one-sided: only explicit finite countermodels
independently exhaustively checked by MathGraph become FALSE. No TRUE result is
promoted in V59.

The decisive test is whether Phase-A experience changes Phase-B capability:
before any B learning, compare the original V58 archive against the frozen
post-A archive on the same untouched B tasks, under the same neighborhood
budget. Then ablate exact A-acquired ancestors.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_CAL_PATH = ROOT / "experiments" / "external_capability_compounding_v59" / "calibrate_neighborhood.py"
_CAL_SPEC = importlib.util.spec_from_file_location("v59_cal", _CAL_PATH)
if _CAL_SPEC is None or _CAL_SPEC.loader is None:
    raise RuntimeError("cannot load calibrated V59 operator")
_CAL = importlib.util.module_from_spec(_CAL_SPEC)
sys.modules[_CAL_SPEC.name] = _CAL
_CAL_SPEC.loader.exec_module(_CAL)

_V58_PATH = ROOT / "experiments" / "external_capability_compounding_v58" / "run.py"
_V58_SPEC = importlib.util.spec_from_file_location("v59_v58_runtime", _V58_PATH)
if _V58_SPEC is None or _V58_SPEC.loader is None:
    raise RuntimeError("cannot load V58 cvc5 constructor")
_V58 = importlib.util.module_from_spec(_V58_SPEC)
sys.modules[_V58_SPEC.name] = _V58
_V58_SPEC.loader.exec_module(_V58)

FRESH_START = 2756
FRESH_COUNT = 64
COLD_TIMEOUT_MS = 900
EXPECTED_SEED_FILE_SHA256 = "241f6223899b6decf77767d0ec182920417b65217846f8b68e24d7a13b2bd535"
EXPECTED_3000_SHA256 = _V58.EXPECTED_3000_SHA256
EXPECTED_3500_SHA256 = _V58.EXPECTED_3500_SHA256
CALIBRATION_RUN = 34960757212
CALIBRATION_COMMIT = "27bb54d7ada5db459a210e19af2cf03da492a3bc"


def table_cid(table) -> str:
    table = _CAL.table_tuple(table)
    return hashlib.sha256(
        json.dumps([list(r) for r in table], separators=(",", ":")).encode()
    ).hexdigest()


def load_fresh(path: Path, expected_sha: str):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch: {digest}")
    lines = data.decode("utf-8").splitlines()
    chosen = lines[FRESH_START:FRESH_START + FRESH_COUNT]
    if len(chosen) != FRESH_COUNT:
        raise RuntimeError(f"expected {FRESH_COUNT} fresh rows, got {len(chosen)}")
    return [json.loads(line) for line in chosen], digest


def stream_digest(rows):
    raw = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows)
    return hashlib.sha256(raw.encode()).hexdigest()


def clone_archive(archive):
    return json.loads(json.dumps(archive))


def archive_digest(archive):
    raw = json.dumps(archive, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def install(archive, table, problem_id, phase, route, parent_cid=None):
    cid = table_cid(table)
    for cap in archive:
        if cap["cid"] == cid:
            return cap, False
    cap = {
        "cid": cid,
        "table": [list(row) for row in _CAL.table_tuple(table)],
        "acquired_on": problem_id,
        "acquired_phase": phase,
        "route": route,
        "parent_cid": parent_cid,
        "acquisition_index": len(archive),
        "reuse_hits": 0,
    }
    archive.append(cap)
    return cap, True


def rank_parents(problem, archive):
    scored = []
    for parent in archive:
        bad, total = _CAL.source_violation_count(problem, parent["table"])
        scored.append((
            bad / max(1, total),
            bad,
            len(parent["table"]),
            -int(parent.get("reuse_hits", 0)),
            parent["cid"],
            parent,
        ))
    scored.sort(key=lambda x: x[:5])
    return scored[:_CAL.TOP_PARENTS]


def warm_route(problem, archive, serial, install_children=False, phase="PROBE"):
    for parent in sorted(
        archive,
        key=lambda p: (-int(p.get("reuse_hits", 0)), int(p.get("acquisition_index", 0)), p["cid"]),
    ):
        if _CAL.solves(problem, parent["table"]):
            if install_children:
                parent["reuse_hits"] = int(parent.get("reuse_hits", 0)) + 1
            return {
                "terminal": "FALSE",
                "route": "DIRECT_REUSE",
                "cid": parent["cid"],
                "parent_cid": parent.get("parent_cid"),
                "parent_phase": parent.get("acquired_phase"),
                "repair_solver_ms": 0,
                "repair_attempts": 0,
                "installed": False,
                "n": len(parent["table"]),
            }, serial

    attempts = []
    for ratio, bad, n, _neg_hits, _cid, parent in rank_parents(problem, archive):
        serial += 1
        repaired = _CAL.repair(problem, parent, serial)
        attempts.append({
            "parent_cid": parent["cid"],
            "parent_phase": parent.get("acquired_phase"),
            "source_violation_ratio": ratio,
            "source_violations": bad,
            "status": repaired["status"],
            "elapsed_ms": repaired["elapsed_ms"],
        })
        if repaired["status"] != "VERIFIED_CHILD":
            continue
        child = repaired["child"]
        if not _CAL.solves(problem, child):
            raise RuntimeError("independent verifier lost repaired child")
        cap = {
            "cid": repaired["child_cid"],
            "table": child,
            "acquired_on": problem["id"],
            "acquired_phase": phase,
            "route": "NEIGHBORHOOD_CHILD",
            "parent_cid": parent["cid"],
            "acquisition_index": len(archive),
            "reuse_hits": 1,
        }
        installed = False
        if install_children:
            existing = next((x for x in archive if x["cid"] == cap["cid"]), None)
            if existing is None:
                archive.append(cap)
                installed = True
            else:
                cap = existing
                cap["reuse_hits"] = int(cap.get("reuse_hits", 0)) + 1
        return {
            "terminal": "FALSE",
            "route": "NEIGHBORHOOD_CHILD",
            "cid": cap["cid"],
            "parent_cid": parent["cid"],
            "parent_phase": parent.get("acquired_phase"),
            "repair_solver_ms": sum(a["elapsed_ms"] for a in attempts),
            "repair_attempts": len(attempts),
            "distance": repaired["distance"],
            "installed": installed,
            "n": len(child),
            "attempts": attempts,
        }, serial

    return {
        "terminal": "UNKNOWN",
        "route": "UNKNOWN",
        "cid": None,
        "parent_cid": None,
        "parent_phase": None,
        "repair_solver_ms": sum(a["elapsed_ms"] for a in attempts),
        "repair_attempts": len(attempts),
        "installed": False,
        "attempts": attempts,
    }, serial


def cold(problem):
    result = _V58.cvc5_construct(problem, timeout_ms=COLD_TIMEOUT_MS)
    if result.status == "VERIFIED_FALSE":
        if result.table is None or not _CAL.solves(problem, result.table):
            raise RuntimeError("cold cvc5 model failed independent verification")
        return {
            "terminal": "FALSE",
            "route": "CVC5_COLD",
            "status": result.status,
            "elapsed_ms": result.elapsed_ms,
            "table": [list(r) for r in result.table],
            "cid": table_cid(result.table),
            "n": result.n,
        }
    return {
        "terminal": "UNKNOWN",
        "route": "PROOF_CANDIDATE" if result.status == "PROOF_CANDIDATE" else "UNKNOWN",
        "status": result.status,
        "elapsed_ms": result.elapsed_ms,
        "table": None,
        "cid": None,
        "n": result.n,
    }


def continuous(problem, archive, serial, phase):
    warm, serial = warm_route(problem, archive, serial, install_children=True, phase=phase)
    if warm["terminal"] == "FALSE":
        warm["cvc5_invocations"] = 0
        return warm, serial
    fallback = _V58.cvc5_construct(problem, timeout_ms=COLD_TIMEOUT_MS)
    if fallback.status == "VERIFIED_FALSE":
        if fallback.table is None or not _CAL.solves(problem, fallback.table):
            raise RuntimeError("fallback model failed independent verification")
        cap, installed = install(
            archive,
            fallback.table,
            problem["id"],
            phase,
            "CVC5_ACQUIRE",
            None,
        )
        cap["reuse_hits"] = int(cap.get("reuse_hits", 0)) + 1
        return {
            "terminal": "FALSE",
            "route": "CVC5_ACQUIRE",
            "cid": cap["cid"],
            "parent_cid": None,
            "parent_phase": None,
            "repair_solver_ms": warm["repair_solver_ms"],
            "repair_attempts": warm["repair_attempts"],
            "installed": installed,
            "cvc5_invocations": 1,
            "cvc5_elapsed_ms": fallback.elapsed_ms,
            "n": fallback.n,
        }, serial
    return {
        "terminal": "UNKNOWN",
        "route": "PROOF_CANDIDATE" if fallback.status == "PROOF_CANDIDATE" else "UNKNOWN",
        "cid": None,
        "parent_cid": None,
        "parent_phase": None,
        "repair_solver_ms": warm["repair_solver_ms"],
        "repair_attempts": warm["repair_attempts"],
        "installed": False,
        "cvc5_invocations": 1,
        "cvc5_elapsed_ms": fallback.elapsed_ms,
        "n": fallback.n,
    }, serial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wrong-book-3000", required=True)
    ap.add_argument("--wrong-book-3500", required=True)
    ap.add_argument("--seed-archive", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    seed_path = Path(args.seed_archive)
    seed_bytes = seed_path.read_bytes()
    seed_file_sha = hashlib.sha256(seed_bytes).hexdigest()
    if seed_file_sha != EXPECTED_SEED_FILE_SHA256:
        raise RuntimeError(f"V58 seed file hash mismatch: {seed_file_sha}")
    seed_doc = json.loads(seed_bytes)
    seed_archive = seed_doc["capabilities"]
    if len(seed_archive) != 18:
        raise RuntimeError("V58 seed capability count changed")

    phase_a, sha3000 = load_fresh(Path(args.wrong_book_3000), EXPECTED_3000_SHA256)
    phase_b, sha3500 = load_fresh(Path(args.wrong_book_3500), EXPECTED_3500_SHA256)
    overlap = {r["id"] for r in phase_a} & {r["id"] for r in phase_b}
    if overlap:
        raise RuntimeError(f"fresh stream overlap: {sorted(overlap)[:3]}")

    serial = 0
    archive = clone_archive(seed_archive)
    phase_a_rows = []
    for index, problem in enumerate(phase_a, 1):
        c = cold(problem)
        w, serial = continuous(problem, archive, serial, "V59_FRESH_A")
        phase_a_rows.append({"problem_id": problem["id"], "cold": c, "continuous": w})
        print(json.dumps({
            "phase": "A", "index": index, "id": problem["id"],
            "cold": c["route"], "continuous": w["route"],
            "archive_size": len(archive),
        }, sort_keys=True), flush=True)

    post_a_archive = clone_archive(archive)
    post_a_digest = archive_digest(post_a_archive)
    a_new = [c for c in post_a_archive if c.get("acquired_phase") == "V59_FRESH_A"]

    # Frozen cross-extension transfer probe: both archives see every B task before B learning.
    transfer_rows = []
    essential_examples = []
    seed_transfer_count = 0
    post_a_transfer_count = 0
    post_a_strict_uplift = 0
    post_a_cold_miss_uplift = 0

    for index, problem in enumerate(phase_b, 1):
        seed_probe, serial = warm_route(problem, clone_archive(seed_archive), serial, False, "SEED_PROBE")
        posta_probe, serial = warm_route(problem, clone_archive(post_a_archive), serial, False, "POST_A_PROBE")
        c = cold(problem)
        if seed_probe["terminal"] == "FALSE":
            seed_transfer_count += 1
        if posta_probe["terminal"] == "FALSE":
            post_a_transfer_count += 1

        strict = seed_probe["terminal"] != "FALSE" and posta_probe["terminal"] == "FALSE"
        cold_miss = strict and c["terminal"] != "FALSE"
        if strict:
            post_a_strict_uplift += 1
        if cold_miss:
            post_a_cold_miss_uplift += 1

        essential = False
        ablated = None
        parent_cid = posta_probe.get("parent_cid")
        solved_cid = posta_probe.get("cid")
        implicated = parent_cid or solved_cid
        if strict and implicated:
            implicated_cap = next((x for x in post_a_archive if x["cid"] == implicated), None)
            if implicated_cap is not None and implicated_cap.get("acquired_phase") == "V59_FRESH_A":
                ablated_archive = [x for x in post_a_archive if x["cid"] != implicated]
                ablated, serial = warm_route(problem, clone_archive(ablated_archive), serial, False, "ABLATION")
                essential = ablated["terminal"] != "FALSE"
                if essential and len(essential_examples) < 12:
                    essential_examples.append({
                        "problem_id": problem["id"],
                        "implicated_cid": implicated,
                        "post_a_route": posta_probe["route"],
                        "post_a_parent_cid": parent_cid,
                        "seed_route": seed_probe["route"],
                        "cold_route": c["route"],
                        "delete_result": ablated["route"],
                        "restore_result": posta_probe["route"],
                    })

        transfer_rows.append({
            "problem_id": problem["id"],
            "seed": seed_probe,
            "post_a": posta_probe,
            "cold": {k: v for k, v in c.items() if k != "table"},
            "strict_post_a_uplift": strict,
            "strict_post_a_cold_miss_uplift": cold_miss,
            "a_ancestor_essential": essential,
        })
        print(json.dumps({
            "phase": "B_TRANSFER", "index": index, "id": problem["id"],
            "seed": seed_probe["route"], "post_a": posta_probe["route"],
            "cold": c["route"], "strict_uplift": strict, "essential": essential,
        }, sort_keys=True), flush=True)

    # Now, after the frozen B transfer probe, let the same developer continue through B.
    archive = clone_archive(post_a_archive)
    phase_b_rows = []
    for index, problem in enumerate(phase_b, 1):
        c = cold(problem)
        w, serial = continuous(problem, archive, serial, "V59_FRESH_B")
        phase_b_rows.append({"problem_id": problem["id"], "cold": c, "continuous": w})
        print(json.dumps({
            "phase": "B_CONTINUOUS", "index": index, "id": problem["id"],
            "cold": c["route"], "continuous": w["route"],
            "archive_size": len(archive),
        }, sort_keys=True), flush=True)

    all_rows = phase_a_rows + phase_b_rows
    cold_false = sum(x["cold"]["terminal"] == "FALSE" for x in all_rows)
    continuous_false = sum(x["continuous"]["terminal"] == "FALSE" for x in all_rows)
    continuous_cvc5 = sum(int(x["continuous"].get("cvc5_invocations", 0)) for x in all_rows)
    child_rows = [
        x for x in all_rows
        if x["continuous"]["route"] == "NEIGHBORHOOD_CHILD"
    ]
    child_cold_misses = [
        x for x in child_rows
        if x["cold"]["terminal"] != "FALSE"
    ]

    checks = {
        "calibrated_parameters_unchanged": (
            _CAL.TOP_PARENTS == 3
            and _CAL.MAX_DISTANCE == 4
            and _CAL.REPAIR_TIMEOUT_MS == 300
            and _CAL.COLD_COMPARE_TIMEOUT_MS == 900
            and COLD_TIMEOUT_MS == 900
        ),
        "exact_v58_executable_seed": (
            seed_file_sha == EXPECTED_SEED_FILE_SHA256 and len(seed_archive) == 18
        ),
        "fresh_streams_disjoint_and_post_v58": (
            FRESH_START == 2756 and len(phase_a) == 64 and len(phase_b) == 64 and not overlap
        ),
        "phase_a_changes_machine": len(a_new) > 0,
        "compiled_child_generated_on_fresh_problem": len(child_rows) > 0,
        "fresh_compiled_child_beats_same_budget_cold": len(child_cold_misses) > 0,
        "phase_a_improves_frozen_phase_b_transfer": post_a_transfer_count > seed_transfer_count,
        "strict_phase_a_to_b_uplift_exists": post_a_strict_uplift > 0,
        "strict_phase_a_to_b_uplift_beats_cold": post_a_cold_miss_uplift > 0,
        "individual_phase_a_ancestor_is_causal": len(essential_examples) > 0,
        "continuous_uses_fewer_cvc5_calls": continuous_cvc5 < len(all_rows),
        "continuous_verified_false_not_worse": continuous_false >= cold_false,
        "wrong_terminal_promotions_zero": True,
    }

    result = {
        "schema": "mathgraph.external-capability-compounding.v59",
        "classification": "PROSPECTIVE_EXTERNAL_FRESH_CAUSAL",
        "calibration": {
            "run": CALIBRATION_RUN,
            "commit": CALIBRATION_COMMIT,
            "top_parents": _CAL.TOP_PARENTS,
            "max_distance": _CAL.MAX_DISTANCE,
            "repair_timeout_ms_per_parent": _CAL.REPAIR_TIMEOUT_MS,
            "total_repair_solver_budget_ms": _CAL.COLD_COMPARE_TIMEOUT_MS,
        },
        "external": {
            "repository": "YanbiaoLab/equational-challenges",
            "commit": _V58.EXTERNAL_COMMIT,
            "dataset_3000_sha256": sha3000,
            "dataset_3500_sha256": sha3500,
            "fresh_start": FRESH_START,
            "fresh_count_each": FRESH_COUNT,
            "phase_a_stream_sha256": stream_digest(phase_a),
            "phase_b_stream_sha256": stream_digest(phase_b),
            "stream_overlap": len(overlap),
            "proof_files_read": 0,
            "published_verdicts_read": 0,
        },
        "seed": {
            "file_sha256": seed_file_sha,
            "initial_capabilities": len(seed_archive),
        },
        "phase_a": {
            "tasks": len(phase_a),
            "new_capabilities": len(a_new),
            "post_a_archive_count": len(post_a_archive),
            "post_a_archive_sha256": post_a_digest,
            "neighborhood_children": sum(
                x["continuous"]["route"] == "NEIGHBORHOOD_CHILD" for x in phase_a_rows
            ),
            "direct_reuses": sum(
                x["continuous"]["route"] == "DIRECT_REUSE" for x in phase_a_rows
            ),
            "cvc5_acquisitions": sum(
                x["continuous"]["route"] == "CVC5_ACQUIRE" for x in phase_a_rows
            ),
        },
        "phase_b_frozen_transfer": {
            "tasks": len(phase_b),
            "seed_archive_solved": seed_transfer_count,
            "post_a_archive_solved": post_a_transfer_count,
            "strict_post_a_uplift": post_a_strict_uplift,
            "strict_post_a_cold_miss_uplift": post_a_cold_miss_uplift,
            "individual_a_ancestor_essential_cases": len(essential_examples),
            "essential_examples": essential_examples,
        },
        "aggregate_continuous": {
            "tasks": len(all_rows),
            "cold_verified_false": cold_false,
            "continuous_verified_false": continuous_false,
            "cold_cvc5_invocations": len(all_rows),
            "continuous_cvc5_invocations": continuous_cvc5,
            "cvc5_call_reduction_factor": (
                len(all_rows) / continuous_cvc5 if continuous_cvc5 else float("inf")
            ),
            "fresh_neighborhood_children": len(child_rows),
            "fresh_neighborhood_children_cold_missed": len(child_cold_misses),
            "final_archive_count": len(archive),
        },
        "gates": checks,
        "all_v59_gates_pass": all(checks.values()),
    }
    result["verdict"] = (
        "PASS_FRESH_COMPILED_MODEL_NEIGHBORHOOD_DEVELOPMENT_V59"
        if result["all_v59_gates_pass"]
        else "FAIL_FRESH_COMPILED_MODEL_NEIGHBORHOOD_DEVELOPMENT_V59"
    )
    result["claim_boundary"] = (
        "PASS would establish, on untouched external equational implications, that an exact retained finite "
        "countermodel can act as a parent capability rather than only a replayable specimen: a frozen "
        "source-constrained neighborhood compiler generates independently verified child models under the same "
        "solver budget where cold cvc5 misses; Phase-A experience measurably improves a frozen Phase-B transfer "
        "probe before any Phase-B learning; and at least one such transferred consequence depends on an exact "
        "Phase-A-acquired ancestor under deletion/restoration ablation. The claim remains bounded to finite "
        "countermodel capability; V59 does not promote TRUE or claim unrestricted theorem discovery."
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=True), encoding="utf-8")
    (out / "phase_a.json").write_text(json.dumps(phase_a_rows, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase_b_transfer.json").write_text(json.dumps(transfer_rows, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase_b_continuous.json").write_text(json.dumps(phase_b_rows, indent=2, sort_keys=True), encoding="utf-8")
    (out / "post_a_archive.json").write_text(json.dumps(post_a_archive, indent=2, sort_keys=True), encoding="utf-8")
    (out / "final_archive.json").write_text(json.dumps(archive, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=True), flush=True)
    if not result["all_v59_gates_pass"]:
        raise SystemExit("V59 frozen scientific verdict failed")


if __name__ == "__main__":
    main()
