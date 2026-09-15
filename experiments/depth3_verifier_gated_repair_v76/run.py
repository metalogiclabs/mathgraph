#!/usr/bin/env python3
"""V76: minimal verifier-horizon expansion repair after V75.

V74 certified the V73 retained states globally optimal for the round-2 frontier.
V75 then certified that depth-3 consequence compounding changes the global
optimum on 11/16 sources.

V76 changes exactly one thing: the admission potential.

State and action language remain unchanged:
    K = exactly 5 retained round-1 capabilities
    action = one swap K' = K - d + a

Old verifier:
    Phi_2(K) = reachable replay-verified round-2 consequences

Expanded verifier:
    Phi_3(K) = reachable replay-verified round-2 + round-3 consequence closure

Starting from the persistent V73 state, admit a swap iff Phi_3 strictly
increases. Repeat until a complete scan finds no positive one-swap repair.
Compare learned V72 proposal ordering, generic ordering, exhaustive
best-improvement, and the exact global depth-3 optimum from complete state
enumeration.

This is a post-hoc repair audit on already-opened V73 sources.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P75 = ROOT / "experiments" / "deep_closure_optimality_audit_v75" / "run.py"
S75 = importlib.util.spec_from_file_location("v76_v75", P75)
if S75 is None or S75.loader is None:
    raise RuntimeError("cannot load V75")
V75 = importlib.util.module_from_spec(S75)
sys.modules[S75.name] = V75
S75.loader.exec_module(V75)

V73 = V75.V73
V72 = V75.V72
V71 = V75.V71

VERIFY_BATCH = 4
MAX_STEPS = 10


def deep_actions(graph, retained):
    retained = tuple(sorted(retained))
    retained_set = set(retained)
    current = V75.deep_reachable(graph, retained)
    shallow_current = V71.reachable_children(graph, retained)
    omitted = [eid for eid in graph["round1_ids"] if eid not in retained_set]

    actions = []
    for drop_id in retained:
        for add_id in omitted:
            nxt = tuple(sorted((retained_set - {drop_id}) | {add_id}))
            frontier = V75.deep_reachable(graph, nxt)
            actions.append({
                "drop_id": int(drop_id),
                "add_id": int(add_id),
                "next_retained": nxt,
                "frontier": frontier,
                "gain_ids": frontier - current,
                "loss_ids": current - frontier,
                "utility": len(frontier) - len(current),
                # Keep the frozen V72 proposal representation unchanged.
                "features": V72.swap_features(
                    graph, retained, drop_id, add_id, shallow_current
                ),
            })
    return current, actions


def best_action(actions):
    return max(
        actions,
        key=lambda a: (
            a["utility"],
            len(a["gain_ids"]),
            -len(a["loss_ids"]),
            -a["add_id"],
            a["drop_id"],
        ),
    )


def exhaustive_deep_trajectory(graph, start):
    retained = tuple(sorted(start))
    initial = V75.deep_reachable(graph, retained)
    checks = 0
    steps = []

    for _ in range(MAX_STEPS):
        current, actions = deep_actions(graph, retained)
        checks += len(actions)
        if not actions:
            return retained, current, steps, checks, True
        best = best_action(actions)
        if best["utility"] <= 0:
            return retained, current, steps, checks, True
        steps.append(best)
        retained = best["next_retained"]

    current, actions = deep_actions(graph, retained)
    checks += len(actions)
    return (
        retained,
        current,
        steps,
        checks,
        all(a["utility"] <= 0 for a in actions),
    )


def gated_deep_trajectory(graph, start, mode, developer):
    retained = tuple(sorted(start))
    initial = V75.deep_reachable(graph, retained)
    checks = 0
    steps = []
    causal_examples = []

    for _ in range(MAX_STEPS):
        current, actions = deep_actions(graph, retained)
        if not actions:
            return {
                "start_frontier": initial,
                "final_retained": retained,
                "final_frontier": current,
                "steps": steps,
                "checks": checks,
                "local_optimum": True,
                "causal_examples": causal_examples,
            }

        if mode == "learned":
            ordered = sorted(
                actions,
                key=lambda a: (
                    -V72.learned_score(a, developer),
                    a["drop_id"],
                    a["add_id"],
                ),
            )
        elif mode == "generic":
            ordered = sorted(actions, key=lambda a: V72.generic_key(graph, a))
        else:
            raise ValueError(mode)

        accepted = None
        for i in range(0, len(ordered), VERIFY_BATCH):
            batch = ordered[i:i + VERIFY_BATCH]
            checks += len(batch)
            positives = [a for a in batch if a["utility"] > 0]
            if positives:
                accepted = best_action(positives)
                break

        if accepted is None:
            return {
                "start_frontier": initial,
                "final_retained": retained,
                "final_frontier": current,
                "steps": steps,
                "checks": checks,
                "local_optimum": True,
                "causal_examples": causal_examples,
            }

        if accepted["gain_ids"]:
            child = min(accepted["gain_ids"])
            causal_examples.append({
                "child_id": int(child),
                "drop_id": accepted["drop_id"],
                "add_id": accepted["add_id"],
                "reachable_before": child in current,
                "reachable_after": child in accepted["frontier"],
                "causal_new_reach": (
                    child not in current and child in accepted["frontier"]
                ),
            })

        steps.append(accepted)
        retained = accepted["next_retained"]

    current, actions = deep_actions(graph, retained)
    checks += len(actions)
    return {
        "start_frontier": initial,
        "final_retained": retained,
        "final_frontier": current,
        "steps": steps,
        "checks": checks,
        "local_optimum": all(a["utility"] <= 0 for a in actions),
        "causal_examples": causal_examples,
    }


def summary(traj):
    return {
        "start_deep_closure": len(traj["start_frontier"]),
        "final_deep_closure": len(traj["final_frontier"]),
        "gain": len(traj["final_frontier"]) - len(traj["start_frontier"]),
        "steps": len(traj["steps"]),
        "checks": traj["checks"],
        "local_optimum": traj["local_optimum"],
        "all_steps_positive": all(s["utility"] > 0 for s in traj["steps"]),
        "causal_examples": traj["causal_examples"],
        "step_records": [
            {
                "drop_id": s["drop_id"],
                "add_id": s["add_id"],
                "utility": s["utility"],
                "gain_count": len(s["gain_ids"]),
                "loss_count": len(s["loss_ids"]),
            }
            for s in traj["steps"]
        ],
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
    if developer_hash != V73.AUTHORITATIVE_V72_DEVELOPER_SHA256:
        raise RuntimeError("developer drift before V76")

    bases, _fresh_sources = V73.generate_fresh_graphs()
    graphs = [V75.extend_round3(g) for g in bases]

    records = []
    learned_global = 0
    generic_global = 0
    oracle_global = 0
    learned_checks = 0
    generic_checks = 0
    oracle_checks = 0
    learned_gain = 0
    generic_gain = 0
    causal = 0

    for index, graph in enumerate(graphs, 1):
        # Persistent state inherited from the V73 round-2 optimum.
        v73 = V72.gated_trajectory(graph, "learned", developer)
        start = tuple(sorted(v73["final_retained"]))

        global_audit = V75.exact_global_deep_optimum(graph)
        global_size = global_audit["global_best_deep_closure_size"]

        learned = gated_deep_trajectory(graph, start, "learned", developer)
        generic = gated_deep_trajectory(graph, start, "generic", developer)

        o_ret, o_front, o_steps, o_checks, o_local = (
            exhaustive_deep_trajectory(graph, start)
        )
        oracle = {
            "start_frontier": V75.deep_reachable(graph, start),
            "final_retained": o_ret,
            "final_frontier": o_front,
            "steps": o_steps,
            "checks": o_checks,
            "local_optimum": o_local,
            "causal_examples": [],
        }

        ls = summary(learned)
        gs = summary(generic)
        os = summary(oracle)

        ls["global_optimality_gap"] = global_size - ls["final_deep_closure"]
        gs["global_optimality_gap"] = global_size - gs["final_deep_closure"]
        os["global_optimality_gap"] = global_size - os["final_deep_closure"]

        learned_global += int(ls["global_optimality_gap"] == 0)
        generic_global += int(gs["global_optimality_gap"] == 0)
        oracle_global += int(os["global_optimality_gap"] == 0)
        learned_checks += ls["checks"]
        generic_checks += gs["checks"]
        oracle_checks += os["checks"]
        learned_gain += ls["gain"]
        generic_gain += gs["gain"]
        causal += sum(
            int(x["causal_new_reach"]) for x in ls["causal_examples"]
        )

        records.append({
            "index": index,
            "source_key": graph["source_key"],
            "v73_start_retained": start,
            "v73_start_deep_closure": len(V75.deep_reachable(graph, start)),
            "global_best_deep_closure": global_size,
            "learned": ls,
            "generic": gs,
            "oracle": os,
        })

        print(json.dumps({
            "phase": "DEPTH3_REPAIR_V76",
            "index": index,
            "source": graph["source_key"][:12],
            "start": len(V75.deep_reachable(graph, start)),
            "global": global_size,
            "learned": ls["final_deep_closure"],
            "generic": gs["final_deep_closure"],
            "oracle": os["final_deep_closure"],
            "learned_gap": ls["global_optimality_gap"],
            "learned_checks": ls["checks"],
            "generic_checks": gs["checks"],
        }, sort_keys=True), flush=True)

    checks = {
        "developer_hash_exact": developer_hash == V73.AUTHORITATIVE_V72_DEVELOPER_SHA256,
        "state_budget_unchanged": V71.RETAIN_BUDGET == 5,
        "action_grammar_unchanged_one_swap": True,
        "only_admission_potential_expanded_to_depth3": True,
        "every_learned_step_strictly_improves_depth3": all(
            r["learned"]["all_steps_positive"] for r in records
        ),
        "every_learned_final_state_depth3_local_optimum": all(
            r["learned"]["local_optimum"] for r in records
        ),
        "learned_reaches_all_depth3_global_optima": learned_global == len(records),
        "learned_uses_no_more_checks_than_generic": learned_checks <= generic_checks,
        "causal_new_depth3_reach_exists": causal > 0,
    }
    passed = all(checks.values())

    result = {
        "schema": "mathgraph.depth3-verifier-gated-repair.v76",
        "classification": "POSTHOC_MINIMAL_HORIZON_EXPANSION_REPAIR",
        "developer_sha256": developer_hash,
        "sources": len(records),
        "learned_global_matches": learned_global,
        "generic_global_matches": generic_global,
        "oracle_global_matches": oracle_global,
        "learned_total_gain": learned_gain,
        "generic_total_gain": generic_gain,
        "learned_total_checks": learned_checks,
        "generic_total_checks": generic_checks,
        "oracle_total_checks": oracle_checks,
        "causal_new_reach_examples": causal,
        "records": records,
        "checks": checks,
        "all_v76_gates_pass": passed,
        "verdict": (
            "PASS_MINIMAL_DEPTH3_VERIFIER_EXPANSION_REPAIR_V76"
            if passed
            else "FAIL_MINIMAL_DEPTH3_VERIFIER_EXPANSION_REPAIR_V76"
        ),
        "claim_boundary": (
            "A PASS shows that V75's certified depth-3 obstruction can be repaired "
            "without changing retained budget or one-swap action grammar: expanding "
            "only the exact admission potential from round-2 reach to depth-3 closure "
            "recovers every globally optimal depth-3 retained state on the opened V73 "
            "sources. The learned V72 ordering is reused unchanged as proposal order; "
            "all admissions remain exact-verifier gated."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))

    print(json.dumps({
        "verdict": result["verdict"],
        "sources": len(records),
        "learned_global_matches": learned_global,
        "generic_global_matches": generic_global,
        "oracle_global_matches": oracle_global,
        "learned_total_gain": learned_gain,
        "generic_total_gain": generic_gain,
        "learned_total_checks": learned_checks,
        "generic_total_checks": generic_checks,
        "oracle_total_checks": oracle_checks,
        "causal_new_reach_examples": causal,
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
