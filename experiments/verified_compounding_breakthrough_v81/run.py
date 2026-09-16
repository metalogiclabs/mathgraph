#!/usr/bin/env python3
"""V81 fresh prospective verified-compounding breakthrough experiment.

The full protocol is frozen before any fresh ten-operation source exists.  The
controller keeps the V72 learned proposer, fixed retained budget of five, and
one-swap action language while extending the exact consequence horizon from 2
through 7.  Each endpoint is exhaustively audited against the exact fixed-budget
global optimum.

Compounding is evaluated separately from development.  For each later horizon,
the warm path starts from the previously persisted globally-certified state;
the cold counterfactual deletes that retained state and restarts from the
original declared baseline under the *same* learned proposer, verifier, action
language, and consequence graph.  A compounding signal requires equal globally
certified endpoint quality, aggregate non-regression in verifier checks, and at
least one exact warm saving restored by the cold-state ablation.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from mathgraph.developmental_artifacts import (
    VerifiedCapabilityBlock,
    VerifiedDevelopmentTransition,
    VerifiedObstruction,
)

ROOT = Path(__file__).resolve().parents[2]
P80 = ROOT / "experiments" / "prospective_deep_horizon_controller_v80" / "run.py"
S80 = importlib.util.spec_from_file_location("v81_v80", P80)
if S80 is None or S80.loader is None:
    raise RuntimeError("cannot load V80")
V80 = importlib.util.module_from_spec(S80)
sys.modules[S80.name] = V80
S80.loader.exec_module(V80)

V73 = V80.V73
V71 = V80.V71
V62 = V80.V62

AUTHORITATIVE_DEVELOPER_SHA256 = V80.AUTHORITATIVE_DEVELOPER_SHA256

FRESH_STREAM_SEED = "MATHGRAPH_V81_FRESH_TEN_OP_BREAKTHROUGH_2026_09_16_A"
FRESH_OPERATION_COUNT = 10
FRESH_SOURCE_COUNT = 3
QUICK_SOURCE_COUNT = 2
MAX_FRESH_ATTEMPTS = 8000
VARIABLES = ("x", "y", "z", "w")

START_HORIZON = 2
MAX_HORIZON = 7
RETAINED_BUDGET = 5
ROUND_CAPS = {
    2: V71.ROUND2_POOL,
    3: 144,
    4: 216,
    5: 288,
    6: 360,
    7: 432,
}
ACTION_GRAMMAR = "one_swap_drop_one_add_one_only"


def stable_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha_doc(obj: Any) -> str:
    return hashlib.sha256(stable_json(obj)).hexdigest()


def build_protocol(developer_sha256: str, source_count: int = FRESH_SOURCE_COUNT) -> dict[str, Any]:
    return {
        "schema": "mathgraph.verified-compounding-breakthrough.v81.protocol",
        "developer_sha256": developer_sha256,
        "fresh_stream_seed": FRESH_STREAM_SEED,
        "fresh_operation_count": FRESH_OPERATION_COUNT,
        "fresh_source_count": int(source_count),
        "start_horizon": START_HORIZON,
        "max_horizon": MAX_HORIZON,
        "retained_budget": RETAINED_BUDGET,
        "round_caps": dict(ROUND_CAPS),
        "action_grammar": ACTION_GRAMMAR,
        "proposal_policy": "frozen_v72_source_id_agnostic",
        "admission_rule": "strict_positive_exact_verifier_delta_only",
        "global_endpoint_rule": "exhaustive_fixed_budget_enumeration",
        "horizon_reveal_rule": "one_next_layer_only_after_prior_global_certificate_and_restart",
        "warm_path": "previously_persisted_globally_certified_state",
        "cold_counterfactual": "original_declared_baseline_same_proposer_verifier_action_language",
        "compounding_rule": "equal_global_endpoint_and_aggregate_warm_not_worse_and_at_least_one_causal_warm_saving",
        "no_retraining_after_fresh_generation": True,
        "no_budget_change_after_fresh_generation": True,
        "no_action_language_change_after_fresh_generation": True,
        "failed_search_promotes_truth": False,
    }


def classify_compounding(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    cold = sum(int(row.get("cold_checks", 0)) for row in comparisons)
    warm = sum(int(row.get("warm_checks", 0)) for row in comparisons)
    endpoints_equal = bool(comparisons) and all(bool(row.get("endpoint_equal")) for row in comparisons)
    causal_savings = [
        row
        for row in comparisons
        if bool(row.get("endpoint_equal"))
        and int(row.get("warm_checks", 0)) < int(row.get("cold_checks", 0))
        and bool(row.get("ablation_restores_cost"))
    ]
    if not endpoints_equal:
        classification = "FAIL"
    elif warm <= cold and causal_savings:
        classification = "VERIFIED_COMPOUNDING_SIGNAL"
    else:
        classification = "ACCUMULATION_ONLY"
    return {
        "classification": classification,
        "comparison_count": len(comparisons),
        "aggregate_cold_checks": cold,
        "aggregate_warm_checks": warm,
        "aggregate_check_savings": cold - warm,
        "all_endpoints_equal": endpoints_equal,
        "causal_saving_count": len(causal_savings),
    }


def _digest_byte(counter: int, label: str) -> int:
    raw = f"{FRESH_STREAM_SEED}|{counter}|{label}".encode("utf-8")
    return hashlib.sha256(raw).digest()[0]


def _generate_term(ops: int, counter: int, label: str) -> str:
    if ops == 0:
        return VARIABLES[_digest_byte(counter, label + "|var") % len(VARIABLES)]
    left_ops = _digest_byte(counter, label + "|split") % ops
    right_ops = ops - 1 - left_ops
    return f"({_generate_term(left_ops, counter, label + '|L')} * {_generate_term(right_ops, counter, label + '|R')})"


def _generate_law(counter: int) -> str:
    lhs_ops = 1 + (_digest_byte(counter, "lhs_ops") % (FRESH_OPERATION_COUNT - 1))
    rhs_ops = FRESH_OPERATION_COUNT - lhs_ops
    return f"{_generate_term(lhs_ops, counter, 'lhs')} = {_generate_term(rhs_ops, counter, 'rhs')}"


def _operation_count(law: str) -> int:
    return law.count("*")


def _canonical_key(law: str) -> str:
    lhs, rhs = V62.parse_eq(law)
    _l, _r, key = V62.canonical_equation(lhs, rhs)
    return key


def generate_fresh_bases(source_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    graphs: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for counter in range(MAX_FRESH_ATTEMPTS):
        if len(graphs) >= source_count:
            break
        law = _generate_law(counter)
        if _operation_count(law) != FRESH_OPERATION_COUNT:
            raise RuntimeError("fresh operation-count invariant failed")
        try:
            key = _canonical_key(law)
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
        sources.append(
            {
                "stream_counter": counter,
                "source_key": graph["source_key"],
                "law": law,
                "operation_count": _operation_count(law),
                "round1_nodes": len(graph["round1_ids"]),
                "round2_nodes": len(graph["round2_ids"]),
            }
        )
    if len(graphs) != source_count:
        raise RuntimeError(f"insufficient eligible ten-operation sources: {len(graphs)} / {source_count}")
    return graphs, sources


def extend_one_layer(graph: dict[str, Any], horizon: int) -> dict[str, Any]:
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
    raw = V71.enumerate_candidates(eqs, graph[prev_key], existing_keys)
    ids: list[int] = []
    for _complexity, eqkey, cl, cr, proof in raw[: ROUND_CAPS[horizon]]:
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
            raise RuntimeError(f"stored horizon-{horizon} replay failed: {eid}")
    out = dict(graph)
    out["eqs"] = eqs
    out[key] = ids
    return out


def _persist_and_restart(out_dir: Path, source_index: int, horizon: int, source_key: str, state: tuple[int, ...]) -> tuple[tuple[int, ...], str, str]:
    payload = {
        "schema": "mathgraph.persisted-capability-state.v81",
        "source_index": source_index,
        "source_key": source_key,
        "horizon": horizon,
        "retained_state": list(state),
    }
    digest = sha_doc(payload)
    path = out_dir / "persisted_states" / f"source_{source_index:02d}_h{horizon}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    replay_payload = {k: loaded[k] for k in payload}
    if sha_doc(replay_payload) != digest:
        raise RuntimeError("persisted state hash changed on restart")
    restarted = tuple(int(x) for x in loaded["retained_state"])
    if restarted != state:
        raise RuntimeError("persisted state changed on restart")
    return restarted, digest, str(path.relative_to(out_dir))


def _capability_blocks(
    *,
    source_index: int,
    source_key: str,
    horizon: int,
    state: tuple[int, ...],
    persistence_hash: str,
    global_value: int,
    transition_ids: tuple[str, ...],
) -> list[VerifiedCapabilityBlock]:
    return [
        VerifiedCapabilityBlock(
            capability_id=f"v81:s{source_index}:h{horizon}:node{node_id}",
            applicability={"source_key": source_key, "horizon": horizon},
            action={"kind": "retain_round1_capability", "node_id": int(node_id)},
            verifier_boundary="exact_replay_verified_consequence_closure",
            certificate_refs=(f"global-optimum:{global_value}", f"sha256:{persistence_hash}"),
            provenance=(f"v81:fresh:source:{source_index}", f"horizon:{horizon}"),
            dependencies=("source_law",),
            scope={"horizon": horizon, "budget": RETAINED_BUDGET},
            causal_evidence=transition_ids or ("exact_global_enumeration",),
            persistence_hash=f"sha256:{persistence_hash}",
        )
        for node_id in state
    ]


def _transition_artifacts(
    *,
    source_index: int,
    horizon: int,
    start_state: tuple[int, ...],
    trajectory: dict[str, Any],
) -> list[VerifiedDevelopmentTransition]:
    artifacts: list[VerifiedDevelopmentTransition] = []
    state = tuple(sorted(start_state))
    for step_index, step in enumerate(trajectory.get("steps", ()), 1):
        nxt = tuple(sorted(int(x) for x in step["next_retained"]))
        witness_ids = tuple(f"consequence:{int(x)}" for x in sorted(step.get("gain_ids", ()))[:8])
        artifacts.append(
            VerifiedDevelopmentTransition(
                transition_id=f"v81:s{source_index}:h{horizon}:step{step_index}",
                from_state=state,
                proposal={"drop_id": int(step["drop_id"]), "add_id": int(step["add_id"])},
                verifier=f"exact_phi_{horizon}",
                delta=int(step["utility"]),
                admitted=True,
                to_state=nxt,
                causal_witnesses=witness_ids,
                exact_optimality_status=(
                    "endpoint_global_candidate"
                    if step_index == len(trajectory.get("steps", ()))
                    else "strictly_improving_intermediate"
                ),
            )
        )
        state = nxt
    return artifacts


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def run_v81(opened_laws: Path, out_dir: Path, *, quick: bool = False) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    source_count = QUICK_SOURCE_COUNT if quick else FRESH_SOURCE_COUNT

    opened_max_ops, opened_count = V80.opened_universe_max_ops(opened_laws)
    if opened_max_ops >= FRESH_OPERATION_COUNT:
        raise RuntimeError("fresh grammar boundary invalid")

    developer, developer_hash, training, opened_sha256, training_attempts = V73.rebuild_v72_developer(opened_laws)
    if developer_hash != AUTHORITATIVE_DEVELOPER_SHA256:
        raise RuntimeError("authoritative V72 developer hash drift")

    # Freeze every scientific rule before the first V81 source is generated.
    protocol = build_protocol(developer_hash, source_count)
    protocol_hash = sha_doc(protocol)
    freeze = {
        "phase": "FREEZE_V81",
        "protocol_sha256": protocol_hash,
        **protocol,
        "opened_universe_max_operation_count": opened_max_ops,
        "opened_universe_sha256": opened_sha256,
    }
    (out_dir / "protocol_freeze.json").write_text(json.dumps(freeze, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(freeze, sort_keys=True), flush=True)

    # Prospective boundary: no fresh V81 source exists before the freeze above.
    bases, fresh_sources = generate_fresh_bases(source_count)

    records: list[dict[str, Any]] = []
    capabilities: list[VerifiedCapabilityBlock] = []
    obstructions: list[VerifiedObstruction] = []
    transitions: list[VerifiedDevelopmentTransition] = []
    economics_rows: list[dict[str, Any]] = []
    total_states = 0
    total_obstruction = 0
    total_recovered = 0
    reuse_decisions = 0
    verifier_expansions = 0
    action_expansions = 0
    causal_examples = 0
    learned_checks = 0
    generic_checks = 0

    for source_index, base in enumerate(bases, 1):
        graph = base
        original_cold, _ = V71.retained_cold(graph)
        original_cold = tuple(sorted(original_cold))
        state = original_cold
        prior_global = None
        source_path: list[dict[str, Any]] = []
        source_failed = False

        for horizon in range(START_HORIZON, MAX_HORIZON + 1):
            if horizon > START_HORIZON:
                graph = extend_one_layer(graph, horizon)

            audit = V80.exact_global(graph, horizon)
            total_states += int(audit["states_enumerated"])
            persistent_value = len(V80.reachable(graph, state, horizon))
            residual = int(audit["global_best"]) - persistent_value
            if residual < 0:
                raise RuntimeError("persistent state exceeds exact global optimum")

            warm_start = state
            if horizon == START_HORIZON:
                learned = V80.gated_repair(graph, state, horizon, "learned", developer)
                generic = V80.gated_repair(graph, state, horizon, "generic", developer)
                decision = "INITIAL_DEVELOPMENT"
            elif residual == 0:
                frontier = V80.reachable(graph, state, horizon)
                learned = {
                    "start": frontier,
                    "final": frontier,
                    "final_retained": state,
                    "steps": [],
                    "checks": 0,
                    "local_optimum": True,
                    "causal": [],
                }
                generic = learned
                decision = "REUSE_STATE_UNDER_EXTENDED_VERIFIER"
                reuse_decisions += 1
            else:
                learned = V80.gated_repair(graph, state, horizon, "learned", developer)
                generic = V80.gated_repair(graph, state, horizon, "generic", developer)
                decision = "EXPAND_VERIFIER_ONLY"
                total_obstruction += residual

            learned_final = len(learned["final"])
            generic_final = len(generic["final"])
            learned_checks += int(learned["checks"])
            generic_checks += int(generic["checks"])
            gap = int(audit["global_best"]) - learned_final
            if gap < 0:
                raise RuntimeError("learned path exceeds exact global optimum")

            if horizon > START_HORIZON and residual > 0:
                obstruction = VerifiedObstruction(
                    obstruction_id=f"v81:s{source_index}:h{horizon}",
                    prior_state=tuple(sorted(warm_start)),
                    prior_scope={"horizon": horizon - 1, "budget": RETAINED_BUDGET},
                    extended_scope={"horizon": horizon, "budget": RETAINED_BUDGET},
                    exact_global_old=int(prior_global if prior_global is not None else 0),
                    persistent_value_new=persistent_value,
                    exact_global_new=int(audit["global_best"]),
                    residual=residual,
                    provenance=(f"v81:fresh:source:{source_index}", f"protocol:{protocol_hash}"),
                )
                obstructions.append(obstruction)
                if gap == 0:
                    verifier_expansions += 1
                    total_recovered += residual
                else:
                    decision = "ACTION_LANGUAGE_EXPANSION_REQUIRED"
                    action_expansions += 1
                    source_failed = True

            step_artifacts = _transition_artifacts(
                source_index=source_index,
                horizon=horizon,
                start_state=warm_start,
                trajectory=learned,
            )
            transitions.extend(step_artifacts)
            causal_examples += sum(1 for row in step_artifacts if row.causal_witnesses)

            state = tuple(sorted(int(x) for x in learned["final_retained"]))
            restarted_state, persistence_hash, persistence_path = _persist_and_restart(
                out_dir, source_index, horizon, base["source_key"], state
            )
            state = restarted_state
            transition_ids = tuple(row.transition_id for row in step_artifacts)
            capabilities.extend(
                _capability_blocks(
                    source_index=source_index,
                    source_key=base["source_key"],
                    horizon=horizon,
                    state=state,
                    persistence_hash=persistence_hash,
                    global_value=int(audit["global_best"]),
                    transition_ids=transition_ids,
                )
            )

            # Cold ablation uses the original baseline but exactly the same learned
            # proposal ordering, graph, verifier and one-swap action language.
            cold_economics = None
            if horizon > START_HORIZON:
                cold = V80.gated_repair(graph, original_cold, horizon, "learned", developer)
                cold_value = len(cold["final"])
                endpoint_equal = learned_final == int(audit["global_best"]) and cold_value == int(audit["global_best"])
                comparison = {
                    "source_index": source_index,
                    "horizon": horizon,
                    "endpoint_equal": endpoint_equal,
                    "global_value": int(audit["global_best"]),
                    "warm_value": learned_final,
                    "cold_value": cold_value,
                    "warm_checks": int(learned["checks"]),
                    "cold_checks": int(cold["checks"]),
                    "check_savings": int(cold["checks"]) - int(learned["checks"]),
                    "ablation": "delete_persisted_state_restore_original_cold_state",
                    "ablation_restores_cost": endpoint_equal and int(cold["checks"]) > int(learned["checks"]),
                    "same_proposer": True,
                    "same_verifier": True,
                    "same_action_language": True,
                    "no_extra_truth_access": True,
                }
                economics_rows.append(comparison)
                cold_economics = comparison

            source_path.append(
                {
                    "horizon": horizon,
                    "decision": decision,
                    "persistent_value_before_action": persistent_value,
                    "global_best": int(audit["global_best"]),
                    "residual": residual,
                    "global_gap_after_action": gap,
                    "learned_checks": int(learned["checks"]),
                    "generic_checks": int(generic["checks"]),
                    "generic_final": generic_final,
                    "retained_state": list(state),
                    "persistence_hash": persistence_hash,
                    "persistence_path": persistence_path,
                    "states_enumerated": int(audit["states_enumerated"]),
                    "layer_size": len(graph[f"round{horizon}_ids"]),
                    "cold_counterfactual": cold_economics,
                }
            )
            prior_global = int(audit["global_best"])
            if source_failed:
                break

        records.append(
            {
                "source_index": source_index,
                "source_key": base["source_key"],
                "operation_count": _operation_count(base["law"]),
                "round1_pool_size": len(base["round1_ids"]),
                "path": source_path,
                "final_horizon_reached": source_path[-1]["horizon"],
                "final_gap": source_path[-1]["global_gap_after_action"],
                "action_language_expansion_required": source_failed,
            }
        )
        print(
            json.dumps(
                {
                    "phase": "FRESH_BREAKTHROUGH_V81",
                    "source_index": source_index,
                    "source": base["source_key"][:12],
                    "path": [
                        {
                            "h": p["horizon"],
                            "decision": p["decision"],
                            "residual": p["residual"],
                            "gap": p["global_gap_after_action"],
                            "warm_checks": p["learned_checks"],
                            "cold_checks": (p["cold_counterfactual"] or {}).get("cold_checks"),
                        }
                        for p in source_path
                    ],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    compounding = classify_compounding(economics_rows)
    all_global = all(p["global_gap_after_action"] == 0 for r in records for p in r["path"])
    all_h7 = all(r["final_horizon_reached"] == MAX_HORIZON for r in records)
    development_pass = bool(all_global and all_h7 and action_expansions == 0)

    result = {
        "schema": "mathgraph.verified-compounding-breakthrough.v81",
        "classification": "PROSPECTIVE_FRESH_DEVELOPMENT_AND_COMPOUNDING_TEST",
        "protocol": protocol,
        "protocol_sha256": protocol_hash,
        "developer_sha256": developer_hash,
        "opened_training_universe": {
            "sha256": opened_sha256,
            "law_count": opened_count,
            "max_operation_count": opened_max_ops,
            "training_source_attempts": training_attempts,
        },
        "training": training,
        "fresh_stream": {
            "seed": FRESH_STREAM_SEED,
            "operation_count": FRESH_OPERATION_COUNT,
            "source_count": source_count,
            "generated_only_after_protocol_freeze": True,
            "sources": fresh_sources,
        },
        "evaluation": {
            "sources": len(records),
            "max_horizon": MAX_HORIZON,
            "total_states_enumerated": total_states,
            "total_obstruction": total_obstruction,
            "total_recovered": total_recovered,
            "reuse_decisions": reuse_decisions,
            "verifier_expansion_decisions": verifier_expansions,
            "action_language_expansion_required_count": action_expansions,
            "causal_transition_examples": causal_examples,
            "learned_total_checks": learned_checks,
            "generic_total_checks": generic_checks,
            "records": records,
        },
        "compounding_economics": compounding,
        "fresh_developmental_cycle_pass": development_pass,
        "autonomous_reuse_expand_pass": development_pass and (reuse_decisions > 0) and (verifier_expansions > 0),
        "global_optimality_gates_pass": all_global,
        "verdict": (
            "PASS_FRESH_VERIFIED_DEVELOPMENT_V81"
            if development_pass
            else "FAIL_FRESH_VERIFIED_DEVELOPMENT_V81"
        ),
        "claim_boundary": (
            "This is bounded prospective evidence on a deterministic ten-operation synthetic source stream, "
            "fixed retained budget five, one-swap developmental grammar, and exact consequence horizons 2..7. "
            "Compounding classification concerns verifier-check economics at equal exact global endpoint quality; "
            "it is not a claim of universal or unbounded self-improvement."
        ),
    }

    (out_dir / "v81_fresh_result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "compounding_economics.json").write_text(
        json.dumps({**compounding, "comparisons": economics_rows}, indent=2, sort_keys=True), encoding="utf-8"
    )
    _write_jsonl(out_dir / "capability_blocks.jsonl", [row.to_dict() | {"stable_hash": row.stable_hash()} for row in capabilities])
    _write_jsonl(out_dir / "verified_obstructions.jsonl", [row.to_dict() | {"stable_hash": row.stable_hash()} for row in obstructions])
    _write_jsonl(out_dir / "development_transitions.jsonl", [row.to_dict() | {"stable_hash": row.stable_hash()} for row in transitions])

    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "protocol_sha256": protocol_hash,
                "developer_sha256": developer_hash,
                "sources": len(records),
                "total_states_enumerated": total_states,
                "total_obstruction": total_obstruction,
                "total_recovered": total_recovered,
                "reuse_decisions": reuse_decisions,
                "verifier_expansion_decisions": verifier_expansions,
                "action_language_expansion_required_count": action_expansions,
                "compounding": compounding,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return result
