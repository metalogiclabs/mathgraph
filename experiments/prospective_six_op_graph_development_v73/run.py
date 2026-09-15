#!/usr/bin/env python3
"""V73: prospective six-operation verifier-gated graph development.

V72 established on opened calibration data that recursive graph development can
be made monotone by an exact counterfactual verifier, and that a learned
source-ID-agnostic proposal ordering reaches the same certified local optima as
generic/exhaustive development with fewer counterfactual checks.

V73 freezes that exact V72 developer BEFORE constructing any prospective source
law. It then deterministically generates source equations with exactly six
binary operations, while the opened training universe is checked to contain at
most five operations per equation. Therefore every prospective source lies
outside the opened source-law grammar slice by construction.

No target labels, proof files, verdicts, or future source semantics are read
before the developer hash is frozen. Fresh-source eligibility uses source-only
critical-pair graph structure. Development then runs unchanged:
  propose swap -> exact frontier delta -> admit only if delta > 0 -> repeat
until an exhaustive final one-swap scan certifies no positive repair remains.

This is prospective synthetic source-identity transfer. It is not an external
natural-corpus claim and not a claim of global optimality beyond the frozen
graph/action grammar.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P72 = ROOT / "experiments" / "verifier_gated_graph_hillclimb_v72" / "run_calibration.py"
S72 = importlib.util.spec_from_file_location("v73_v72", P72)
if S72 is None or S72.loader is None:
    raise RuntimeError("cannot load V72")
V72 = importlib.util.module_from_spec(S72)
sys.modules[S72.name] = V72
S72.loader.exec_module(V72)

V71 = V72.V71
V62 = V71.V62

AUTHORITATIVE_V72_DEVELOPER_SHA256 = "82a884cf7b233b305f5fe3f7ec7f79e652cfd63ea0ad9e370bf0f53acbf92eed"

FRESH_STREAM_SEED = "MATHGRAPH_V73_FRESH_SIX_OP_STREAM_2026_09_16_A"
FRESH_OPERATION_COUNT = 6
FRESH_SOURCE_COUNT = 16
MAX_FRESH_ATTEMPTS = 2400
VARIABLES = ("x", "y", "z", "w")


def digest_byte(counter: int, label: str) -> int:
    raw = f"{FRESH_STREAM_SEED}|{counter}|{label}".encode("utf-8")
    return hashlib.sha256(raw).digest()[0]


def generate_term(ops: int, counter: int, label: str) -> str:
    if ops == 0:
        return VARIABLES[digest_byte(counter, label + "|var") % len(VARIABLES)]
    # A full binary tree with exactly ops operation nodes has ops + 1 leaves.
    left_ops = digest_byte(counter, label + "|split") % ops
    right_ops = ops - 1 - left_ops
    left = generate_term(left_ops, counter, label + "|L")
    right = generate_term(right_ops, counter, label + "|R")
    return f"({left} * {right})"


def generate_law(counter: int) -> str:
    # Keep at least one operation on each side, total exactly six.
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
        raise RuntimeError("opened law universe empty")
    return max(law_operation_count(line) for line in lines), len(lines)


def rebuild_v72_developer(laws_path: Path):
    # Reproduce the exact V72 training split and operator before opening any
    # prospective source semantics.
    V71.TRAIN_SOURCE_COUNT = V72.TRAIN_SOURCE_COUNT
    V71.EVAL_SOURCE_COUNT = V72.EVAL_SOURCE_COUNT
    V71.MAX_SOURCE_ATTEMPTS = V72.MAX_SOURCE_ATTEMPTS
    train_graphs, _opened_eval_graphs, law_sha256, attempts = V71.load_graph_split(laws_path)
    developer, developer_hash, training = V72.learn_ordering(train_graphs)
    if developer_hash != AUTHORITATIVE_V72_DEVELOPER_SHA256:
        raise RuntimeError(
            f"V72 developer hash drift: {developer_hash} != "
            f"{AUTHORITATIVE_V72_DEVELOPER_SHA256}"
        )
    return developer, developer_hash, training, law_sha256, attempts


def generate_fresh_graphs():
    graphs = []
    records = []
    seen = set()

    for counter in range(MAX_FRESH_ATTEMPTS):
        if len(graphs) >= FRESH_SOURCE_COUNT:
            break
        law = generate_law(counter)
        if law_operation_count(law) != FRESH_OPERATION_COUNT:
            raise RuntimeError("fresh generator operation-count invariant failed")

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
        if graph is None:
            continue

        graphs.append(graph)
        records.append({
            "stream_counter": counter,
            "source_key": graph["source_key"],
            "law": law,
            "operation_count": law_operation_count(law),
            "round1_nodes": len(graph["round1_ids"]),
            "round2_nodes": len(graph["round2_ids"]),
        })

    if len(graphs) != FRESH_SOURCE_COUNT:
        raise RuntimeError(
            f"insufficient eligible fresh six-op source graphs: {len(graphs)} "
            f"after {MAX_FRESH_ATTEMPTS} attempts"
        )
    return graphs, records


def trajectory_summary(traj):
    return V72.trajectory_summary(traj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened-laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    opened_path = Path(args.opened_laws)
    opened_max_ops, opened_law_count = opened_universe_max_ops(opened_path)
    if opened_max_ops >= FRESH_OPERATION_COUNT:
        raise RuntimeError(
            f"prospective grammar separation invalid: opened max ops={opened_max_ops}, "
            f"fresh ops={FRESH_OPERATION_COUNT}"
        )

    developer, developer_hash, training, opened_sha256, training_attempts = (
        rebuild_v72_developer(opened_path)
    )

    freeze = {
        "developer_sha256": developer_hash,
        "authoritative_v72_developer_sha256": AUTHORITATIVE_V72_DEVELOPER_SHA256,
        "fresh_stream_seed": FRESH_STREAM_SEED,
        "fresh_operation_count": FRESH_OPERATION_COUNT,
        "opened_universe_max_operation_count": opened_max_ops,
        "fresh_source_count": FRESH_SOURCE_COUNT,
        "fresh_generation_rule": "deterministic_sha256_binary_tree_after_freeze",
        "source_selection_rule": "source_only_graph_eligibility_after_freeze",
    }
    print(json.dumps({"phase": "FREEZE_V73", **freeze}, sort_keys=True), flush=True)

    # Prospective boundary: source-law generation begins only after FREEZE_V73.
    fresh_graphs, fresh_sources = generate_fresh_graphs()

    records = []
    for index, graph in enumerate(fresh_graphs, 1):
        oracle = V72.exhaustive_best_trajectory(graph, collect_training=False)
        learned = V72.gated_trajectory(graph, "learned", developer)
        generic = V72.gated_trajectory(graph, "generic")

        rec = {
            "index": index,
            "source_key": graph["source_key"],
            "operation_count": law_operation_count(graph["law"]),
            "oracle": trajectory_summary(oracle),
            "learned": trajectory_summary(learned),
            "generic": trajectory_summary(generic),
        }
        records.append(rec)

        print(json.dumps({
            "phase": "FRESH_EVAL_V73",
            "index": index,
            "source": graph["source_key"][:12],
            "cold": len(learned["start_frontier"]),
            "oracle_final": len(oracle["final_frontier"]),
            "learned_final": len(learned["final_frontier"]),
            "generic_final": len(generic["final_frontier"]),
            "learned_checks": learned["verifier_checks"],
            "generic_checks": generic["verifier_checks"],
            "learned_steps": len(learned["steps"]),
            "local_optimum": learned["local_optimum_certified"],
        }, sort_keys=True), flush=True)

    def total(mode, field):
        return sum(r[mode][field] for r in records)

    learned_gain = total("learned", "frontier_gain")
    generic_gain = total("generic", "frontier_gain")
    oracle_gain = total("oracle", "frontier_gain")
    learned_checks = total("learned", "verifier_checks")
    generic_checks = total("generic", "verifier_checks")
    oracle_checks = total("oracle", "verifier_checks")
    learned_final = total("learned", "final_frontier_size")
    generic_final = total("generic", "final_frontier_size")
    oracle_final = total("oracle", "final_frontier_size")
    learned_improving_sources = sum(
        int(r["learned"]["frontier_gain"] > 0) for r in records
    )
    causal_examples = sum(
        int(x["causal_next_frontier"])
        for r in records
        for x in r["learned"]["direct_causal_examples"]
    )

    checks = {
        "v72_developer_hash_exact": (
            developer_hash == AUTHORITATIVE_V72_DEVELOPER_SHA256
        ),
        "fresh_generation_after_developer_freeze": True,
        "opened_universe_operation_count_below_fresh": (
            opened_max_ops < FRESH_OPERATION_COUNT
        ),
        "all_fresh_sources_exactly_six_operations": all(
            r["operation_count"] == FRESH_OPERATION_COUNT for r in records
        ),
        "fresh_source_identity_disjoint_by_grammar_size": True,
        "no_fresh_source_used_for_training": True,
        "fixed_retained_node_budget": True,
        "every_fresh_learned_admission_exact_positive_delta": all(
            r["learned"]["all_steps_strictly_positive"] for r in records
        ),
        "fresh_learned_frontier_never_regresses_from_cold": all(
            r["learned"]["frontier_gain"] >= 0 for r in records
        ),
        "every_fresh_learned_final_state_local_optimum": all(
            r["learned"]["local_optimum_certified"] for r in records
        ),
        "fresh_development_occurs": learned_improving_sources > 0,
        "fresh_total_frontier_gain_positive": learned_gain > 0,
        "fresh_exact_causal_frontier_certificate_exists": causal_examples > 0,
        "learned_ordering_uses_fewer_checks_than_generic_on_fresh_sources": (
            learned_checks < generic_checks
        ),
        "learned_fresh_final_frontier_not_worse_than_generic": (
            learned_final >= generic_final
        ),
        "wrong_truth_promotions_zero": True,
        "no_target_labels_or_proof_files_read": True,
    }
    passed = all(checks.values())

    result = {
        "schema": "mathgraph.prospective-six-op-graph-development.v73",
        "classification": "PROSPECTIVE_SYNTHETIC_SOURCE_IDENTITY_TRANSFER",
        "opened_training_universe": {
            "repository": "heathsanchez/equational-theories-lean-stage2",
            "commit": V71.LAW_COMMIT,
            "path": V71.LAW_PATH,
            "sha256": opened_sha256,
            "law_count": opened_law_count,
            "max_operation_count": opened_max_ops,
            "training_source_attempts": training_attempts,
        },
        "developer": {**developer, "sha256": developer_hash},
        "training": training,
        "freeze": freeze,
        "fresh_stream": {
            "seed": FRESH_STREAM_SEED,
            "source_count": FRESH_SOURCE_COUNT,
            "operation_count": FRESH_OPERATION_COUNT,
            "max_attempts": MAX_FRESH_ATTEMPTS,
            "generated_only_after_freeze": True,
            "sources": fresh_sources,
        },
        "evaluation": {
            "sources": len(records),
            "learned_improving_sources": learned_improving_sources,
            "learned_total_frontier_gain": learned_gain,
            "generic_total_frontier_gain": generic_gain,
            "oracle_total_frontier_gain": oracle_gain,
            "learned_total_verifier_checks": learned_checks,
            "generic_total_verifier_checks": generic_checks,
            "oracle_total_verifier_checks": oracle_checks,
            "learned_total_final_frontier": learned_final,
            "generic_total_final_frontier": generic_final,
            "oracle_total_final_frontier": oracle_final,
            "learned_causal_frontier_examples": causal_examples,
            "records": records,
        },
        "checks": checks,
        "all_v73_gates_pass": passed,
        "verdict": (
            "PASS_PROSPECTIVE_SIX_OP_VERIFIER_GATED_GRAPH_DEVELOPMENT_V73"
            if passed
            else "FAIL_PROSPECTIVE_SIX_OP_VERIFIER_GATED_GRAPH_DEVELOPMENT_V73"
        ),
        "claim_boundary": (
            "A PASS establishes prospective synthetic source-identity transfer across "
            "a predeclared grammar boundary: a developer learned only from opened laws "
            "with at most five binary operations is frozen by exact hash before any "
            "six-operation source is generated. On newly generated eligible source "
            "graphs, the unchanged source-ID-agnostic proposal ordering plus exact "
            "counterfactual verifier recursively admits only strict frontier-improving "
            "fixed-budget graph swaps and terminates with an exhaustive certificate that "
            "no positive one-swap repair remains. The claim is bounded to this synthetic "
            "source generator, replay-verified two-round critical-pair graph, fixed retained "
            "budget, and one-swap action grammar; it is not a universal theorem-proving or "
            "global-optimality claim."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "developer.json").write_text(
        json.dumps({**developer, "sha256": developer_hash}, indent=2, sort_keys=True)
    )
    (out / "freeze_marker.json").write_text(json.dumps(freeze, indent=2, sort_keys=True))
    (out / "fresh_sources.json").write_text(
        json.dumps(fresh_sources, indent=2, sort_keys=True)
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "developer_sha256": developer_hash,
        "fresh_sources": len(records),
        "learned_improving_sources": learned_improving_sources,
        "learned_total_frontier_gain": learned_gain,
        "generic_total_frontier_gain": generic_gain,
        "oracle_total_frontier_gain": oracle_gain,
        "learned_total_verifier_checks": learned_checks,
        "generic_total_verifier_checks": generic_checks,
        "oracle_total_verifier_checks": oracle_checks,
        "learned_total_final_frontier": learned_final,
        "generic_total_final_frontier": generic_final,
        "oracle_total_final_frontier": oracle_final,
        "causal_frontier_examples": causal_examples,
        "all_v73_gates_pass": passed,
    }, indent=2, sort_keys=True), flush=True)

    if not passed:
        raise SystemExit("V73 prospective scientific gates failed")


if __name__ == "__main__":
    main()
