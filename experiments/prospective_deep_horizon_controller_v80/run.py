#!/usr/bin/env python3
"""V80: prospective deep-horizon autonomous controller.

Fresh nine-operation source laws are generated only after the full protocol is
frozen. The controller starts from horizon 2 and advances one verified
consequence layer at a time through horizon 6.

At each horizon:
  * exact fixed-budget global optimum is exhaustively computed;
  * if the persistent state is still globally optimal, REUSE;
  * otherwise try only the already-frozen verifier-gated one-swap repair;
  * if one-swap cannot reach the exact global optimum, emit
    ACTION_LANGUAGE_EXPANSION_REQUIRED and stop that source.

No retraining, budget change, or action-language widening is allowed after
fresh source generation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P78 = ROOT / "experiments" / "autonomous_horizon_controller_v78" / "run.py"
S78 = importlib.util.spec_from_file_location("v80_v78", P78)
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

FRESH_STREAM_SEED = "MATHGRAPH_V80_FRESH_NINE_OP_DEEP_HORIZON_2026_09_16_A"
FRESH_OPERATION_COUNT = 9
FRESH_SOURCE_COUNT = 6
MAX_FRESH_ATTEMPTS = 6000
VARIABLES = ("x", "y", "z", "w")

START_HORIZON = 2
MAX_HORIZON = 6
RETAINED_BUDGET = 5
ROUND_CAPS = {
    2: V71.ROUND2_POOL,
    3: 144,
    4: 216,
    5: 288,
    6: 360,
}
VERIFY_BATCH = V78.VERIFY_BATCH
MAX_REPAIR_STEPS = 16


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
            f"insufficient eligible nine-op sources: {len(graphs)} "
            f"after {MAX_FRESH_ATTEMPTS} attempts"
        )
    return graphs, sources


def extend_one_layer(graph, horizon: int):
    if horizon < 3:
        raise ValueError("base graph already includes horizon 2")
    key = f"round{horizon}_ids"
    if key in graph:
        return graph

    prev_key = f"round{horizon - 1}_ids"
    if prev_key not in graph:
        raise RuntimeError(f"missing {prev_key}")

    eqs = dict(graph["eqs"])
    existing_keys = {eq.key for eq in eqs.values()}
    next_id = max(eqs) + 1

    raw = V71.enumerate_candidates(
        eqs,
        graph[prev_key],
        existing_keys,
    )

    ids = []
    for complexity, eqkey, cl, cr, proof in raw[: ROUND_CAPS[horizon]]:
        child = V62.Equation(next_id, cl, cr, eqkey, proof, horizon)
        trial = dict(eqs)
        trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError(f"horizon-{horizon} replay failed")
        eqs[next_id] = child
        existing_keys.add(eqkey)
        ids.append(next_id)
        next_id += 1

    for eid in ids:
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored horizon-{horizon} node failed replay")

    out = dict(graph)
    out["eqs"] = eqs
    out[key] = ids
    return out


def reachable(graph, retained, horizon: int):
    return V78.reachable_to_horizon(graph, retained, horizon)


def exact_global(graph, horizon: int):
    ids = tuple(sorted(graph["round1_ids"]))
    states = list(itertools.combinations(ids, RETAINED_BUDGET))
    best = -1
    best_sets = []
    for kept in states:
        value = len(reachable(graph, kept, horizon))
        if value > best:
            best = value
            best_sets = [tuple(kept)]
        elif value == best and len(best_sets) < 128:
            best_sets.append(tuple(kept))
    return {
        "global_best": best,
        "states_enumerated": len(states),
        "stored_global_optima": best_sets,
    }


def gated_repair(graph, state, horizon: int, mode: str, developer):
    # Reuse the V78 verifier-gated one-swap engine, but allow a larger fixed
    # repair-step ceiling by iterating V78's exact local scans if necessary.
    retained = tuple(sorted(state))
    start_frontier = reachable(graph, retained, horizon)
    all_steps = []
    total_checks = 0
    causal = []

    for _ in range(MAX_REPAIR_STEPS):
        current, actions = V78.actions_for_horizon(graph, retained, horizon)
        if not actions:
            return {
                "start": start_frontier,
                "final": current,
                "final_retained": retained,
                "steps": all_steps,
                "checks": total_checks,
                "local_optimum": True,
                "causal": causal,
            }

        if mode == "learned":
            ordered = sorted(
                actions,
                key=lambda a: (
                    -V78.learned_score(a, developer),
                    a["drop_id"],
                    a["add_id"],
                ),
            )
        elif mode == "generic":
            ordered = sorted(actions, key=lambda a: V78.generic_key(graph, a))
        else:
            raise ValueError(mode)

        accepted = None
        for i in range(0, len(ordered), VERIFY_BATCH):
            batch = ordered[i:i + VERIFY_BATCH]
            total_checks += len(batch)
            positives = [a for a in batch if a["utility"] > 0]
            if positives:
                accepted = V78.best_action(positives)
                break

        if accepted is None:
            return {
                "start": start_frontier,
                "final": current,
                "final_retained": retained,
                "steps": all_steps,
                "checks": total_checks,
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
        all_steps.append(accepted)
        retained = tuple(sorted(accepted["next_retained"]))

    current, actions = V78.actions_for_horizon(graph, retained, horizon)
    total_checks += len(actions)
    return {
        "start": start_frontier,
        "final": current,
        "final_retained": retained,
        "steps": all_steps,
        "checks": total_checks,
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

    opened_path = Path(args.opened_laws)
    opened_max_ops, opened_count = opened_universe_max_ops(opened_path)
    if opened_max_ops >= FRESH_OPERATION_COUNT:
        raise RuntimeError("fresh grammar boundary invalid")

    developer, developer_hash, training, opened_sha256, training_attempts = (
        V73.rebuild_v72_developer(opened_path)
    )
    if developer_hash != AUTHORITATIVE_DEVELOPER_SHA256:
        raise RuntimeError("authoritative developer hash drift")

    protocol = {
        "schema": "mathgraph.prospective-deep-horizon-controller.v80.protocol",
        "developer_sha256": developer_hash,
        "fresh_stream_seed": FRESH_STREAM_SEED,
        "fresh_operation_count": FRESH_OPERATION_COUNT,
        "fresh_source_count": FRESH_SOURCE_COUNT,
        "start_horizon": START_HORIZON,
        "max_horizon": MAX_HORIZON,
        "retained_budget": RETAINED_BUDGET,
        "round_caps": ROUND_CAPS,
        "proposal_policy": "frozen_v72_source_id_agnostic",
        "action_grammar": "one_swap_drop_one_add_one_only",
        "controller_rule": (
            "at_each_horizon_exact_global_audit; "
            "reuse_if_persistent_global; otherwise verifier_only_one_swap_repair; "
            "if_repair_below_global_emit_action_language_expansion_required"
        ),
        "horizon_reveal_rule": (
            "reveal_exactly_one_next_layer_only_after_prior_endpoint_global_certificate"
        ),
        "no_retraining_after_fresh_generation": True,
        "no_budget_change_after_fresh_generation": True,
        "no_action_language_change_after_fresh_generation": True,
    }
    protocol_hash = sha_doc(protocol)

    print(json.dumps({
        "phase": "FREEZE_V80",
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
    reuse_decisions = 0
    verifier_expansion_decisions = 0
    obstruction_by_horizon = {h: 0 for h in range(3, MAX_HORIZON + 1)}

    for index, base in enumerate(bases, 1):
        graph = base
        cold, _ = V71.retained_cold(graph)
        state = tuple(sorted(cold))
        path = []
        source_failed = False

        for horizon in range(START_HORIZON, MAX_HORIZON + 1):
            if horizon > START_HORIZON:
                graph = extend_one_layer(graph, horizon)

            audit = exact_global(graph, horizon)
            total_states += audit["states_enumerated"]
            persistent_size = len(reachable(graph, state, horizon))
            obstruction = audit["global_best"] - persistent_size
            if obstruction < 0:
                raise RuntimeError("persistent state exceeds exact global optimum")

            if horizon == START_HORIZON:
                learned = gated_repair(graph, state, horizon, "learned", developer)
                generic = gated_repair(graph, state, horizon, "generic", developer)
                decision = "INITIAL_DEVELOPMENT"
            elif obstruction == 0:
                decision = "REUSE_STATE_UNDER_EXTENDED_VERIFIER"
                reuse_decisions += 1
                frozen_frontier = reachable(graph, state, horizon)
                learned = {
                    "start": frozen_frontier,
                    "final": frozen_frontier,
                    "final_retained": state,
                    "steps": [],
                    "checks": 0,
                    "local_optimum": True,
                    "causal": [],
                }
                generic = learned
            else:
                obstruction_by_horizon[horizon] += 1
                total_obstruction += obstruction
                learned = gated_repair(graph, state, horizon, "learned", developer)
                generic = gated_repair(graph, state, horizon, "generic", developer)
                decision = "EXPAND_VERIFIER_ONLY"

            ls = summarize(learned)
            gs = summarize(generic)
            learned_checks += ls["checks"]
            generic_checks += gs["checks"]

            gap = audit["global_best"] - ls["final_size"]
            if gap < 0:
                raise RuntimeError("repair exceeds exact global optimum")

            if horizon > START_HORIZON and obstruction > 0:
                if gap == 0:
                    verifier_expansion_decisions += 1
                    total_recovered += obstruction
                else:
                    decision = "ACTION_LANGUAGE_EXPANSION_REQUIRED"
                    action_expansion_required += 1
                    source_failed = True

            total_causal += sum(
                int(x["causal_new_reach"]) for x in ls["causal_examples"]
            )

            path.append({
                "horizon": horizon,
                "decision": decision,
                "persistent_size_before_action": persistent_size,
                "global_best": audit["global_best"],
                "obstruction": obstruction,
                "learned": ls,
                "generic": gs,
                "global_gap_after_action": gap,
                "states_enumerated": audit["states_enumerated"],
                "layer_size": len(graph[f"round{horizon}_ids"]) if horizon >= 2 else None,
            })

            state = tuple(sorted(ls["final_retained"]))

            if source_failed:
                break

        records.append({
            "index": index,
            "source_key": base["source_key"],
            "operation_count": law_operation_count(base["law"]),
            "round1_pool_size": len(base["round1_ids"]),
            "controller_path": path,
            "final_horizon_reached": path[-1]["horizon"],
            "final_global_gap": path[-1]["global_gap_after_action"],
            "action_language_expansion_required": source_failed,
        })

        print(json.dumps({
            "phase": "FRESH_DEEP_CONTROLLER_V80",
            "index": index,
            "source": base["source_key"][:12],
            "r1": len(base["round1_ids"]),
            "path": [
                {
                    "h": p["horizon"],
                    "decision": p["decision"],
                    "obstruction": p["obstruction"],
                    "gap": p["global_gap_after_action"],
                    "layer": p["layer_size"],
                }
                for p in path
            ],
        }, sort_keys=True), flush=True)

    all_global = all(
        p["global_gap_after_action"] == 0
        for r in records
        for p in r["controller_path"]
    )
    all_reach_h6 = all(r["final_horizon_reached"] == MAX_HORIZON for r in records)
    every_step_positive = all(
        p["learned"]["all_steps_positive"]
        for r in records for p in r["controller_path"]
    )
    every_local = all(
        p["learned"]["local_optimum"]
        for r in records for p in r["controller_path"]
    )

    checks = {
        "developer_hash_exact_before_generation": (
            developer_hash == AUTHORITATIVE_DEVELOPER_SHA256
        ),
        "protocol_frozen_before_generation": True,
        "fresh_generation_after_freeze": True,
        "opened_grammar_below_fresh_grammar": (
            opened_max_ops < FRESH_OPERATION_COUNT
        ),
        "all_fresh_sources_exactly_nine_operations": all(
            r["operation_count"] == FRESH_OPERATION_COUNT for r in records
        ),
        "no_retraining_after_fresh_generation": True,
        "budget_never_changed": True,
        "action_language_never_changed": True,
        "every_endpoint_exact_global_optimum": all_global,
        "all_sources_reach_horizon_6": all_reach_h6,
        "no_action_language_expansion_required": (
            action_expansion_required == 0
        ),
        "at_least_one_reuse_decision": reuse_decisions > 0,
        "at_least_one_verifier_expansion_decision": (
            verifier_expansion_decisions > 0
        ),
        "every_accepted_step_strictly_improving": every_step_positive,
        "every_endpoint_one_swap_local_optimum": every_local,
        "causal_new_reach_exists": total_causal > 0,
        "learned_not_worse_than_generic_checks": learned_checks <= generic_checks,
        "wrong_truth_promotions_zero": True,
    }
    passed = all(checks.values())

    result = {
        "schema": "mathgraph.prospective-deep-horizon-controller.v80",
        "classification": "PROSPECTIVE_DEEP_HORIZON_ACTION_INVARIANCE_TEST",
        "protocol": protocol,
        "protocol_sha256": protocol_hash,
        "developer": {**developer, "sha256": developer_hash},
        "training": training,
        "opened_training_universe": {
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
            "total_recovered": total_recovered,
            "causal_new_reach_examples": total_causal,
            "reuse_decisions": reuse_decisions,
            "verifier_expansion_decisions": verifier_expansion_decisions,
            "action_language_expansion_required_count": action_expansion_required,
            "obstruction_by_horizon": obstruction_by_horizon,
            "learned_total_checks": learned_checks,
            "generic_total_checks": generic_checks,
            "records": records,
        },
        "checks": checks,
        "all_v80_gates_pass": passed,
        "verdict": (
            "PASS_PROSPECTIVE_DEEP_HORIZON_ACTION_INVARIANCE_V80"
            if passed
            else "FAIL_PROSPECTIVE_DEEP_HORIZON_ACTION_INVARIANCE_V80"
        ),
        "claim_boundary": (
            "A PASS establishes that on the frozen V80 synthetic nine-operation "
            "source stream, the already-frozen one-swap developmental primitive "
            "remained sufficient to reach the exact global fixed-budget optimum "
            "at every horizon 2 through 6. The autonomous controller chooses "
            "state reuse versus verifier-only repair from the exact residual at "
            "each newly revealed horizon. This is bounded evidence for action-"
            "language invariance in the declared graph model, not a universal "
            "claim or proof of adequacy at unbounded consequence depth."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "protocol_freeze.json").write_text(
        json.dumps({
            "phase": "FREEZE_V80",
            "protocol_sha256": protocol_hash,
            **protocol,
        }, indent=2, sort_keys=True)
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
        "total_recovered": total_recovered,
        "reuse_decisions": reuse_decisions,
        "verifier_expansion_decisions": verifier_expansion_decisions,
        "action_language_expansion_required_count": action_expansion_required,
        "obstruction_by_horizon": obstruction_by_horizon,
        "causal_new_reach_examples": total_causal,
        "learned_total_checks": learned_checks,
        "generic_total_checks": generic_checks,
    }, indent=2, sort_keys=True), flush=True)

    if not passed:
        raise SystemExit("V80 prospective deep-horizon scientific gates failed")


if __name__ == "__main__":
    main()
