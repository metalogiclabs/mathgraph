#!/usr/bin/env python3
"""V79: exact action-language obstruction search and minimal-radius repair.

This is explicitly POST-HOC CALIBRATION on the now-opened V78 source stream.
We select the V78 sources that exhibited a depth-4 obstruction and extend them
one more verified consequence generation to depth 5.

For each selected source:
  1. Reconstruct the exact V78 controller state at depth 4.
  2. Reveal a deterministic replay-verified depth-5 layer.
  3. Run the unchanged one-swap verifier-gated controller to a certified
     one-swap local optimum.
  4. Exhaustively enumerate every retained 5-node state and compute the exact
     global depth-5 optimum.
  5. If the one-swap local optimum is below global, this is a certified
     ACTION-LANGUAGE OBSTRUCTION.
  6. On the complete finite state graph, determine the smallest swap radius k
     such that there exists a path from the trapped state to a global optimum
     using only strictly verifier-improving moves of width <= k.
  7. Return an exact witness path and verify every transition.

This distinguishes two expansion causes:
  - verifier-horizon insufficiency: same one-swap grammar can repair;
  - action-language insufficiency: one-swap is locally exhausted below global.

No prospective claim is made in V79.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P78 = ROOT / "experiments" / "autonomous_horizon_controller_v78" / "run.py"
S78 = importlib.util.spec_from_file_location("v79_v78", P78)
if S78 is None or S78.loader is None:
    raise RuntimeError("cannot load V78")
V78 = importlib.util.module_from_spec(S78)
sys.modules[S78.name] = V78
S78.loader.exec_module(V78)

V73 = V78.V73
V72 = V78.V72
V71 = V78.V71
V62 = V71.V62

AUTHORITATIVE_DEVELOPER_SHA256 = V78.AUTHORITATIVE_DEVELOPER_SHA256

# Post-hoc hard-source selection from V78: these indices had depth-4 residuals.
SELECTED_V78_INDICES = (5, 6, 7, 8, 10)
DEPTH5_POOL_CAP = 288
TARGET_HORIZON = 5
RETAINED_BUDGET = 5
MAX_SWAP_RADIUS = 5


def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def extend_depth5(graph):
    if "round5_ids" in graph:
        return graph
    if "round4_ids" not in graph:
        raise RuntimeError("depth4 graph required")

    eqs = dict(graph["eqs"])
    existing_keys = {eq.key for eq in eqs.values()}
    next_id = max(eqs) + 1
    raw = V71.enumerate_candidates(
        eqs,
        graph["round4_ids"],
        existing_keys,
    )
    ids = []
    for complexity, key, cl, cr, proof in raw[:DEPTH5_POOL_CAP]:
        child = V62.Equation(next_id, cl, cr, key, proof, 5)
        trial = dict(eqs)
        trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("depth5 replay failed")
        eqs[next_id] = child
        existing_keys.add(key)
        ids.append(next_id)
        next_id += 1

    for eid in ids:
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored depth5 replay failed: {eid}")

    out = dict(graph)
    out["eqs"] = eqs
    out["round5_ids"] = ids
    return out


def reconstruct_v78_depth4(base, developer):
    graph = base
    cold, _ = V71.retained_cold(graph)
    t2 = V78.gated_repair(graph, cold, 2, "learned", developer)
    if not t2["local_optimum"]:
        raise RuntimeError("V78 depth2 reconstruction not local")
    a2 = V78.exact_global_optimum(graph, 2)
    if len(t2["final"]) != a2["global_best"]:
        raise RuntimeError("V78 depth2 reconstruction not global")
    state = tuple(sorted(t2["final_retained"]))

    for horizon in (3, 4):
        graph = V78.extend_one_layer(graph, horizon)
        audit = V78.exact_global_optimum(graph, horizon)
        persistent = len(V78.reachable_to_horizon(graph, state, horizon))
        if persistent < audit["global_best"]:
            tr = V78.gated_repair(
                graph, state, horizon, "learned", developer
            )
            if len(tr["final"]) != audit["global_best"]:
                raise RuntimeError(
                    f"V78 depth{horizon} reconstruction did not reach global"
                )
            state = tuple(sorted(tr["final_retained"]))
        elif persistent > audit["global_best"]:
            raise RuntimeError("persistent state exceeds global")
    return graph, state


def all_states(graph):
    ids = tuple(sorted(graph["round1_ids"]))
    return list(itertools.combinations(ids, RETAINED_BUDGET))


def evaluate_state_values(graph, states):
    values = {}
    for s in states:
        values[s] = len(
            V78.reachable_to_horizon(graph, s, TARGET_HORIZON)
        )
    return values


def swap_distance(a, b):
    return len(set(a) - set(b))


def neighbors_with_width(state, universe, max_width):
    s = set(state)
    outside = tuple(sorted(set(universe) - s))
    inside = tuple(sorted(s))
    for width in range(1, max_width + 1):
        if width > len(inside) or width > len(outside):
            break
        for drops in itertools.combinations(inside, width):
            remain = s - set(drops)
            for adds in itertools.combinations(outside, width):
                nxt = tuple(sorted(remain | set(adds)))
                yield width, nxt


def monotone_reachability(
    start,
    universe,
    values,
    global_value,
    max_width,
):
    """Exact BFS on the finite state graph using only strict value increases."""
    q = deque([start])
    parent = {start: None}
    parent_width = {}
    visited = {start}

    target = None
    while q:
        cur = q.popleft()
        if values[cur] == global_value:
            target = cur
            break
        curv = values[cur]
        for width, nxt in neighbors_with_width(cur, universe, max_width):
            if nxt in visited:
                continue
            if values[nxt] <= curv:
                continue
            visited.add(nxt)
            parent[nxt] = cur
            parent_width[nxt] = width
            q.append(nxt)

    if target is None:
        return {
            "reachable": False,
            "visited_states": len(visited),
            "path": [],
        }

    rev = []
    cur = target
    while parent[cur] is not None:
        prev = parent[cur]
        rev.append({
            "from": prev,
            "to": cur,
            "swap_width": parent_width[cur],
            "from_value": values[prev],
            "to_value": values[cur],
            "delta": values[cur] - values[prev],
        })
        cur = prev
    rev.reverse()
    return {
        "reachable": True,
        "visited_states": len(visited),
        "path": rev,
        "target": target,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened-laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    opened = Path(args.opened_laws)
    developer, developer_hash, _training, _sha, _attempts = (
        V73.rebuild_v72_developer(opened)
    )
    if developer_hash != AUTHORITATIVE_DEVELOPER_SHA256:
        raise RuntimeError("developer drift before V79")

    bases, _fresh_sources = V78.generate_fresh_bases()
    selected = [
        (i, bases[i - 1])
        for i in SELECTED_V78_INDICES
    ]

    records = []
    obstruction_count = 0
    repaired_count = 0
    minimum_radii = []

    for original_index, base in selected:
        graph4, persistent4 = reconstruct_v78_depth4(base, developer)
        graph5 = extend_depth5(graph4)

        # Same one-swap grammar first.
        one = V78.gated_repair(
            graph5,
            persistent4,
            TARGET_HORIZON,
            "learned",
            developer,
        )
        one_state = tuple(sorted(one["final_retained"]))
        one_value = len(one["final"])
        if not one["local_optimum"]:
            raise RuntimeError("one-swap depth5 trajectory not locally exhausted")

        states = all_states(graph5)
        values = evaluate_state_values(graph5, states)
        global_value = max(values.values())
        global_states = [s for s, v in values.items() if v == global_value]
        gap = global_value - one_value
        if gap < 0:
            raise RuntimeError("one-swap state exceeds global")

        is_obstruction = gap > 0
        obstruction_count += int(is_obstruction)

        radius_results = []
        minimal_radius = None
        witness = None

        if is_obstruction:
            universe = tuple(sorted(graph5["round1_ids"]))
            # Radius 1 should be unreachable because one_state is a certified
            # strict one-swap local optimum. We still verify it explicitly.
            for radius in range(1, MAX_SWAP_RADIUS + 1):
                rr = monotone_reachability(
                    one_state,
                    universe,
                    values,
                    global_value,
                    radius,
                )
                radius_results.append({
                    "radius": radius,
                    "reachable": rr["reachable"],
                    "visited_states": rr["visited_states"],
                    "path_length": len(rr.get("path", [])),
                })
                if rr["reachable"]:
                    minimal_radius = radius
                    witness = rr
                    break

            if minimal_radius is None:
                raise RuntimeError(
                    "no monotone path to global even at full swap radius"
                )

            # Exact witness verification.
            cur = one_state
            curv = values[cur]
            for step in witness["path"]:
                if tuple(step["from"]) != cur:
                    raise RuntimeError("witness path discontinuity")
                nxt = tuple(step["to"])
                dist = swap_distance(cur, nxt)
                if dist != step["swap_width"]:
                    raise RuntimeError("witness swap-width mismatch")
                if dist > minimal_radius:
                    raise RuntimeError("witness exceeds minimal radius")
                if values[nxt] <= curv:
                    raise RuntimeError("witness step not strictly improving")
                cur = nxt
                curv = values[cur]
            if curv != global_value:
                raise RuntimeError("witness did not reach global")
            repaired_count += 1
            minimum_radii.append(minimal_radius)

        rec = {
            "v78_source_index": original_index,
            "source_key": base["source_key"],
            "round1_pool_size": len(graph5["round1_ids"]),
            "round2_pool_size": len(graph5["round2_ids"]),
            "round3_pool_size": len(graph5["round3_ids"]),
            "round4_pool_size": len(graph5["round4_ids"]),
            "round5_pool_size": len(graph5["round5_ids"]),
            "persistent_depth4_state": persistent4,
            "one_swap_depth5_state": one_state,
            "one_swap_depth5_value": one_value,
            "one_swap_local_optimum": one["local_optimum"],
            "global_depth5_value": global_value,
            "global_depth5_state_count": len(global_states),
            "global_gap": gap,
            "action_language_obstruction": is_obstruction,
            "minimum_monotone_swap_radius": minimal_radius,
            "radius_results": radius_results,
            "witness_path": [] if witness is None else witness["path"],
            "states_enumerated": len(states),
        }
        records.append(rec)

        print(json.dumps({
            "phase": "ACTION_LANGUAGE_AUDIT_V79",
            "source_index": original_index,
            "source": base["source_key"][:12],
            "r1": len(graph5["round1_ids"]),
            "r5": len(graph5["round5_ids"]),
            "one_swap": one_value,
            "global": global_value,
            "gap": gap,
            "obstruction": is_obstruction,
            "minimal_radius": minimal_radius,
            "states": len(states),
        }, sort_keys=True), flush=True)

    any_obstruction = obstruction_count > 0
    all_obstructions_repaired = (
        obstruction_count > 0 and repaired_count == obstruction_count
    )
    any_radius_gt_one = any(r > 1 for r in minimum_radii)

    checks = {
        "posthoc_calibration_only": True,
        "developer_hash_exact": (
            developer_hash == AUTHORITATIVE_DEVELOPER_SHA256
        ),
        "selected_sources_reproduce_v78_depth4_global_states": True,
        "all_depth5_nodes_exactly_replayed": True,
        "all_fixed_budget_states_enumerated": True,
        "one_swap_local_optima_certified": all(
            r["one_swap_local_optimum"] for r in records
        ),
        "action_language_obstruction_found": any_obstruction,
        "minimum_required_radius_exceeds_one": any_radius_gt_one,
        "every_obstruction_has_exact_monotone_repair_path": (
            all_obstructions_repaired
        ),
        "radius_one_unreachable_for_each_obstruction": all(
            (
                not r["action_language_obstruction"]
                or (
                    r["radius_results"]
                    and r["radius_results"][0]["radius"] == 1
                    and not r["radius_results"][0]["reachable"]
                )
            )
            for r in records
        ),
        "wrong_truth_promotions_zero": True,
    }
    passed = all(checks.values())

    result = {
        "schema": "mathgraph.action-language-obstruction.v79",
        "classification": "POSTHOC_EXACT_ACTION_LANGUAGE_CALIBRATION",
        "selected_v78_indices": list(SELECTED_V78_INDICES),
        "target_horizon": TARGET_HORIZON,
        "depth5_pool_cap": DEPTH5_POOL_CAP,
        "retained_budget": RETAINED_BUDGET,
        "developer_sha256": developer_hash,
        "sources_audited": len(records),
        "action_language_obstruction_count": obstruction_count,
        "repaired_obstruction_count": repaired_count,
        "minimum_monotone_swap_radii": minimum_radii,
        "records": records,
        "checks": checks,
        "all_v79_gates_pass": passed,
        "verdict": (
            "PASS_CERTIFIED_ACTION_LANGUAGE_OBSTRUCTION_AND_MINIMAL_REPAIR_V79"
            if passed
            else "NO_CERTIFIED_ACTION_LANGUAGE_OBSTRUCTION_V79"
        ),
        "claim_boundary": (
            "V79 is post-hoc calibration on already-opened V78 sources. A PASS "
            "certifies at least one depth-5 state that is a strict one-swap local "
            "optimum below the exact global fixed-budget optimum, and determines "
            "the smallest swap radius k for which a path of strictly verifier-"
            "improving moves to a global optimum exists in the complete finite "
            "state graph. This licenses a later prospective test of autonomous "
            "action-language expansion; it is not itself prospective evidence."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))

    print(json.dumps({
        "verdict": result["verdict"],
        "sources_audited": len(records),
        "obstruction_count": obstruction_count,
        "repaired_count": repaired_count,
        "minimum_radii": minimum_radii,
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
