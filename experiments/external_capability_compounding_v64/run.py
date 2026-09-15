#!/usr/bin/env python3
"""V64 opened calibration: source-law compilation across later targets.

Training block (already opened by V58):
  Wrong Book 3000 rows 2628:2756
  Wrong Book 3500 rows 2628:2756

Validation block (already opened by V59):
  Wrong Book 3000 rows 2756:2820
  Wrong Book 3500 rows 2756:2820

Protocol
--------
A target-independent cvc5 route probe is used only to decide whether an
implication should enter the proof-development route. cvc5 UNSAT remains
non-terminal; it is never promoted to TRUE.

During TRAIN, the first PROOF_CANDIDATE encountered for a source equation
causes that source law to be compiled once by V63's verified critical-pair
compiler. The resulting lemma basis is retained by exact source id.

During VALIDATION, for later problems whose source was compiled during TRAIN
and whose route probe again says PROOF_CANDIDATE, compare:

  COLD: source identity only + explicit narrowing.
  WARM: source identity + the retained TRAIN-derived lemma basis + the exact
        same narrowing machinery.

Every accepted proof is replayed step-by-step with complete substitutions.
No validation target can add or modify the retained TRAIN basis.

This is opened-data calibration only. Rows >= 2820 remain untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_V63_PATH = ROOT / "experiments" / "external_capability_compounding_v63" / "run.py"
_SPEC = importlib.util.spec_from_file_location("v64_v63", _V63_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load V63")
V63 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V63
_SPEC.loader.exec_module(V63)
V62 = V63.V62

_V58_PATH = ROOT / "experiments" / "external_capability_compounding_v58" / "run.py"
_SPEC2 = importlib.util.spec_from_file_location("v64_v58", _V58_PATH)
if _SPEC2 is None or _SPEC2.loader is None:
    raise RuntimeError("cannot load V58")
V58 = importlib.util.module_from_spec(_SPEC2)
sys.modules[_SPEC2.name] = V58
_SPEC2.loader.exec_module(V58)

TRAIN_START = 2628
TRAIN_COUNT = 128
VALID_START = 2756
VALID_COUNT = 64

ROUTE_TIMEOUT_MS = 450
MAX_VALIDATION_PROBES = 10


def load_slice(path: Path, expected_sha: str, start: int, count: int):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch: {path}: {digest}")
    lines = data.decode("utf-8").splitlines()
    chosen = lines[start:start + count]
    if len(chosen) != count:
        raise RuntimeError(f"expected {count} rows at {start}, got {len(chosen)}")
    return [json.loads(line) for line in chosen], digest


def source_id(problem: dict) -> str:
    return str(problem["eq1_id"])


def source_only_basis(problem):
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    eq = V62.Equation(0, lhs, rhs, key, {"kind": "SOURCE"}, 0)
    return {0: eq}


def compile_source(problem):
    sl, sr = V62.parse_eq(problem["equation1"])
    eqs, by_key, rounds, verified_count = V62.saturate(sl, sr)
    if len(eqs) != verified_count:
        raise RuntimeError(f"compiled source basis did not fully replay: {problem['id']}")
    return {
        "source_id": source_id(problem),
        "equation1": problem["equation1"],
        "eqs": eqs,
        "rounds": rounds,
        "verified_count": verified_count,
    }


def proof_for(problem, eqs):
    _sl, _sr = V62.parse_eq(problem["equation1"])
    tl, tr = V62.parse_eq(problem["equation2"])
    proof = V63.beam_narrow(tl, tr, eqs)
    replay = V63.verify_proof(proof["path"], proof["steps"], eqs) if proof["proved"] else False
    if proof["proved"] and not replay:
        raise RuntimeError(f"proof failed exact replay: {problem['id']}")
    return {
        "proved": bool(proof["proved"] and replay),
        "depth": len(proof["steps"]) if proof["proved"] else None,
        "generated": int(proof["generated"]),
        "used_rule_ids": [int(step["eid"]) for step in proof["steps"]] if proof["proved"] else [],
    }


def route(problem):
    result = V58.cvc5_construct(problem, timeout_ms=ROUTE_TIMEOUT_MS)
    return {
        "status": result.status,
        "elapsed_ms": result.elapsed_ms,
        "proof_candidate": result.status == "PROOF_CANDIDATE",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    train_a, sha3000 = load_slice(Path(args.book3000), V58.EXPECTED_3000_SHA256, TRAIN_START, TRAIN_COUNT)
    train_b, sha3500 = load_slice(Path(args.book3500), V58.EXPECTED_3500_SHA256, TRAIN_START, TRAIN_COUNT)
    valid_a, _ = load_slice(Path(args.book3000), V58.EXPECTED_3000_SHA256, VALID_START, VALID_COUNT)
    valid_b, _ = load_slice(Path(args.book3500), V58.EXPECTED_3500_SHA256, VALID_START, VALID_COUNT)
    train = train_a + train_b
    valid = valid_a + valid_b

    compiled = {}
    train_route_counts = {}
    compile_records = []

    for index, problem in enumerate(train, 1):
        r = route(problem)
        train_route_counts[r["status"]] = train_route_counts.get(r["status"], 0) + 1
        sid = source_id(problem)
        if r["proof_candidate"] and sid not in compiled:
            basis = compile_source(problem)
            compiled[sid] = basis
            compile_records.append({
                "source_id": sid,
                "trigger_problem_id": problem["id"],
                "compiled_equations": len(basis["eqs"]),
                "verified_equations": basis["verified_count"],
                "rounds": basis["rounds"],
            })
            print(json.dumps({
                "phase": "TRAIN_COMPILE",
                "index": index,
                "source_id": sid,
                "trigger": problem["id"],
                "compiled_equations": len(basis["eqs"]),
            }, sort_keys=True), flush=True)

    validation = []
    route_checked = 0
    for index, problem in enumerate(valid, 1):
        sid = source_id(problem)
        if sid not in compiled:
            continue

        r = route(problem)
        route_checked += 1
        if not r["proof_candidate"]:
            continue

        cold = proof_for(problem, source_only_basis(problem))
        warm = proof_for(problem, compiled[sid]["eqs"])
        derived_used = warm["proved"] and any(eid != 0 for eid in warm["used_rule_ids"])

        row = {
            "problem_id": problem["id"],
            "source_id": sid,
            "route_status": r["status"],
            "cold": cold,
            "warm": warm,
            "warm_only": warm["proved"] and not cold["proved"],
            "derived_rule_used": bool(derived_used),
        }
        validation.append(row)
        print(json.dumps({
            "phase": "VALID",
            "index": index,
            "problem_id": problem["id"],
            "source_id": sid,
            "cold": cold["proved"],
            "warm": warm["proved"],
            "cold_generated": cold["generated"],
            "warm_generated": warm["generated"],
            "derived_rule_used": derived_used,
        }, sort_keys=True), flush=True)

        if len(validation) >= MAX_VALIDATION_PROBES:
            break

    warm_proved = sum(x["warm"]["proved"] for x in validation)
    cold_proved = sum(x["cold"]["proved"] for x in validation)
    warm_only = sum(x["warm_only"] for x in validation)
    derived_success = sum(x["warm"]["proved"] and x["derived_rule_used"] for x in validation)

    common = [x for x in validation if x["warm"]["proved"] and x["cold"]["proved"]]
    common_depth_improved = sum(
        x["warm"]["depth"] < x["cold"]["depth"] for x in common
        if x["warm"]["depth"] is not None and x["cold"]["depth"] is not None
    )
    common_generated_cold = sum(x["cold"]["generated"] for x in common)
    common_generated_warm = sum(x["warm"]["generated"] for x in common)
    generation_ratio = (
        common_generated_cold / common_generated_warm
        if common_generated_warm
        else (float("inf") if common_generated_cold else 1.0)
    )

    checks = {
        "dataset_hashes_exact": (
            sha3000 == V58.EXPECTED_3000_SHA256
            and sha3500 == V58.EXPECTED_3500_SHA256
        ),
        "training_compiled_source_bases": len(compiled) > 0,
        "all_compiled_lemmas_exactly_replayed": all(
            rec["compiled_equations"] == rec["verified_equations"]
            for rec in compile_records
        ),
        "heldout_validation_has_prior_compiled_sources": len(validation) > 0,
        "warm_proves_at_least_one_later_target": warm_proved > 0,
        "warm_success_uses_acquired_lemma": derived_success > 0,
        "retained_basis_improves_later_proof_search": (
            warm_only > 0
            or common_depth_improved > 0
            or generation_ratio >= 1.10
        ),
        "warm_proof_coverage_not_worse": warm_proved >= cold_proved,
        "fresh_rows_2820_plus_untouched": True,
    }

    result = {
        "schema": "mathgraph.external-capability-compounding.v64.proof-basis-transfer-calibration",
        "classification": "OPENED_DATA_TRAIN_VALIDATION_NOT_FRESH_EVIDENCE",
        "protocol": {
            "train_rows_each": [TRAIN_START, TRAIN_START + TRAIN_COUNT],
            "validation_rows_each": [VALID_START, VALID_START + VALID_COUNT],
            "route_timeout_ms": ROUTE_TIMEOUT_MS,
            "max_validation_probes": MAX_VALIDATION_PROBES,
            "critical_pair_rounds": V62.MAX_ROUNDS,
            "max_compiled_equations": V62.MAX_EQUATIONS,
            "narrowing_depth": V63.MAX_DEPTH,
            "beam_width": V63.BEAM_WIDTH,
        },
        "train": {
            "tasks": len(train),
            "route_counts": train_route_counts,
            "compiled_sources": len(compiled),
            "compile_records": compile_records,
        },
        "validation": {
            "tasks_total": len(valid),
            "compiled_source_tasks_route_checked": route_checked,
            "probes": len(validation),
            "cold_proved": cold_proved,
            "warm_proved": warm_proved,
            "warm_only": warm_only,
            "warm_proofs_using_derived_rules": derived_success,
            "common_proved": len(common),
            "common_depth_improved": common_depth_improved,
            "common_cold_generated": common_generated_cold,
            "common_warm_generated": common_generated_warm,
            "common_generation_reduction_factor": generation_ratio,
            "records": validation,
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=True),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=True), flush=True)

    if not result["all_checks_pass"]:
        raise SystemExit("V64 proof-basis transfer calibration failed")


if __name__ == "__main__":
    main()
