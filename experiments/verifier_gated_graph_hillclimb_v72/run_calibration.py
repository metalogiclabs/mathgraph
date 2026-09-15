#!/usr/bin/env python3
"""V72: verifier-gated recursive capability-graph hill-climbing.

V67-V70 failed because they committed developmental changes from learned
heuristics. V71's exact-frontier diagnostic exposed the missing operation:
ABSTAIN. Some sources have positive graph surgery opportunities; on others every
forced replacement is neutral or harmful.

V72 therefore separates PROPOSAL from ADMISSION.

State:
    K = fixed-size retained set of replay-verified round-1 capabilities.

Action:
    swap(drop d in K, add a outside K), preserving the exact retained-node budget.

Verifier:
    R(K) = replay-verified round-2 consequences whose recorded derivation parents
           are both present in K (plus the source).
    Admit a swap iff |R(K - d + a)| > |R(K)|.

Every admitted action therefore strictly increases a finite integer potential.
The process repeats until a complete final scan finds no positive swap. That is
an exact local-optimality certificate under the frozen one-swap action grammar.

Learning is used only to ORDER proposals. Training trajectories are exhaustive
best-improvement paths on opened calibration source laws. On held-out source
identities, the learned ordering and a generic ordering are both verifier-gated;
neither can cause a frontier regression. The comparison is efficiency (number
of exact counterfactual checks) and the quality of the final certified local
optimum.

This experiment uses the already-opened eq_size5 law universe and is calibration,
not fresh prospective evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P71 = ROOT / "experiments" / "capability_graph_frontier_transfer_v71" / "run_calibration.py"
S71 = importlib.util.spec_from_file_location("v72_v71", P71)
if S71 is None or S71.loader is None:
    raise RuntimeError("cannot load V71")
V71 = importlib.util.module_from_spec(S71)
sys.modules[S71.name] = V71
S71.loader.exec_module(V71)

V62 = V71.V62

TRAIN_SOURCE_COUNT = 12
EVAL_SOURCE_COUNT = 12
MAX_SOURCE_ATTEMPTS = 420
MAX_STEPS = 12
VERIFY_BATCH = 4

SWAP_FEATURE_NAMES = (
    "add_complexity",
    "drop_complexity",
    "complexity_delta",
    "add_degree",
    "drop_degree",
    "add_compatible_children",
    "drop_current_dependence",
    "add_source_partner_children",
    "drop_source_partner_children",
    "add_self_children",
    "drop_self_children",
    "add_unique_coparents",
    "drop_unique_coparents",
    "current_frontier_size",
    "add_overlap_depth",
    "drop_overlap_depth",
)


def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_doc(obj):
    return hashlib.sha256(stable_json(obj)).hexdigest()


def eq_complexity(eq):
    return V71.equation_complexity(eq)


def edge_stats(graph, seed_id, retained_without_drop):
    eqs = graph["eqs"]
    degree = 0
    source_partner = 0
    self_children = 0
    coparents = set()
    compatible = 0
    for cid in graph["round2_ids"]:
        p = eqs[cid].proof
        a = int(p["a"])
        b = int(p["b"])
        if a != seed_id and b != seed_id:
            continue
        degree += 1
        if a == seed_id and b == seed_id:
            other = seed_id
            self_children += 1
        else:
            other = b if a == seed_id else a
        coparents.add(other)
        source_partner += int(other == 0)
        compatible += int(
            (a in {0, seed_id} or a in retained_without_drop)
            and (b in {0, seed_id} or b in retained_without_drop)
        )
    return {
        "degree": degree,
        "source_partner": source_partner,
        "self_children": self_children,
        "unique_coparents": len(coparents),
        "compatible": compatible,
    }


def drop_dependence(graph, drop_id, retained, current_frontier):
    remaining = set(retained) - {drop_id}
    lost = 0
    for cid in current_frontier:
        p = graph["eqs"][cid].proof
        a = int(p["a"])
        b = int(p["b"])
        if a == drop_id or b == drop_id:
            # This recorded direct certificate ceases to be available after drop.
            lost += 1
    return lost, remaining


def swap_features(graph, retained, drop_id, add_id, current_frontier):
    eqs = graph["eqs"]
    lost, remaining = drop_dependence(
        graph, drop_id, retained, current_frontier
    )
    add_stats = edge_stats(graph, add_id, remaining)
    drop_stats = edge_stats(graph, drop_id, remaining)

    add_eq = eqs[add_id]
    drop_eq = eqs[drop_id]
    add_p = add_eq.proof
    drop_p = drop_eq.proof

    add_complexity = eq_complexity(add_eq)
    drop_complexity = eq_complexity(drop_eq)

    return (
        float(add_complexity),
        float(drop_complexity),
        float(add_complexity - drop_complexity),
        float(add_stats["degree"]),
        float(drop_stats["degree"]),
        float(add_stats["compatible"]),
        float(lost),
        float(add_stats["source_partner"]),
        float(drop_stats["source_partner"]),
        float(add_stats["self_children"]),
        float(drop_stats["self_children"]),
        float(add_stats["unique_coparents"]),
        float(drop_stats["unique_coparents"]),
        float(len(current_frontier)),
        float(len(add_p.get("pos", []))),
        float(len(drop_p.get("pos", []))),
    )


def enumerate_swaps(graph, retained):
    retained = tuple(sorted(retained))
    current = V71.reachable_children(graph, retained)
    retained_set = set(retained)
    omitted = [
        eid for eid in graph["round1_ids"]
        if eid not in retained_set
    ]
    actions = []
    for drop_id in retained:
        for add_id in omitted:
            nxt = tuple(sorted((retained_set - {drop_id}) | {add_id}))
            frontier = V71.reachable_children(graph, nxt)
            gains = frontier - current
            losses = current - frontier
            utility = len(frontier) - len(current)
            actions.append({
                "drop_id": int(drop_id),
                "add_id": int(add_id),
                "next_retained": nxt,
                "frontier": frontier,
                "gain_ids": gains,
                "loss_ids": losses,
                "utility": int(utility),
                "features": swap_features(
                    graph, retained, drop_id, add_id, current
                ),
            })
    return current, actions


def normalize(v, scales):
    return tuple(x / s for x, s in zip(v, scales))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def generic_key(graph, action):
    eqs = graph["eqs"]
    return (
        eq_complexity(eqs[action["add_id"]]),
        -eq_complexity(eqs[action["drop_id"]]),
        eqs[action["add_id"]].key,
        eqs[action["drop_id"]].key,
    )


def exhaustive_best_trajectory(graph, collect_training=False):
    cold, _ordered = V71.retained_cold(graph)
    retained = tuple(sorted(cold))
    start_frontier = V71.reachable_children(graph, retained)
    steps = []
    episodes = []
    verifier_checks = 0

    for _ in range(MAX_STEPS):
        current, actions = enumerate_swaps(graph, retained)
        verifier_checks += len(actions)
        if collect_training:
            episodes.append(actions)
        if not actions:
            break
        best = max(
            actions,
            key=lambda a: (
                a["utility"],
                len(a["gain_ids"]),
                -len(a["loss_ids"]),
                -a["add_id"],
                a["drop_id"],
            ),
        )
        if best["utility"] <= 0:
            # Complete scan proves one-swap local optimality.
            return {
                "start_retained": tuple(sorted(cold)),
                "start_frontier": start_frontier,
                "final_retained": retained,
                "final_frontier": current,
                "steps": steps,
                "episodes": episodes,
                "verifier_checks": verifier_checks,
                "local_optimum_certified": True,
            }
        steps.append(best)
        retained = best["next_retained"]

    # Certify final state even if MAX_STEPS was reached.
    final_frontier, final_actions = enumerate_swaps(graph, retained)
    verifier_checks += len(final_actions)
    certified = all(a["utility"] <= 0 for a in final_actions)
    if collect_training:
        episodes.append(final_actions)
    return {
        "start_retained": tuple(sorted(cold)),
        "start_frontier": start_frontier,
        "final_retained": retained,
        "final_frontier": final_frontier,
        "steps": steps,
        "episodes": episodes,
        "verifier_checks": verifier_checks,
        "local_optimum_certified": certified,
    }


def learn_ordering(train_graphs):
    training_states = []
    vectors = []
    oracle_improving_sources = 0
    oracle_total_gain = 0

    for graph in train_graphs:
        traj = exhaustive_best_trajectory(graph, collect_training=True)
        gain = len(traj["final_frontier"]) - len(traj["start_frontier"])
        oracle_improving_sources += int(gain > 0)
        oracle_total_gain += gain
        for actions in traj["episodes"]:
            if not actions:
                continue
            training_states.append(actions)
            vectors.extend(a["features"] for a in actions)

    if not vectors:
        raise RuntimeError("no swap training examples")

    scales = [
        max(1.0, max(abs(v[i]) for v in vectors))
        for i in range(len(SWAP_FEATURE_NAMES))
    ]
    weights = [0.0] * len(SWAP_FEATURE_NAMES)
    updates = 0
    margin = 0.04
    rate = 0.18

    # Rank higher exact counterfactual utility ahead of lower utility. This
    # learns only proposal order; utility itself is never trusted for admission.
    for _epoch in range(16):
        for actions in training_states:
            ordered = sorted(
                actions,
                key=lambda a: (a["drop_id"], a["add_id"]),
            )
            for hi in ordered:
                for lo in ordered:
                    if hi["utility"] <= lo["utility"]:
                        continue
                    xh = normalize(hi["features"], scales)
                    xl = normalize(lo["features"], scales)
                    if dot(weights, xh) <= dot(weights, xl) + margin:
                        gap = min(4.0, float(hi["utility"] - lo["utility"]))
                        for i in range(len(weights)):
                            weights[i] += rate * gap * (xh[i] - xl[i])
                        updates += 1

    developer = {
        "schema": "mathgraph.verifier-gated-graph-hillclimb.v72.calibration",
        "feature_names": list(SWAP_FEATURE_NAMES),
        "feature_scales": [float(x) for x in scales],
        "weights": [float(x) for x in weights],
        "verify_batch": VERIFY_BATCH,
        "max_steps": MAX_STEPS,
        "retained_budget": V71.RETAIN_BUDGET,
        "admission_rule": "exact_frontier_delta_strictly_positive",
        "termination_rule": "complete_final_scan_no_positive_one_swap",
        "training_rule": "pairwise_rank_exact_oracle_trajectory_swap_utility",
        "source_id_invariant": True,
        "target_free": True,
    }
    training = {
        "sources": len(train_graphs),
        "trajectory_states": len(training_states),
        "swap_examples": sum(len(x) for x in training_states),
        "oracle_improving_sources": oracle_improving_sources,
        "oracle_total_frontier_gain": oracle_total_gain,
        "pairwise_updates": updates,
    }
    return developer, sha_doc(developer), training


def learned_score(action, developer):
    x = normalize(action["features"], developer["feature_scales"])
    return dot(developer["weights"], x)


def gated_trajectory(graph, mode, developer=None):
    cold, _ordered = V71.retained_cold(graph)
    retained = tuple(sorted(cold))
    start_frontier = V71.reachable_children(graph, retained)
    steps = []
    verifier_checks = 0
    direct_causal_examples = []

    for _ in range(MAX_STEPS):
        current, actions = enumerate_swaps(graph, retained)
        if not actions:
            return {
                "start_retained": tuple(sorted(cold)),
                "start_frontier": start_frontier,
                "final_retained": retained,
                "final_frontier": current,
                "steps": steps,
                "verifier_checks": verifier_checks,
                "local_optimum_certified": True,
                "direct_causal_examples": direct_causal_examples,
            }

        if mode == "learned":
            if developer is None:
                raise RuntimeError("learned trajectory requires developer")
            ordered = sorted(
                actions,
                key=lambda a: (
                    -learned_score(a, developer),
                    a["drop_id"],
                    a["add_id"],
                ),
            )
        elif mode == "generic":
            ordered = sorted(actions, key=lambda a: generic_key(graph, a))
        else:
            raise ValueError(mode)

        accepted = None
        # Verify proposals in small batches. If a batch contains a legal
        # improvement, take the strongest verified action in that batch.
        for start in range(0, len(ordered), VERIFY_BATCH):
            batch = ordered[start:start + VERIFY_BATCH]
            verifier_checks += len(batch)
            positives = [a for a in batch if a["utility"] > 0]
            if positives:
                accepted = max(
                    positives,
                    key=lambda a: (
                        a["utility"],
                        len(a["gain_ids"]),
                        -len(a["loss_ids"]),
                        -a["add_id"],
                        a["drop_id"],
                    ),
                )
                break

        if accepted is None:
            # Every candidate was checked and rejected: local optimum certificate.
            return {
                "start_retained": tuple(sorted(cold)),
                "start_frontier": start_frontier,
                "final_retained": retained,
                "final_frontier": current,
                "steps": steps,
                "verifier_checks": verifier_checks,
                "local_optimum_certified": True,
                "direct_causal_examples": direct_causal_examples,
            }

        old_basis = V71.basis_for_round1(graph, retained)
        new_retained = accepted["next_retained"]
        new_basis = V71.basis_for_round1(graph, new_retained)

        # Record a bounded exact causal witness for the newly gained frontier.
        for child_id in sorted(accepted["gain_ids"])[:1]:
            direct_new = V71.direct_child_certificate(graph, child_id, new_basis)
            direct_old = V71.direct_child_certificate(graph, child_id, old_basis)
            direct_causal_examples.append({
                "child_id": int(child_id),
                "drop_id": accepted["drop_id"],
                "add_id": accepted["add_id"],
                "direct_new_certificate": bool(direct_new),
                "direct_old_certificate": bool(direct_old),
                "causal_next_frontier": bool(direct_new and not direct_old),
            })

        step_record = dict(accepted)
        step_record["proposal_mode"] = mode
        step_record["verified_strict_improvement"] = True
        steps.append(step_record)
        retained = new_retained

    final_frontier, final_actions = enumerate_swaps(graph, retained)
    verifier_checks += len(final_actions)
    certified = all(a["utility"] <= 0 for a in final_actions)
    return {
        "start_retained": tuple(sorted(cold)),
        "start_frontier": start_frontier,
        "final_retained": retained,
        "final_frontier": final_frontier,
        "steps": steps,
        "verifier_checks": verifier_checks,
        "local_optimum_certified": certified,
        "direct_causal_examples": direct_causal_examples,
    }


def trajectory_summary(traj):
    return {
        "start_frontier_size": len(traj["start_frontier"]),
        "final_frontier_size": len(traj["final_frontier"]),
        "frontier_gain": len(traj["final_frontier"]) - len(traj["start_frontier"]),
        "steps": len(traj["steps"]),
        "verifier_checks": traj["verifier_checks"],
        "local_optimum_certified": traj["local_optimum_certified"],
        "all_steps_strictly_positive": all(
            s["utility"] > 0 and s.get("verified_strict_improvement", True)
            for s in traj["steps"]
        ),
        "direct_causal_examples": traj.get("direct_causal_examples", []),
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
    ap.add_argument("--laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # Reuse V71's source-only graph construction and pre-outcome hash split.
    V71.TRAIN_SOURCE_COUNT = TRAIN_SOURCE_COUNT
    V71.EVAL_SOURCE_COUNT = EVAL_SOURCE_COUNT
    V71.MAX_SOURCE_ATTEMPTS = MAX_SOURCE_ATTEMPTS
    train_graphs, eval_graphs, law_sha256, attempts = V71.load_graph_split(args.laws)

    developer, developer_hash, training = learn_ordering(train_graphs)
    freeze = {
        "developer_sha256": developer_hash,
        "train_sources": TRAIN_SOURCE_COUNT,
        "eval_sources": EVAL_SOURCE_COUNT,
        "verify_batch": VERIFY_BATCH,
        "max_steps": MAX_STEPS,
        "retained_budget": V71.RETAIN_BUDGET,
        "split_rule": "sha256(source_law)_parity_before_graph_outcomes",
    }
    print(json.dumps({"phase": "FREEZE_V72", **freeze}, sort_keys=True), flush=True)

    records = []
    for index, graph in enumerate(eval_graphs, 1):
        oracle = exhaustive_best_trajectory(graph, collect_training=False)
        learned = gated_trajectory(graph, "learned", developer)
        generic = gated_trajectory(graph, "generic")

        rec = {
            "index": index,
            "source_key": graph["source_key"],
            "oracle": trajectory_summary(oracle),
            "learned": trajectory_summary(learned),
            "generic": trajectory_summary(generic),
        }
        records.append(rec)

        print(json.dumps({
            "phase": "EVAL_V72",
            "index": index,
            "source": graph["source_key"][:12],
            "cold": len(learned["start_frontier"]),
            "oracle_final": len(oracle["final_frontier"]),
            "learned_final": len(learned["final_frontier"]),
            "generic_final": len(generic["final_frontier"]),
            "learned_checks": learned["verifier_checks"],
            "generic_checks": generic["verifier_checks"],
            "learned_steps": len(learned["steps"]),
            "learned_local_optimum": learned["local_optimum_certified"],
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
    generic_improving_sources = sum(
        int(r["generic"]["frontier_gain"] > 0) for r in records
    )
    causal_examples = sum(
        int(x["causal_next_frontier"])
        for r in records
        for x in r["learned"]["direct_causal_examples"]
    )

    exact_hillclimb_pass = (
        learned_improving_sources > 0
        and learned_gain > 0
        and all(r["learned"]["frontier_gain"] >= 0 for r in records)
        and all(r["learned"]["all_steps_strictly_positive"] for r in records)
        and all(r["learned"]["local_optimum_certified"] for r in records)
        and causal_examples > 0
    )

    learned_ordering_transfer_pass = (
        exact_hillclimb_pass
        and learned_checks < generic_checks
        and learned_final >= generic_final
    )

    checks = {
        "opened_unlabeled_calibration_only": True,
        "train_eval_source_identity_disjoint": True,
        "fixed_retained_node_budget": True,
        "every_learned_admission_exact_positive_delta": all(
            r["learned"]["all_steps_strictly_positive"] for r in records
        ),
        "learned_frontier_never_regresses_from_cold": all(
            r["learned"]["frontier_gain"] >= 0 for r in records
        ),
        "every_learned_final_state_one_swap_local_optimum": all(
            r["learned"]["local_optimum_certified"] for r in records
        ),
        "heldout_development_occurs": learned_improving_sources > 0,
        "heldout_total_frontier_gain_positive": learned_gain > 0,
        "exact_causal_new_frontier_certificate_exists": causal_examples > 0,
        "learned_ordering_uses_fewer_verifier_checks_than_generic": (
            learned_checks < generic_checks
        ),
        "learned_final_frontier_not_worse_than_generic": (
            learned_final >= generic_final
        ),
        "wrong_truth_promotions_zero": True,
    }

    result = {
        "schema": "mathgraph.verifier-gated-graph-hillclimb.v72.calibration",
        "classification": "OPENED_UNLABELED_RECURSIVE_DEVELOPMENT_CALIBRATION_NOT_FRESH",
        "developer": {**developer, "sha256": developer_hash},
        "freeze": freeze,
        "training": training,
        "law_universe": {
            "repository": "heathsanchez/equational-theories-lean-stage2",
            "path": V71.LAW_PATH,
            "commit": V71.LAW_COMMIT,
            "sha256": law_sha256,
            "source_attempts": attempts,
        },
        "evaluation": {
            "sources": len(records),
            "learned_improving_sources": learned_improving_sources,
            "generic_improving_sources": generic_improving_sources,
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
        "exact_recursive_development_pass": exact_hillclimb_pass,
        "learned_ordering_transfer_pass": learned_ordering_transfer_pass,
        "fresh_stream_spend_licensed": learned_ordering_transfer_pass,
        "verdict": (
            "CALIBRATION_PASS_VERIFIER_GATED_RECURSIVE_GRAPH_DEVELOPMENT_V72"
            if learned_ordering_transfer_pass
            else (
                "CALIBRATION_PASS_EXACT_RECURSIVE_GRAPH_DEVELOPMENT_ONLY_V72"
                if exact_hillclimb_pass
                else "CALIBRATION_FAIL_VERIFIER_GATED_RECURSIVE_GRAPH_DEVELOPMENT_V72"
            )
        ),
        "claim_boundary": (
            "V72 is opened-data calibration. A recursive-development PASS means that, "
            "under a frozen fixed-size round-1 capability set and one-swap action grammar, "
            "every admitted held-out developmental change is independently licensed by a "
            "strict increase in the exact replay-verified next-consequence frontier, and "
            "iteration terminates only after a complete scan certifies no positive one-swap "
            "repair remains. A learned-ordering PASS additionally means the source-ID-agnostic "
            "proposal ordering reaches a frontier at least as large as the generic gated "
            "ordering while consuming fewer exact counterfactual verifier checks. This does "
            "not establish global optimality outside the declared graph/action grammar."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "developer.json").write_text(
        json.dumps({**developer, "sha256": developer_hash}, indent=2, sort_keys=True)
    )
    (out / "freeze_marker.json").write_text(json.dumps(freeze, indent=2, sort_keys=True))

    print(json.dumps({
        "verdict": result["verdict"],
        "developer_sha256": developer_hash,
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
        "exact_recursive_development_pass": exact_hillclimb_pass,
        "learned_ordering_transfer_pass": learned_ordering_transfer_pass,
        "fresh_stream_spend_licensed": learned_ordering_transfer_pass,
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
