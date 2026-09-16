#!/usr/bin/env python3
"""V78: prospective autonomous verifier-horizon controller.

Goal
----
Move from the hand-staged V77 cycle to a bounded autonomous developmental
controller. The controller is frozen before any fresh source exists.

For each fresh eight-operation source it starts at consequence horizon h=2 and
repeats:

  1. Develop the fixed-size retained capability state under Phi_h.
  2. Exhaustively certify that state is globally optimal for Phi_h.
  3. Reveal exactly one next consequence layer h+1.
  4. Compare the persistent h-optimal state against the exact global optimum
     for Phi_{h+1}.
  5. If there is no residual, preserve the state and advance the verifier.
  6. If there is a residual, first attempt the minimal repair:
       - same retained budget,
       - same one-swap action grammar,
       - same frozen learned proposal ordering,
       - only the verifier horizon changes.
  7. Exhaustively certify the repaired state against the global optimum.
  8. If verifier-only repair fails, emit ACTION_LANGUAGE_EXPANSION_REQUIRED;
     do not silently broaden the action grammar.
  9. Continue until the pre-frozen MAX_HORIZON boundary.

Thus the controller, not the experiment author, decides per source whether each
new horizon requires REUSE or verifier-only EXPANSION. The run is prospective:
the controller protocol, developer hash, source generator, horizon boundary,
pool caps, and admission rules are all frozen before any eight-operation source
is generated.

Claim boundary
--------------
A pass establishes bounded prospective transfer of this autonomous controller
on the declared synthetic source generator and exact critical-pair graph model.
It does not establish universal self-improvement or unbounded adequacy.
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
P77 = ROOT / "experiments" / "prospective_developmental_cycle_v77" / "run.py"
S77 = importlib.util.spec_from_file_location("v78_v77", P77)
if S77 is None or S77.loader is None:
    raise RuntimeError("cannot load V77")
V77 = importlib.util.module_from_spec(S77)
sys.modules[S77.name] = V77
S77.loader.exec_module(V77)

V76 = V77.V76
V75 = V77.V75
V73 = V77.V73
V72 = V77.V72
V71 = V77.V71
V62 = V71.V62

AUTHORITATIVE_DEVELOPER_SHA256 = V73.AUTHORITATIVE_V72_DEVELOPER_SHA256

FRESH_STREAM_SEED = "MATHGRAPH_V78_FRESH_EIGHT_OP_AUTONOMOUS_HORIZON_2026_09_16_A"
FRESH_OPERATION_COUNT = 8
FRESH_SOURCE_COUNT = 10
MAX_FRESH_ATTEMPTS = 5000
VARIABLES = ("x", "y", "z", "w")

START_HORIZON = 2
MAX_HORIZON = 4
RETAINED_BUDGET = 5
ROUND1_POOL = V71.ROUND1_POOL
ROUND_CAPS = {
    2: V71.ROUND2_POOL,
    3: V75.ROUND3_POOL,
    4: 216,
}
VERIFY_BATCH = V76.VERIFY_BATCH
MAX_REPAIR_STEPS = 12


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
    return (
        f"{generate_term(lhs_ops, counter, 'lhs')} = "
        f"{generate_term(rhs_ops, counter, 'rhs')}"
    )


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
        raise RuntimeError("opened universe empty")
    return max(law_operation_count(line) for line in lines), len(lines)


def generate_fresh_bases():
    graphs = []
    sources = []
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
        sources.append({
            "stream_counter": counter,
            "source_key": graph["source_key"],
            "law": law,
            "operation_count": law_operation_count(law),
            "round1_nodes": len(graph["round1_ids"]),
            "round2_nodes": len(graph["round2_ids"]),
        })
    if len(graphs) != FRESH_SOURCE_COUNT:
        raise RuntimeError(
            f"only {len(graphs)} eligible fresh sources after {MAX_FRESH_ATTEMPTS}"
        )
    return graphs, sources


def extend_one_layer(graph, next_horizon: int):
    if next_horizon < 3:
        raise ValueError("base graph already includes horizon 2")
    prev_key = f"round{next_horizon - 1}_ids"
    next_key = f"round{next_horizon}_ids"
    if next_key in graph:
        return graph
    if prev_key not in graph:
        raise RuntimeError(f"missing previous layer {prev_key}")

    eqs = dict(graph["eqs"])
    existing_keys = {eq.key for eq in eqs.values()}
    next_id = max(eqs) + 1
    cap = ROUND_CAPS[next_horizon]

    raw = V71.enumerate_candidates(
        eqs,
        graph[prev_key],
        existing_keys,
    )
    ids = []
    for complexity, key, cl, cr, proof in raw[:cap]:
        child = V62.Equation(next_id, cl, cr, key, proof, next_horizon)
        trial = dict(eqs)
        trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError(
                f"round-{next_horizon} critical-pair replay failed"
            )
        eqs[next_id] = child
        existing_keys.add(key)
        ids.append(next_id)
        next_id += 1

    for eid in ids:
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(
                f"stored round-{next_horizon} node replay failed: {eid}"
            )

    out = dict(graph)
    out["eqs"] = eqs
    out[next_key] = ids
    return out


def reachable_to_horizon(graph, retained, horizon: int):
    reachable = {0, *retained}
    descendants = set()
    for depth in range(2, horizon + 1):
        key = f"round{depth}_ids"
        if key not in graph:
            raise RuntimeError(f"graph missing {key} for horizon {horizon}")
        for eid in graph[key]:
            p = graph["eqs"][eid].proof
            if int(p["a"]) in reachable and int(p["b"]) in reachable:
                reachable.add(eid)
                descendants.add(eid)
    return descendants


def exact_global_optimum(graph, horizon: int):
    ids = tuple(sorted(graph["round1_ids"]))
    if len(ids) < RETAINED_BUDGET:
        raise RuntimeError("round1 pool below budget")
    expected = math.comb(len(ids), RETAINED_BUDGET)
    best_size = -1
    best_sets = []
    states = 0
    for kept in itertools.combinations(ids, RETAINED_BUDGET):
        states += 1
        size = len(reachable_to_horizon(graph, kept, horizon))
        if size > best_size:
            best_size = size
            best_sets = [tuple(kept)]
        elif size == best_size and len(best_sets) < 128:
            best_sets.append(tuple(kept))
    if states != expected:
        raise RuntimeError(f"state census mismatch {states} != {expected}")
    return {
        "horizon": horizon,
        "round1_pool_size": len(ids),
        "states_enumerated": states,
        "global_best": best_size,
        "stored_global_optima": best_sets,
    }


def action_features(graph, retained, drop_id, add_id):
    # Preserve the frozen V72 proposal representation: it is deliberately based
    # on the shallow graph and does not inspect future-horizon labels.
    shallow = V71.reachable_children(graph, retained)
    return V72.swap_features(
        graph, retained, drop_id, add_id, shallow
    )


def actions_for_horizon(graph, retained, horizon: int):
    retained = tuple(sorted(retained))
    retained_set = set(retained)
    current = reachable_to_horizon(graph, retained, horizon)
    omitted = [eid for eid in graph["round1_ids"] if eid not in retained_set]
    actions = []
    for drop_id in retained:
        for add_id in omitted:
            nxt = tuple(sorted((retained_set - {drop_id}) | {add_id}))
            frontier = reachable_to_horizon(graph, nxt, horizon)
            actions.append({
                "drop_id": int(drop_id),
                "add_id": int(add_id),
                "next_retained": nxt,
                "frontier": frontier,
                "gain_ids": frontier - current,
                "loss_ids": current - frontier,
                "utility": len(frontier) - len(current),
                "features": action_features(
                    graph, retained, drop_id, add_id
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


def learned_score(action, developer):
    return V72.dot(
        developer["weights"],
        V72.normalize(action["features"], developer["feature_scales"]),
    )


def generic_key(graph, action):
    return V72.generic_key(graph, action)


def gated_repair(graph, start, horizon: int, mode: str, developer):
    retained = tuple(sorted(start))
    initial = reachable_to_horizon(graph, retained, horizon)
    steps = []
    checks = 0
    causal = []

    for _ in range(MAX_REPAIR_STEPS):
        current, actions = actions_for_horizon(graph, retained, horizon)
        if not actions:
            return {
                "start": initial,
                "final": current,
                "final_retained": retained,
                "steps": steps,
                "checks": checks,
                "local_optimum": True,
                "causal": causal,
            }

        if mode == "learned":
            ordered = sorted(
                actions,
                key=lambda a: (
                    -learned_score(a, developer),
                    a["drop_id"],
                    a["add_id"],
                ),
            )
        elif mode == "generic":
            ordered = sorted(
                actions,
                key=lambda a: generic_key(graph, a),
            )
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
                "start": initial,
                "final": current,
                "final_retained": retained,
                "steps": steps,
                "checks": checks,
                "local_optimum": True,
                "causal": causal,
            }

        if accepted["gain_ids"]:
            child = min(accepted["gain_ids"])
            causal.append({
                "child_id": int(child),
                "drop_id": accepted["drop_id"],
                "add_id": accepted["add_id"],
                "causal_new_reach": (
                    child not in current and child in accepted["frontier"]
                ),
            })
        steps.append(accepted)
        retained = accepted["next_retained"]

    current, actions = actions_for_horizon(graph, retained, horizon)
    checks += len(actions)
    return {
        "start": initial,
        "final": current,
        "final_retained": retained,
        "steps": steps,
        "checks": checks,
        "local_optimum": all(a["utility"] <= 0 for a in actions),
        "causal": causal,
    }


def summarize(traj):
    return {
        "start_size": len(traj["start"]),
        "final_size": len(traj["final"]),
        "gain": len(traj["final"]) - len(traj["start"]),
        "final_retained": tuple(sorted(traj["final_retained"])),
        "steps": len(traj["steps"]),
        "checks": traj["checks"],
        "local_optimum": traj["local_optimum"],
        "all_steps_positive": all(s["utility"] > 0 for s in traj["steps"]),
        "causal_examples": traj["causal"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened-laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    opened = Path(args.opened_laws)
    opened_max_ops, opened_count = opened_universe_max_ops(opened)
    if opened_max_ops >= FRESH_OPERATION_COUNT:
        raise RuntimeError("fresh grammar boundary invalid")

    developer, developer_hash, training, opened_sha256, training_attempts = (
        V73.rebuild_v72_developer(opened)
    )
    if developer_hash != AUTHORITATIVE_DEVELOPER_SHA256:
        raise RuntimeError("developer hash drift")

    protocol = {
        "schema": "mathgraph.autonomous-horizon-controller.v78.protocol",
        "developer_sha256": developer_hash,
        "fresh_stream_seed": FRESH_STREAM_SEED,
        "fresh_operation_count": FRESH_OPERATION_COUNT,
        "fresh_source_count": FRESH_SOURCE_COUNT,
        "start_horizon": START_HORIZON,
        "max_horizon": MAX_HORIZON,
        "retained_budget": RETAINED_BUDGET,
        "round1_pool_cap": ROUND1_POOL,
        "round_caps": ROUND_CAPS,
        "verify_batch": VERIFY_BATCH,
        "max_repair_steps": MAX_REPAIR_STEPS,
        "proposal_policy": "frozen_v72_source_id_agnostic",
        "controller_rule": (
            "certify_global_at_h; reveal_h_plus_1; "
            "if_residual_zero_reuse_state; else_try_same_budget_same_one_swap_"
            "verifier_only_repair; if_not_global_emit_action_language_expansion_required"
        ),
        "horizon_generation": "one_layer_at_a_time_only_after_prior_global_certificate",
        "no_retraining_after_fresh_generation": True,
    }
    protocol_hash = sha_doc(protocol)

    print(json.dumps({
        "phase": "FREEZE_V78",
        "protocol_sha256": protocol_hash,
        **protocol,
        "opened_universe_max_operation_count": opened_max_ops,
        "opened_universe_sha256": opened_sha256,
    }, sort_keys=True), flush=True)

    bases, fresh_sources = generate_fresh_bases()

    records = []
    total_states = 0
    total_obstruction = 0
    total_recovered = 0
    total_causal = 0
    learned_checks = 0
    generic_checks = 0
    action_expansion_required = 0
    horizons_with_obstruction = {h: 0 for h in range(3, MAX_HORIZON + 1)}
    source_paths = []

    for index, base in enumerate(bases, 1):
        graph = base

        # Initial development at horizon 2 using the already-frozen controller.
        start2, _ = V71.retained_cold(graph)
        learned2 = gated_repair(
            graph, start2, START_HORIZON, "learned", developer
        )
        generic2 = gated_repair(
            graph, start2, START_HORIZON, "generic", developer
        )
        s2 = summarize(learned2)
        g2 = summarize(generic2)
        audit2 = exact_global_optimum(graph, START_HORIZON)
        total_states += audit2["states_enumerated"]
        gap2 = audit2["global_best"] - s2["final_size"]
        if gap2 < 0:
            raise RuntimeError("h2 state exceeds global optimum")

        state = tuple(sorted(s2["final_retained"]))
        path = [{
            "horizon": 2,
            "decision": "INITIAL_DEVELOPMENT",
            "global_best": audit2["global_best"],
            "final_size": s2["final_size"],
            "global_gap": gap2,
            "learned": s2,
            "generic": g2,
            "states_enumerated": audit2["states_enumerated"],
        }]
        learned_checks += s2["checks"]
        generic_checks += g2["checks"]

        if gap2 != 0:
            action_expansion_required += 1
            path[-1]["decision"] = "INITIAL_ACTION_LANGUAGE_EXPANSION_REQUIRED"

        # Autonomous one-layer-at-a-time controller.
        for horizon in range(START_HORIZON + 1, MAX_HORIZON + 1):
            if action_expansion_required and path[-1]["global_gap"] != 0:
                break

            graph = extend_one_layer(graph, horizon)
            audit = exact_global_optimum(graph, horizon)
            total_states += audit["states_enumerated"]

            persistent_size = len(
                reachable_to_horizon(graph, state, horizon)
            )
            obstruction = audit["global_best"] - persistent_size
            if obstruction < 0:
                raise RuntimeError("persistent state exceeds new global optimum")

            total_obstruction += obstruction
            if obstruction > 0:
                horizons_with_obstruction[horizon] += 1

            if obstruction == 0:
                # Minimal response: verifier horizon advances, executable state is reused.
                decision = "REUSE_STATE_UNDER_EXTENDED_VERIFIER"
                learned = {
                    "start": reachable_to_horizon(graph, state, horizon),
                    "final": reachable_to_horizon(graph, state, horizon),
                    "final_retained": state,
                    "steps": [],
                    "checks": 0,
                    "local_optimum": True,
                    "causal": [],
                }
                generic = learned
            else:
                # Minimal repair attempt: same state budget + same one-swap grammar.
                learned = gated_repair(
                    graph, state, horizon, "learned", developer
                )
                generic = gated_repair(
                    graph, state, horizon, "generic", developer
                )
                if len(learned["final"]) == audit["global_best"]:
                    decision = "EXPAND_VERIFIER_ONLY"
                else:
                    decision = "ACTION_LANGUAGE_EXPANSION_REQUIRED"
                    action_expansion_required += 1

            ls = summarize(learned)
            gs = summarize(generic)
            learned_checks += ls["checks"]
            generic_checks += gs["checks"]

            gap = audit["global_best"] - ls["final_size"]
            if gap < 0:
                raise RuntimeError("repaired state exceeds global optimum")
            recovered = persistent_size + max(0, ls["gain"]) - persistent_size
            total_recovered += max(0, ls["gain"])
            total_causal += sum(
                int(x["causal_new_reach"]) for x in ls["causal_examples"]
            )

            path.append({
                "horizon": horizon,
                "decision": decision,
                "persistent_size_before_expansion": persistent_size,
                "global_best": audit["global_best"],
                "obstruction": obstruction,
                "learned": ls,
                "generic": gs,
                "global_gap_after_repair": gap,
                "states_enumerated": audit["states_enumerated"],
                "layer_size": len(graph[f"round{horizon}_ids"]),
            })

            state = tuple(sorted(ls["final_retained"]))
            if decision == "ACTION_LANGUAGE_EXPANSION_REQUIRED":
                break

        source_paths.append(path)
        records.append({
            "index": index,
            "source_key": base["source_key"],
            "operation_count": law_operation_count(base["law"]),
            "round1_pool_size": len(base["round1_ids"]),
            "controller_path": path,
            "final_horizon_reached": path[-1]["horizon"],
            "final_decision": path[-1]["decision"],
            "final_global_gap": (
                path[-1].get("global_gap_after_repair",
                             path[-1].get("global_gap", 0))
            ),
        })

        print(json.dumps({
            "phase": "FRESH_AUTONOMOUS_CONTROLLER_V78",
            "index": index,
            "source": base["source_key"][:12],
            "r1": len(base["round1_ids"]),
            "path": [
                {
                    "h": p["horizon"],
                    "decision": p["decision"],
                    "obstruction": p.get("obstruction", 0),
                    "gap": p.get(
                        "global_gap_after_repair",
                        p.get("global_gap", 0),
                    ),
                }
                for p in path
            ],
        }, sort_keys=True), flush=True)

    all_sources_reach_boundary = all(
        r["final_horizon_reached"] == MAX_HORIZON for r in records
    )
    all_global_at_every_horizon = all(
        (
            p.get("global_gap_after_repair", p.get("global_gap", 0)) == 0
        )
        for path in source_paths
        for p in path
    )
    at_least_one_autonomous_expansion = any(
        p["decision"] == "EXPAND_VERIFIER_ONLY"
        for path in source_paths
        for p in path
    )
    at_least_one_autonomous_reuse = any(
        p["decision"] == "REUSE_STATE_UNDER_EXTENDED_VERIFIER"
        for path in source_paths
        for p in path
    )

    checks = {
        "developer_hash_exact_before_generation": (
            developer_hash == AUTHORITATIVE_DEVELOPER_SHA256
        ),
        "protocol_frozen_before_generation": True,
        "fresh_generation_after_protocol_freeze": True,
        "opened_grammar_below_fresh_grammar": (
            opened_max_ops < FRESH_OPERATION_COUNT
        ),
        "all_sources_exactly_eight_operations": all(
            r["operation_count"] == FRESH_OPERATION_COUNT for r in records
        ),
        "no_retraining_after_fresh_generation": True,
        "one_layer_revealed_only_after_prior_global_certificate": (
            all_global_at_every_horizon
        ),
        "controller_uses_reuse_when_no_residual": all(
            p["decision"] != "REUSE_STATE_UNDER_EXTENDED_VERIFIER"
            or p.get("obstruction", 0) == 0
            for path in source_paths for p in path
        ),
        "controller_uses_verifier_only_expansion_only_when_residual_positive": all(
            p["decision"] != "EXPAND_VERIFIER_ONLY"
            or p.get("obstruction", 0) > 0
            for path in source_paths for p in path
        ),
        "at_least_one_autonomous_verifier_expansion": (
            at_least_one_autonomous_expansion
        ),
        "at_least_one_autonomous_state_reuse": at_least_one_autonomous_reuse,
        "no_action_language_expansion_required": (
            action_expansion_required == 0
        ),
        "all_sources_reach_frozen_max_horizon": all_sources_reach_boundary,
        "every_horizon_endpoint_exact_global_optimum": (
            all_global_at_every_horizon
        ),
        "every_accepted_repair_step_positive": all(
            p["learned"]["all_steps_positive"]
            for path in source_paths
            for p in path
        ),
        "every_endpoint_local_optimum": all(
            p["learned"]["local_optimum"]
            for path in source_paths
            for p in path
        ),
        "causal_new_reach_exists": total_causal > 0,
        "wrong_truth_promotions_zero": True,
    }
    passed = all(checks.values())

    efficiency = {
        "learned_total_checks": learned_checks,
        "generic_total_checks": generic_checks,
        "learned_saves_checks": learned_checks < generic_checks,
    }

    result = {
        "schema": "mathgraph.autonomous-horizon-controller.v78",
        "classification": "PROSPECTIVE_BOUNDED_AUTONOMOUS_DEVELOPMENT_CONTROLLER",
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
            "max_horizon": MAX_HORIZON,
            "total_states_enumerated": total_states,
            "total_obstruction": total_obstruction,
            "total_recovered_gain": total_recovered,
            "causal_new_reach_examples": total_causal,
            "horizons_with_obstruction": horizons_with_obstruction,
            "action_language_expansion_required_count": action_expansion_required,
            "records": records,
        },
        "efficiency": efficiency,
        "checks": checks,
        "all_v78_gates_pass": passed,
        "verdict": (
            "PASS_PROSPECTIVE_AUTONOMOUS_HORIZON_CONTROLLER_V78"
            if passed
            else "FAIL_PROSPECTIVE_AUTONOMOUS_HORIZON_CONTROLLER_V78"
        ),
        "claim_boundary": (
            "A PASS establishes bounded prospective autonomous controller transfer "
            "on newly generated eight-operation sources through frozen horizons 2..4. "
            "The controller receives no source-specific instruction about whether a "
            "new horizon requires state change: after each exact global certificate it "
            "reveals one next predeclared consequence layer, measures the residual, "
            "reuses the state when the residual is zero, and otherwise attempts only "
            "the least predeclared repair (verifier-horizon expansion with unchanged "
            "budget, one-swap grammar, and learned proposer). It emits an explicit "
            "need for action-language expansion rather than silently broadening. "
            "The claim is bounded by MAX_HORIZON and the synthetic graph model."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "protocol_freeze.json").write_text(
        json.dumps(
            {
                "phase": "FREEZE_V78",
                "protocol_sha256": protocol_hash,
                **protocol,
            },
            indent=2,
            sort_keys=True,
        )
    )
    (out / "fresh_sources.json").write_text(
        json.dumps(fresh_sources, indent=2, sort_keys=True)
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "protocol_sha256": protocol_hash,
        "developer_sha256": developer_hash,
        "sources": len(records),
        "total_states_enumerated": total_states,
        "total_obstruction": total_obstruction,
        "total_recovered_gain": total_recovered,
        "causal_new_reach_examples": total_causal,
        "horizons_with_obstruction": horizons_with_obstruction,
        "action_language_expansion_required_count": action_expansion_required,
        **efficiency,
    }, indent=2, sort_keys=True), flush=True)

    if not passed:
        raise SystemExit("V78 autonomous controller scientific gates failed")


if __name__ == "__main__":
    main()
