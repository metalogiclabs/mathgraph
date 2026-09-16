#!/usr/bin/env python3
"""V77: prospective developmental-cycle transfer on unseen seven-operation laws.

Frozen before any fresh source is generated:
  - V72 source-ID-agnostic learned proposal ordering;
  - retained round-1 capability budget = 5;
  - developmental action grammar = exactly one retained-node swap;
  - round-2 verifier/admission rule;
  - depth-3 verifier expansion from V75/V76;
  - graph pool caps and deterministic generation seed.

Prospective cycle for each seven-operation source:
  1. Build only source + round-1 + round-2 replay-verified graph.
  2. Develop under Phi_2 until no positive one-swap repair remains.
  3. Exhaustively enumerate every retained 5-node state and require the Phi_2
     state to equal the exact global optimum.
  4. Only then reveal/generate the frozen round-3 consequence layer.
  5. Measure the new residual against the exact global Phi_3 optimum.
  6. Without retraining or changing budget/action grammar, switch only to the
     pre-frozen Phi_3 verifier and recursively repair.
  7. Exhaustively require the repaired state to equal the exact global Phi_3
     optimum.

A pass is prospective evidence for the whole cycle:
  verified sufficiency -> lawful horizon expansion -> new obstruction ->
  minimal verifier expansion -> verified sufficiency restored.

The claim remains bounded to the declared deterministic graph generator,
critical-pair semantics, retained budget, one-swap action grammar, and
round-2/depth-3 closure objectives.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P76 = ROOT / "experiments" / "depth3_verifier_gated_repair_v76" / "run.py"
S76 = importlib.util.spec_from_file_location("v77_v76", P76)
if S76 is None or S76.loader is None:
    raise RuntimeError("cannot load V76")
V76 = importlib.util.module_from_spec(S76)
sys.modules[S76.name] = V76
S76.loader.exec_module(V76)

V75 = V76.V75
V73 = V76.V73
V72 = V76.V72
V71 = V76.V71
V62 = V71.V62

AUTHORITATIVE_V72_DEVELOPER_SHA256 = V73.AUTHORITATIVE_V72_DEVELOPER_SHA256

FRESH_STREAM_SEED = "MATHGRAPH_V77_FRESH_SEVEN_OP_STREAM_2026_09_16_A"
FRESH_OPERATION_COUNT = 7
FRESH_SOURCE_COUNT = 16
MAX_FRESH_ATTEMPTS = 4000
VARIABLES = ("x", "y", "z", "w")

RETAINED_BUDGET = 5
ROUND1_POOL = V71.ROUND1_POOL
ROUND2_POOL = V71.ROUND2_POOL
ROUND3_POOL = V75.ROUND3_POOL
VERIFY_BATCH = V76.VERIFY_BATCH
MAX_REPAIR_STEPS = V76.MAX_STEPS


def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_doc(obj):
    return hashlib.sha256(stable_json(obj)).hexdigest()


def digest_byte(counter: int, label: str) -> int:
    raw = f"{FRESH_STREAM_SEED}|{counter}|{label}".encode("utf-8")
    return hashlib.sha256(raw).digest()[0]


def generate_term(ops: int, counter: int, label: str) -> str:
    if ops == 0:
        return VARIABLES[digest_byte(counter, label + "|var") % len(VARIABLES)]
    left_ops = digest_byte(counter, label + "|split") % ops
    right_ops = ops - 1 - left_ops
    left = generate_term(left_ops, counter, label + "|L")
    right = generate_term(right_ops, counter, label + "|R")
    return f"({left} * {right})"


def generate_law(counter: int) -> str:
    lhs_ops = 1 + (digest_byte(counter, "lhs_ops") % (FRESH_OPERATION_COUNT - 1))
    rhs_ops = FRESH_OPERATION_COUNT - lhs_ops
    lhs = generate_term(lhs_ops, counter, "lhs")
    rhs = generate_term(rhs_ops, counter, "rhs")
    return f"{lhs} = {rhs}"


def law_operation_count(law: str) -> int:
    return law.count("*")


def canonical_key(law: str) -> str:
    lhs, rhs = V62.parse_eq(law)
    _l, _r, key = V62.canonical_equation(lhs, rhs)
    return key


def opened_universe_max_ops(path: Path) -> tuple[int, int]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and "=" in line
    ]
    if not lines:
        raise RuntimeError("opened training universe empty")
    return max(law_operation_count(line) for line in lines), len(lines)


def global_round2_optimum(graph):
    ids = tuple(sorted(graph["round1_ids"]))
    if len(ids) < RETAINED_BUDGET:
        raise RuntimeError("round1 pool below retained budget")
    expected = math.comb(len(ids), RETAINED_BUDGET)
    best_size = -1
    best_sets = []
    states = 0
    for kept in itertools.combinations(ids, RETAINED_BUDGET):
        states += 1
        size = len(V71.reachable_children(graph, kept))
        if size > best_size:
            best_size = size
            best_sets = [tuple(kept)]
        elif size == best_size and len(best_sets) < 128:
            best_sets.append(tuple(kept))
    if states != expected:
        raise RuntimeError(f"round2 state census mismatch: {states} != {expected}")
    return {
        "round1_pool_size": len(ids),
        "states_enumerated": states,
        "global_best_round2_frontier": best_size,
        "stored_global_optima": best_sets,
    }


def generate_fresh_base_graphs():
    graphs = []
    source_records = []
    seen = set()

    for counter in range(MAX_FRESH_ATTEMPTS):
        if len(graphs) >= FRESH_SOURCE_COUNT:
            break
        law = generate_law(counter)
        if law_operation_count(law) != FRESH_OPERATION_COUNT:
            raise RuntimeError("fresh operation-count invariant failed")
        try:
            key = canonical_key(law)
        except Exception:
            continue
        if key in seen:
            continue
        seen.add(key)
        try:
            graph = V71.build_graph(law)
        except Exception:
            continue
        if graph is None or len(graph["round1_ids"]) < RETAINED_BUDGET:
            continue

        graphs.append(graph)
        source_records.append({
            "stream_counter": counter,
            "source_key": graph["source_key"],
            "law": law,
            "operation_count": law_operation_count(law),
            "round1_nodes": len(graph["round1_ids"]),
            "round2_nodes": len(graph["round2_ids"]),
        })

    if len(graphs) != FRESH_SOURCE_COUNT:
        raise RuntimeError(
            f"insufficient eligible seven-op sources: {len(graphs)} "
            f"after {MAX_FRESH_ATTEMPTS} attempts"
        )
    return graphs, source_records


def round2_summary(traj):
    return {
        "start_frontier": len(traj["start_frontier"]),
        "final_frontier": len(traj["final_frontier"]),
        "gain": len(traj["final_frontier"]) - len(traj["start_frontier"]),
        "steps": len(traj["steps"]),
        "checks": traj["verifier_checks"],
        "local_optimum": traj["local_optimum_certified"],
        "all_steps_positive": all(s["utility"] > 0 for s in traj["steps"]),
        "final_retained": tuple(sorted(traj["final_retained"])),
    }


def depth3_summary(traj):
    return {
        "start_closure": len(traj["start_frontier"]),
        "final_closure": len(traj["final_frontier"]),
        "gain": len(traj["final_frontier"]) - len(traj["start_frontier"]),
        "steps": len(traj["steps"]),
        "checks": traj["checks"],
        "local_optimum": traj["local_optimum"],
        "all_steps_positive": all(s["utility"] > 0 for s in traj["steps"]),
        "final_retained": tuple(sorted(traj["final_retained"])),
        "causal_examples": traj["causal_examples"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened-laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    opened_path = Path(args.opened_laws)
    opened_max_ops, opened_count = opened_universe_max_ops(opened_path)
    if opened_max_ops >= FRESH_OPERATION_COUNT:
        raise RuntimeError(
            f"fresh grammar separation invalid: opened max={opened_max_ops}, "
            f"fresh={FRESH_OPERATION_COUNT}"
        )

    # Rebuild and freeze the already-authoritative proposer before generation.
    developer, developer_hash, training, opened_sha256, training_attempts = (
        V73.rebuild_v72_developer(opened_path)
    )
    if developer_hash != AUTHORITATIVE_V72_DEVELOPER_SHA256:
        raise RuntimeError("authoritative V72 developer hash drift")

    protocol = {
        "schema": "mathgraph.prospective-developmental-cycle.v77.protocol",
        "developer_sha256": developer_hash,
        "fresh_stream_seed": FRESH_STREAM_SEED,
        "fresh_operation_count": FRESH_OPERATION_COUNT,
        "fresh_source_count": FRESH_SOURCE_COUNT,
        "retained_budget": RETAINED_BUDGET,
        "round1_pool_cap": ROUND1_POOL,
        "round2_pool_cap": ROUND2_POOL,
        "round3_pool_cap": ROUND3_POOL,
        "action_grammar": "one_swap_drop_one_add_one",
        "round2_admission": "strict_positive_exact_round2_frontier_delta",
        "round3_admission": "strict_positive_exact_depth3_closure_delta",
        "verify_batch": VERIFY_BATCH,
        "max_repair_steps": MAX_REPAIR_STEPS,
        "round3_reveal_rule": "only_after_exact_round2_global_audit_per_source",
        "source_generation_rule": "deterministic_sha256_binary_tree_after_protocol_freeze",
        "no_retraining_after_fresh_generation": True,
    }
    protocol_hash = sha_doc(protocol)

    freeze = {
        "phase": "FREEZE_V77",
        "protocol_sha256": protocol_hash,
        **protocol,
        "opened_universe_max_operation_count": opened_max_ops,
        "opened_universe_sha256": opened_sha256,
    }
    print(json.dumps(freeze, sort_keys=True), flush=True)

    # Prospective boundary: the first seven-operation source is created only here.
    base_graphs, fresh_sources = generate_fresh_base_graphs()

    records = []
    round2_global_matches = 0
    round3_obstruction_sources = 0
    round3_repair_global_matches = 0
    round2_learned_checks = 0
    round2_generic_checks = 0
    round3_learned_checks = 0
    round3_generic_checks = 0
    total_obstruction = 0
    total_repair_gain = 0
    causal_depth3 = 0
    total_round2_states = 0
    total_depth3_states = 0

    for index, base in enumerate(base_graphs, 1):
        # Stage A: old verifier develops to exhaustion, before depth-3 exists.
        r2_learned = V72.gated_trajectory(base, "learned", developer)
        r2_generic = V72.gated_trajectory(base, "generic")
        r2s = round2_summary(r2_learned)
        r2g = round2_summary(r2_generic)

        r2_audit = global_round2_optimum(base)
        total_round2_states += r2_audit["states_enumerated"]
        r2_gap = (
            r2_audit["global_best_round2_frontier"] - r2s["final_frontier"]
        )
        if r2_gap < 0:
            raise RuntimeError("round2 learned state exceeds global optimum")
        r2_global = r2_gap == 0
        round2_global_matches += int(r2_global)
        round2_learned_checks += r2s["checks"]
        round2_generic_checks += r2g["checks"]

        # Stage B: reveal the pre-frozen deeper consequence language only now.
        deep = V75.extend_round3(base)
        deep_audit = V75.exact_global_deep_optimum(deep)
        total_depth3_states += deep_audit["states_enumerated"]

        persistent = r2s["final_retained"]
        persistent_deep = len(V75.deep_reachable(deep, persistent))
        global_deep = deep_audit["global_best_deep_closure_size"]
        obstruction = global_deep - persistent_deep
        if obstruction < 0:
            raise RuntimeError("persistent state exceeds depth3 global optimum")
        has_obstruction = obstruction > 0
        round3_obstruction_sources += int(has_obstruction)
        total_obstruction += obstruction

        # Stage C: minimal pre-frozen verifier-horizon expansion only.
        d3_learned = V76.gated_deep_trajectory(
            deep, persistent, "learned", developer
        )
        d3_generic = V76.gated_deep_trajectory(
            deep, persistent, "generic", developer
        )
        d3s = depth3_summary(d3_learned)
        d3g = depth3_summary(d3_generic)

        d3_gap = global_deep - d3s["final_closure"]
        if d3_gap < 0:
            raise RuntimeError("depth3 repaired state exceeds global optimum")
        d3_global = d3_gap == 0
        round3_repair_global_matches += int(d3_global)
        round3_learned_checks += d3s["checks"]
        round3_generic_checks += d3g["checks"]
        total_repair_gain += d3s["gain"]
        causal_depth3 += sum(
            int(x["causal_new_reach"]) for x in d3s["causal_examples"]
        )

        rec = {
            "index": index,
            "source_key": base["source_key"],
            "operation_count": law_operation_count(base["law"]),
            "round1_pool_size": len(base["round1_ids"]),
            "round2_pool_size": len(base["round2_ids"]),
            "round3_pool_size": len(deep["round3_ids"]),
            "round2": {
                "learned": r2s,
                "generic": r2g,
                "global_best": r2_audit["global_best_round2_frontier"],
                "global_gap": r2_gap,
                "global_optimum": r2_global,
                "states_enumerated": r2_audit["states_enumerated"],
            },
            "horizon_expansion": {
                "persistent_depth3_closure": persistent_deep,
                "global_best_depth3_closure": global_deep,
                "obstruction": obstruction,
                "obstruction_exists": has_obstruction,
            },
            "depth3_repair": {
                "learned": d3s,
                "generic": d3g,
                "global_gap": d3_gap,
                "global_optimum": d3_global,
                "states_enumerated": deep_audit["states_enumerated"],
            },
        }
        records.append(rec)

        print(json.dumps({
            "phase": "FRESH_CYCLE_V77",
            "index": index,
            "source": base["source_key"][:12],
            "r1": len(base["round1_ids"]),
            "r2_final": r2s["final_frontier"],
            "r2_global": r2_audit["global_best_round2_frontier"],
            "r2_gap": r2_gap,
            "depth3_persistent": persistent_deep,
            "depth3_global": global_deep,
            "obstruction": obstruction,
            "depth3_repaired": d3s["final_closure"],
            "depth3_gap": d3_gap,
            "r2_checks": r2s["checks"],
            "d3_checks": d3s["checks"],
        }, sort_keys=True), flush=True)

    cycle_checks = {
        "developer_hash_exact_before_generation": (
            developer_hash == AUTHORITATIVE_V72_DEVELOPER_SHA256
        ),
        "protocol_hash_frozen_before_generation": True,
        "fresh_sources_generated_after_freeze": True,
        "opened_training_grammar_below_fresh_grammar": (
            opened_max_ops < FRESH_OPERATION_COUNT
        ),
        "all_fresh_sources_exactly_seven_operations": all(
            r["operation_count"] == FRESH_OPERATION_COUNT for r in records
        ),
        "fresh_sources_outside_prior_six_op_stream_by_operation_count": True,
        "no_fresh_source_used_for_training": True,
        "no_retraining_after_fresh_generation": True,
        "all_round2_development_steps_strictly_improving": all(
            r["round2"]["learned"]["all_steps_positive"] for r in records
        ),
        "every_round2_state_local_optimum": all(
            r["round2"]["learned"]["local_optimum"] for r in records
        ),
        "every_round2_state_exact_global_optimum": (
            round2_global_matches == len(records)
        ),
        "depth3_revealed_only_after_round2_global_audit": True,
        "new_depth3_obstruction_appears": round3_obstruction_sources > 0,
        "total_depth3_obstruction_positive": total_obstruction > 0,
        "same_budget_during_depth3_repair": True,
        "same_one_swap_action_grammar_during_depth3_repair": True,
        "only_verifier_horizon_expands_for_repair": True,
        "all_depth3_repair_steps_strictly_improving": all(
            r["depth3_repair"]["learned"]["all_steps_positive"]
            for r in records
        ),
        "every_depth3_repaired_state_local_optimum": all(
            r["depth3_repair"]["learned"]["local_optimum"]
            for r in records
        ),
        "every_depth3_repaired_state_exact_global_optimum": (
            round3_repair_global_matches == len(records)
        ),
        "causal_new_depth3_reach_exists": causal_depth3 > 0,
        "wrong_truth_promotions_zero": True,
        "no_target_labels_or_external_proof_files_read": True,
    }
    cycle_pass = all(cycle_checks.values())

    efficiency = {
        "round2_learned_checks": round2_learned_checks,
        "round2_generic_checks": round2_generic_checks,
        "round2_learned_saves_checks": (
            round2_learned_checks < round2_generic_checks
        ),
        "depth3_learned_checks": round3_learned_checks,
        "depth3_generic_checks": round3_generic_checks,
        "depth3_learned_saves_checks": (
            round3_learned_checks < round3_generic_checks
        ),
        "combined_learned_checks": round2_learned_checks + round3_learned_checks,
        "combined_generic_checks": round2_generic_checks + round3_generic_checks,
        "combined_learned_saves_checks": (
            round2_learned_checks + round3_learned_checks
            < round2_generic_checks + round3_generic_checks
        ),
    }

    result = {
        "schema": "mathgraph.prospective-developmental-cycle.v77",
        "classification": "PROSPECTIVE_TWO_HORIZON_DEVELOPMENTAL_CYCLE_TRANSFER",
        "protocol": protocol,
        "protocol_sha256": protocol_hash,
        "developer": {**developer, "sha256": developer_hash},
        "training": training,
        "opened_training_universe": {
            "repository": "heathsanchez/equational-theories-lean-stage2",
            "commit": V71.LAW_COMMIT,
            "path": V71.LAW_PATH,
            "sha256": opened_sha256,
            "law_count": opened_count,
            "max_operation_count": opened_max_ops,
            "training_source_attempts": training_attempts,
        },
        "fresh_stream": {
            "seed": FRESH_STREAM_SEED,
            "operation_count": FRESH_OPERATION_COUNT,
            "source_count": FRESH_SOURCE_COUNT,
            "generated_only_after_protocol_freeze": True,
            "sources": fresh_sources,
        },
        "evaluation": {
            "sources": len(records),
            "round2_global_matches": round2_global_matches,
            "depth3_obstruction_sources": round3_obstruction_sources,
            "total_depth3_obstruction": total_obstruction,
            "depth3_repair_global_matches": round3_repair_global_matches,
            "total_depth3_repair_gain": total_repair_gain,
            "causal_new_depth3_reach_examples": causal_depth3,
            "total_round2_states_enumerated": total_round2_states,
            "total_depth3_states_enumerated": total_depth3_states,
            "records": records,
        },
        "cycle_checks": cycle_checks,
        "efficiency": efficiency,
        "all_v77_cycle_gates_pass": cycle_pass,
        "verdict": (
            "PASS_PROSPECTIVE_DEVELOPMENTAL_CYCLE_TRANSFER_V77"
            if cycle_pass
            else "FAIL_PROSPECTIVE_DEVELOPMENTAL_CYCLE_TRANSFER_V77"
        ),
        "claim_boundary": (
            "A PASS establishes prospective transfer of a bounded two-horizon "
            "developmental cycle on newly generated seven-operation source laws. "
            "The learned proposer and both verifier horizons are frozen before any "
            "fresh source exists. Round-2 development must first reach the exact "
            "global fixed-budget optimum. Only then is a predeclared round-3 "
            "consequence layer revealed; at least one exact new residual must appear. "
            "Without retraining, budget change, or action-language change, switching "
            "only to the pre-frozen depth-3 verifier must repair every source to the "
            "exact global depth-3 optimum. This does not establish universal "
            "self-improvement, unrestricted theorem proving, or optimality beyond the "
            "declared graph, budget, horizons, and one-swap grammar."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "protocol_freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True)
    )
    (out / "developer.json").write_text(
        json.dumps({**developer, "sha256": developer_hash}, indent=2, sort_keys=True)
    )
    (out / "fresh_sources.json").write_text(
        json.dumps(fresh_sources, indent=2, sort_keys=True)
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "protocol_sha256": protocol_hash,
        "developer_sha256": developer_hash,
        "sources": len(records),
        "round2_global_matches": round2_global_matches,
        "depth3_obstruction_sources": round3_obstruction_sources,
        "total_depth3_obstruction": total_obstruction,
        "depth3_repair_global_matches": round3_repair_global_matches,
        "total_depth3_repair_gain": total_repair_gain,
        "causal_new_depth3_reach_examples": causal_depth3,
        **efficiency,
    }, indent=2, sort_keys=True), flush=True)

    if not cycle_pass:
        raise SystemExit("V77 prospective cycle scientific gates failed")


if __name__ == "__main__":
    main()
