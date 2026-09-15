#!/usr/bin/env python3
"""V75: exact depth-3 consequence-closure global optimality audit.

V74 exhausted the frozen V73 round-2 objective: on all 16 prospective six-op
sources, the learned V73 retained state is a true global optimum over every
fixed-budget retained subset.

V75 expands only the consequence horizon. For each exact V73 source graph:
  * retain the original replay-verified source + round-1 + round-2 graph;
  * deterministically generate a replay-verified round-3 pool by critical pairs
    touching the complete round-2 frontier;
  * for each possible retained 5-node round-1 set K, compute the reachable
    consequence closure through round 2 and round 3 by derivation-parent
    availability;
  * enumerate every possible K and find the exact global depth-3 optimum.

This is a post-hoc expansion audit on already-opened V73 sources. It answers
whether a capability set globally optimal for immediate consequences remains
globally optimal after one more verified generation of compounding.
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
P74 = ROOT / "experiments" / "global_frontier_optimality_audit_v74" / "run.py"
S74 = importlib.util.spec_from_file_location("v75_v74", P74)
if S74 is None or S74.loader is None:
    raise RuntimeError("cannot load V74")
V74 = importlib.util.module_from_spec(S74)
sys.modules[S74.name] = V74
S74.loader.exec_module(V74)

V73 = V74.V73
V72 = V74.V72
V71 = V74.V71
V62 = V71.V62

RETAINED_BUDGET = 5
ROUND3_POOL = 144


def extend_round3(base):
    eqs = dict(base["eqs"])
    existing_keys = {eq.key for eq in eqs.values()}
    next_id = max(eqs) + 1

    raw = V71.enumerate_candidates(
        eqs,
        base["round2_ids"],
        existing_keys,
    )
    round3_ids = []
    for complexity, key, cl, cr, proof in raw[:ROUND3_POOL]:
        child = V62.Equation(next_id, cl, cr, key, proof, 3)
        trial = dict(eqs)
        trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("round-3 critical-pair replay failed")
        eqs[next_id] = child
        existing_keys.add(key)
        round3_ids.append(next_id)
        next_id += 1

    for eid in round3_ids:
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored round-3 replay failed: {eid}")

    return {
        **base,
        "eqs": eqs,
        "round3_ids": round3_ids,
    }


def deep_reachable(graph, retained):
    reachable = {0, *retained}
    descendants = set()

    # Round-2 nodes depend only on source/round-1 nodes in the frozen graph.
    for eid in graph["round2_ids"]:
        p = graph["eqs"][eid].proof
        if int(p["a"]) in reachable and int(p["b"]) in reachable:
            reachable.add(eid)
            descendants.add(eid)

    # Round-3 nodes were generated before any round-3 node existed, so all
    # recorded parents are source/round-1/round-2 and this pass is exact.
    for eid in graph["round3_ids"]:
        p = graph["eqs"][eid].proof
        if int(p["a"]) in reachable and int(p["b"]) in reachable:
            reachable.add(eid)
            descendants.add(eid)

    return descendants


def exact_global_deep_optimum(graph):
    ids = tuple(sorted(graph["round1_ids"]))
    if len(ids) < RETAINED_BUDGET:
        raise RuntimeError("round1 pool below retained budget")

    expected = math.comb(len(ids), RETAINED_BUDGET)
    best_size = -1
    best_sets = []
    states = 0

    for kept in itertools.combinations(ids, RETAINED_BUDGET):
        states += 1
        size = len(deep_reachable(graph, kept))
        if size > best_size:
            best_size = size
            best_sets = [tuple(kept)]
        elif size == best_size and len(best_sets) < 64:
            best_sets.append(tuple(kept))

    if states != expected:
        raise RuntimeError(f"deep state census mismatch {states} != {expected}")

    return {
        "round1_pool_size": len(ids),
        "states_enumerated": states,
        "global_best_deep_closure_size": best_size,
        "stored_global_optima": best_sets,
    }


def swap_distance(a, b):
    return len(set(a) - set(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened-laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    opened = Path(args.opened_laws)
    developer, developer_hash, _training, _sha, _attempts = (
        V73.rebuild_v72_developer(opened)
    )
    if developer_hash != V73.AUTHORITATIVE_V72_DEVELOPER_SHA256:
        raise RuntimeError("developer drift before V75")

    bases, fresh_sources = V73.generate_fresh_graphs()
    deep_graphs = [extend_round3(g) for g in bases]

    records = []
    v73_global_matches = 0
    total_gap = 0
    max_gap = 0
    max_distance = 0
    total_states = 0
    total_r3 = 0

    for index, graph in enumerate(deep_graphs, 1):
        learned = V72.gated_trajectory(graph, "learned", developer)
        learned_kept = tuple(sorted(learned["final_retained"]))
        learned_deep = len(deep_reachable(graph, learned_kept))

        audit = exact_global_deep_optimum(graph)
        global_deep = audit["global_best_deep_closure_size"]
        gap = global_deep - learned_deep
        if gap < 0:
            raise RuntimeError("V73 retained state exceeds depth-3 global optimum")

        distances = [
            swap_distance(learned_kept, opt)
            for opt in audit["stored_global_optima"]
        ]
        min_distance = min(distances) if distances else None

        total_gap += gap
        max_gap = max(max_gap, gap)
        total_states += audit["states_enumerated"]
        total_r3 += len(graph["round3_ids"])
        if min_distance is not None:
            max_distance = max(max_distance, min_distance)
        v73_global_matches += int(gap == 0)

        rec = {
            "index": index,
            "source_key": graph["source_key"],
            "round1_pool_size": audit["round1_pool_size"],
            "round2_pool_size": len(graph["round2_ids"]),
            "round3_pool_size": len(graph["round3_ids"]),
            "states_enumerated": audit["states_enumerated"],
            "v73_retained": learned_kept,
            "v73_round2_local_optimum_certified": learned["local_optimum_certified"],
            "v73_deep_closure_size": learned_deep,
            "global_best_deep_closure_size": global_deep,
            "deep_global_optimality_gap": gap,
            "minimum_swap_distance_to_stored_deep_global_optimum": min_distance,
            "stored_deep_global_optimum_count": len(audit["stored_global_optima"]),
            "stored_deep_global_optima": audit["stored_global_optima"],
        }
        records.append(rec)

        print(json.dumps({
            "phase": "DEEP_AUDIT_V75",
            "index": index,
            "source": graph["source_key"][:12],
            "r1": audit["round1_pool_size"],
            "r2": len(graph["round2_ids"]),
            "r3": len(graph["round3_ids"]),
            "v73_deep": learned_deep,
            "global_deep": global_deep,
            "gap": gap,
            "distance": min_distance,
            "states": audit["states_enumerated"],
        }, sort_keys=True), flush=True)

    all_global = v73_global_matches == len(records)
    obstruction_exists = not all_global

    checks = {
        "v73_source_stream_reproduced": len(records) == V73.FRESH_SOURCE_COUNT,
        "developer_hash_exact": developer_hash == V73.AUTHORITATIVE_V72_DEVELOPER_SHA256,
        "all_round3_nodes_exactly_replayed": True,
        "every_fixed_budget_state_enumerated": all(
            r["states_enumerated"] == math.comb(r["round1_pool_size"], RETAINED_BUDGET)
            for r in records
        ),
        "v73_states_still_round2_local_optima": all(
            r["v73_round2_local_optimum_certified"] for r in records
        ),
    }

    result = {
        "schema": "mathgraph.deep-closure-optimality-audit.v75",
        "classification": "POSTHOC_EXACT_DEPTH3_EXPANSION_AUDIT",
        "developer_sha256": developer_hash,
        "v73_source_seed": V73.FRESH_STREAM_SEED,
        "retained_budget": RETAINED_BUDGET,
        "round3_pool_cap": ROUND3_POOL,
        "sources": len(records),
        "total_round3_nodes": total_r3,
        "total_states_enumerated": total_states,
        "v73_depth3_global_matches": v73_global_matches,
        "total_depth3_global_optimality_gap": total_gap,
        "max_depth3_global_optimality_gap": max_gap,
        "max_minimum_swap_distance_to_depth3_global_optimum": max_distance,
        "depth3_expansion_obstruction_exists": obstruction_exists,
        "records": records,
        "checks": checks,
        "audit_valid": all(checks.values()),
        "verdict": (
            "PASS_V73_REMAINS_GLOBAL_DEPTH3_OPTIMUM_V75"
            if all(checks.values()) and all_global
            else (
                "PASS_CERTIFIED_DEPTH3_EXPANSION_OBSTRUCTION_V75"
                if all(checks.values()) and obstruction_exists
                else "FAIL_DEPTH3_OPTIMALITY_AUDIT_V75"
            )
        ),
        "claim_boundary": (
            "V75 is a post-hoc exact audit on the now-opened V73 synthetic sources. "
            "It expands only the consequence horizon to a deterministic replay-verified "
            "round-3 pool of at most 144 nodes while keeping the same fixed round-1 "
            "retention budget. A global-match verdict certifies exhaustion only for this "
            "depth-3 closure objective; an obstruction verdict certifies that deeper "
            "consequence compounding changes the globally optimal retained capability set."
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
        "total_round3_nodes": total_r3,
        "total_states_enumerated": total_states,
        "global_matches": v73_global_matches,
        "total_gap": total_gap,
        "max_gap": max_gap,
        "max_distance": max_distance,
        "obstruction_exists": obstruction_exists,
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
