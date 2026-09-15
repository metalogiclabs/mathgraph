#!/usr/bin/env python3
"""V74: exact global fixed-budget frontier optimality audit.

V73 ended every fresh six-operation source at a state with no positive one-swap
repair. V74 asks whether those local optima are actually global optima of the
frozen objective.

For each of the exact 16 V73 source graphs, enumerate every retained set of
B=5 nodes from the fixed round-1 pool of 18 nodes:

    C(18, 5) = 8568 states per source.

For each retained set K, compute the exact replay-verified next consequence
frontier R(K). The maximum |R(K)| is therefore the global optimum under the
frozen graph universe, retained-node budget, and frontier objective.

This is a post-hoc optimality audit on the now-opened V73 sources. It does not
create new prospective evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P73 = ROOT / "experiments" / "prospective_six_op_graph_development_v73" / "run.py"
S73 = importlib.util.spec_from_file_location("v74_v73", P73)
if S73 is None or S73.loader is None:
    raise RuntimeError("cannot load V73")
V73 = importlib.util.module_from_spec(S73)
sys.modules[S73.name] = V73
S73.loader.exec_module(V73)

V72 = V73.V72
V71 = V73.V71

EXPECTED_POOL = 18
EXPECTED_BUDGET = 5
EXPECTED_STATES = math.comb(EXPECTED_POOL, EXPECTED_BUDGET)


def global_optimum(graph):
    ids = tuple(sorted(graph["round1_ids"]))
    if len(ids) != EXPECTED_POOL:
        raise RuntimeError(
            f"unexpected round1 pool size {len(ids)} != {EXPECTED_POOL}"
        )

    best_size = -1
    best_sets = []
    states = 0

    for kept in itertools.combinations(ids, EXPECTED_BUDGET):
        states += 1
        size = len(V71.reachable_children(graph, kept))
        if size > best_size:
            best_size = size
            best_sets = [tuple(kept)]
        elif size == best_size:
            if len(best_sets) < 64:
                best_sets.append(tuple(kept))

    if states != EXPECTED_STATES:
        raise RuntimeError(f"state census mismatch: {states} != {EXPECTED_STATES}")

    return {
        "global_best_frontier_size": best_size,
        "states_enumerated": states,
        "stored_global_optima": best_sets,
    }


def swap_distance(a, b):
    sa = set(a)
    sb = set(b)
    if len(sa) != len(sb):
        raise ValueError("retained sets have different budgets")
    return len(sa - sb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened-laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    opened_path = Path(args.opened_laws)

    # Rebuild the exact V72 developer and exact deterministic V73 source stream.
    developer, developer_hash, _training, _sha, _attempts = (
        V73.rebuild_v72_developer(opened_path)
    )
    if developer_hash != V73.AUTHORITATIVE_V72_DEVELOPER_SHA256:
        raise RuntimeError("developer drift before V74 audit")

    fresh_graphs, fresh_sources = V73.generate_fresh_graphs()
    if len(fresh_graphs) != V73.FRESH_SOURCE_COUNT:
        raise RuntimeError("V73 source stream did not reproduce exactly")

    records = []
    total_gap = 0
    global_matches = 0
    max_gap = 0
    max_distance = 0

    for index, graph in enumerate(fresh_graphs, 1):
        learned = V72.gated_trajectory(graph, "learned", developer)
        learned_final = tuple(sorted(learned["final_retained"]))
        learned_size = len(learned["final_frontier"])

        audit = global_optimum(graph)
        global_size = audit["global_best_frontier_size"]
        gap = global_size - learned_size
        if gap < 0:
            raise RuntimeError("learned state exceeds computed global optimum")

        distances = [
            swap_distance(learned_final, opt)
            for opt in audit["stored_global_optima"]
        ]
        min_distance = min(distances) if distances else None

        total_gap += gap
        max_gap = max(max_gap, gap)
        if min_distance is not None:
            max_distance = max(max_distance, min_distance)
        global_matches += int(gap == 0)

        rec = {
            "index": index,
            "source_key": graph["source_key"],
            "learned_final_retained": learned_final,
            "learned_final_frontier_size": learned_size,
            "learned_one_swap_local_optimum_certified": (
                learned["local_optimum_certified"]
            ),
            "global_best_frontier_size": global_size,
            "global_optimality_gap": gap,
            "minimum_swap_distance_to_stored_global_optimum": min_distance,
            "states_enumerated": audit["states_enumerated"],
            "stored_global_optimum_count": len(audit["stored_global_optima"]),
            "stored_global_optima": audit["stored_global_optima"],
        }
        records.append(rec)

        print(json.dumps({
            "phase": "GLOBAL_AUDIT_V74",
            "index": index,
            "source": graph["source_key"][:12],
            "learned": learned_size,
            "global": global_size,
            "gap": gap,
            "distance": min_distance,
            "states": audit["states_enumerated"],
        }, sort_keys=True), flush=True)

    all_global = global_matches == len(records)
    checks = {
        "v73_source_stream_reproduced": len(records) == V73.FRESH_SOURCE_COUNT,
        "developer_hash_exact": (
            developer_hash == V73.AUTHORITATIVE_V72_DEVELOPER_SHA256
        ),
        "fixed_round1_pool_18": all(
            len(g["round1_ids"]) == EXPECTED_POOL for g in fresh_graphs
        ),
        "fixed_retained_budget_5": V71.RETAIN_BUDGET == EXPECTED_BUDGET,
        "all_8568_states_enumerated_per_source": all(
            r["states_enumerated"] == EXPECTED_STATES for r in records
        ),
        "every_learned_state_one_swap_local_optimum": all(
            r["learned_one_swap_local_optimum_certified"] for r in records
        ),
        "every_learned_state_is_global_optimum": all_global,
        "global_optimality_gap_zero": total_gap == 0,
    }

    result = {
        "schema": "mathgraph.global-frontier-optimality-audit.v74",
        "classification": "POSTHOC_EXACT_GLOBAL_FIXED_BUDGET_AUDIT",
        "developer_sha256": developer_hash,
        "v73_source_seed": V73.FRESH_STREAM_SEED,
        "objective": "maximize exact replay-verified round2 frontier size",
        "round1_pool": EXPECTED_POOL,
        "retained_budget": EXPECTED_BUDGET,
        "states_per_source": EXPECTED_STATES,
        "sources": len(records),
        "total_states_enumerated": EXPECTED_STATES * len(records),
        "global_matches": global_matches,
        "total_global_optimality_gap": total_gap,
        "max_global_optimality_gap": max_gap,
        "max_minimum_swap_distance_to_global_optimum": max_distance,
        "records": records,
        "checks": checks,
        "all_v74_gates_pass": all(checks.values()),
        "verdict": (
            "PASS_GLOBAL_FIXED_BUDGET_FRONTIER_OPTIMALITY_V74"
            if all(checks.values())
            else "FAIL_GLOBAL_FIXED_BUDGET_FRONTIER_OPTIMALITY_V74"
        ),
        "claim_boundary": (
            "A PASS certifies global optimality only for the frozen V73 graph model: "
            "18 replay-verified round-1 capability nodes, exactly 5 retained nodes, and "
            "objective equal to the number of directly replay-verified round-2 consequences "
            "whose recorded parents are retained. It does not establish optimality for deeper "
            "consequence layers, larger capability pools, variable budgets, other action "
            "grammars, or unrestricted theorem proving."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "fresh_sources.json").write_text(
        json.dumps(fresh_sources, indent=2, sort_keys=True)
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "sources": len(records),
        "states_per_source": EXPECTED_STATES,
        "total_states_enumerated": result["total_states_enumerated"],
        "global_matches": global_matches,
        "total_gap": total_gap,
        "max_gap": max_gap,
        "max_minimum_swap_distance": max_distance,
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
