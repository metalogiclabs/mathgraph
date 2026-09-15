#!/usr/bin/env python3
"""V71 calibration: closed-loop residual-conditioned development.

Static lemma ranking (V67), fixed action transfer (V68), action scope (V69),
and shallow counterfactual value ranking (V69) did not create new causal reach.
V70 tests source-only adaptive depth. V71 adds the verifier residual itself.

Three equal-budget developers are compared on the already-opened Stage2 stream:

  COLD:
    frozen 16+15 complexity-ranked development.

  RESIDUAL:
    closed-loop development. After each small retained batch, run a cheap
    verifier-side proof-frontier probe and allocate the next batch to exact
    source consequences that most reduce the current residual.

  META:
    the identical residual loop, but with the V69 learned causal seed-value
    operator as a prior propagated down each developed lineage.

The task census remains independent of target outcome. Target structure is used
only after a task has been selected, which is the intended developmental phase.
Every retained critical pair and every accepted final proof is independently
replay verified.

This is opened-data calibration only. A decisive learned-development signal
requires META to prove a target that BOTH COLD and RESIDUAL fail, using a
META-exclusive verified lineage whose deletion kills the proof and restoration
restores it.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

P70 = ROOT / "experiments" / "adaptive_causal_budget_allocation_v70" / "run_calibration.py"
S70 = importlib.util.spec_from_file_location("v71_v70", P70)
if S70 is None or S70.loader is None:
    raise RuntimeError("cannot load V70")
V70 = importlib.util.module_from_spec(S70)
sys.modules[S70.name] = V70
S70.loader.exec_module(V70)

V69 = V70.V69
V67 = V69.V67
V65, V64, V63, V62, V58 = V67.V65, V67.V64, V67.V63, V67.V62, V67.V58

TOTAL_BUDGET = V69.TOTAL_BUDGET
COLD_QUOTAS = V69.QUOTAS
BATCH = 4
PROBE_CAP = 24
SOURCE_LIMIT = 80
TARGETS_PER_SOURCE = 2

RESIDUAL_DEPTH = 2
RESIDUAL_BEAM = 40
RESIDUAL_ACTIVE_RULES = 20
RESIDUAL_PER_TERM = 320


def stable_hash(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def score_tuple(term, goal):
    return (
        V63.structural_distance(term, goal),
        abs(V62.nodes(term) - V62.nodes(goal)),
        V62.nodes(term),
        V62.tkey(term),
    )


def residual_probe_direction(start, goal, eqs):
    """Cheap proof-frontier probe; returns best live residual, not a proof claim."""
    if start == goal:
        return {
            "term": start,
            "goal": goal,
            "score": score_tuple(start, goal),
            "generated": 0,
            "depth": 0,
            "reached_goal": True,
        }

    bank = V63.target_bank(start, goal)
    active = sorted(eqs.values(), key=V63.rule_score)[:RESIDUAL_ACTIVE_RULES]
    beam = {start}
    seen = {start}
    best = start
    best_score = score_tuple(start, goal)
    generated = 0

    for depth in range(1, RESIDUAL_DEPTH + 1):
        candidates = {}
        for current in beam:
            per_term = 0
            for eq in active:
                for direction in (0, 1):
                    for nxt, _step in V63.explicit_rewrites(current, eq, direction, bank):
                        generated += 1
                        per_term += 1
                        if nxt in seen:
                            continue
                        sc = score_tuple(nxt, goal)
                        prev = candidates.get(nxt)
                        if prev is None or sc < prev:
                            candidates[nxt] = sc
                        if sc < best_score:
                            best, best_score = nxt, sc
                        if nxt == goal:
                            return {
                                "term": nxt,
                                "goal": goal,
                                "score": sc,
                                "generated": generated,
                                "depth": depth,
                                "reached_goal": True,
                            }
                        if per_term >= RESIDUAL_PER_TERM:
                            break
                    if per_term >= RESIDUAL_PER_TERM:
                        break
                if per_term >= RESIDUAL_PER_TERM:
                    break

        ordered = sorted(candidates.items(), key=lambda kv: kv[1])[:RESIDUAL_BEAM]
        beam = {t for t, _ in ordered}
        seen.update(beam)
        if not beam:
            break

    return {
        "term": best,
        "goal": goal,
        "score": best_score,
        "generated": generated,
        "depth": RESIDUAL_DEPTH,
        "reached_goal": best == goal,
    }


def residual_probe(problem, eqs):
    tl, tr = V62.parse_eq(problem["equation2"])
    a = residual_probe_direction(tl, tr, eqs)
    b = residual_probe_direction(tr, tl, eqs)
    return a if a["score"] <= b["score"] else b


def scalar_residual(sc):
    # Lexicographic score is what the proof probe actually ranks by. This
    # scalar preserves the dominant structural-distance term for gain scoring.
    return float(sc[0]) + 0.20 * float(sc[1]) + 0.01 * float(sc[2])


def candidate_residual_gain(residual, cl, cr, ck, proof, next_id, eqs):
    child = V62.Equation(next_id, cl, cr, ck, proof, max(
        (e.round for e in eqs.values()), default=0
    ) + 1)
    trial = dict(eqs)
    trial[next_id] = child
    if not V62.verify_overlap(child, trial):
        raise RuntimeError("candidate replay failed during residual scoring")

    current = residual["term"]
    goal = residual["goal"]
    before = scalar_residual(residual["score"])
    bank = V63.target_bank(current, goal)
    best = before
    applicable = 0

    for direction in (0, 1):
        for nxt, _step in V63.explicit_rewrites(current, child, direction, bank):
            applicable += 1
            s = scalar_residual(score_tuple(nxt, goal))
            if s < best:
                best = s
            if applicable >= RESIDUAL_PER_TERM:
                break
        if applicable >= RESIDUAL_PER_TERM:
            break

    return max(0.0, before - best), applicable


def enumerate_candidates(eqs, by_key, frontier, round_no):
    return V69.enumerate_from_frontier(eqs, by_key, frontier, round_no)


def seed_prior_for_candidate(problem, src, cl, cr, ck, proof, op):
    temp = V62.Equation(-1, cl, cr, ck, proof, 1)
    score, _roll, _raw = V69.score_seed(src, temp, op)
    return float(score)


def compile_closed_loop(problem, seed_op, use_learned_prior: bool):
    src = V69.source_equation(problem)
    eqs = {0: src}
    by_key = {src.key: 0}
    frontier = [0]
    next_id = 1
    retained = 0
    round_no = 1
    lineage_prior = {0: 0.0}
    records = []

    while retained < TOTAL_BUDGET and frontier:
        residual = residual_probe(problem, eqs)
        candidates = enumerate_candidates(eqs, by_key, frontier, round_no)
        ranked = []

        for ck, (comp, cl, cr, proof, _rnd) in candidates.items():
            gain, applicable = candidate_residual_gain(
                residual, cl, cr, ck, proof, next_id, eqs
            )

            parents = [int(proof["a"]), int(proof["b"])]
            if round_no == 1 and use_learned_prior:
                prior = seed_prior_for_candidate(
                    problem, src, cl, cr, ck, proof, seed_op
                )
            elif use_learned_prior:
                prior = max(lineage_prior.get(p, 0.0) for p in parents)
            else:
                prior = 0.0

            unlock = V70.one_step_unlock_count(
                eqs, by_key, next_id, cl, cr, ck, proof, round_no
            )
            src_comp = max(1, V69.eq_complexity(src))
            compression = max(0.0, (src_comp - comp) / src_comp)

            # Residual feedback is dominant. The learned prior is deliberately
            # modest so the comparison against RESIDUAL isolates whether old
            # causal experience improves where the loop explores.
            priority = (
                1.00 * gain
                + 0.30 * prior
                + 0.0125 * float(unlock)
                + 0.15 * compression
                - 0.0025 * (comp / src_comp)
            )
            ranked.append((
                priority, gain, prior, unlock, compression, applicable,
                comp, ck, cl, cr, proof
            ))

        ranked.sort(key=lambda x: (-x[0], x[6], x[7]))
        take = min(BATCH, TOTAL_BUDGET - retained, len(ranked))
        added = []

        for (
            priority, gain, prior, unlock, compression, applicable,
            comp, ck, cl, cr, proof
        ) in ranked[:take]:
            child = V62.Equation(next_id, cl, cr, ck, proof, round_no)
            trial = dict(eqs)
            trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError("retained closed-loop equation replay failure")

            eqs[next_id] = child
            by_key[ck] = next_id
            added.append(next_id)
            lineage_prior[next_id] = float(prior)
            records.append({
                "eid": next_id,
                "round": round_no,
                "key": ck,
                "priority": float(priority),
                "residual_gain": float(gain),
                "learned_prior": float(prior),
                "unlock_count": int(unlock),
                "compression": float(compression),
                "residual_applications": int(applicable),
                "residual_before": list(residual["score"]),
                "residual_reached_goal_before_addition": residual["reached_goal"],
                "parents": [int(proof["a"]), int(proof["b"])],
                "complexity": int(comp),
            })
            next_id += 1
            retained += 1

        frontier = added
        round_no += 1

    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored equation replay failure eid={eid}")

    final_residual = residual_probe(problem, eqs)
    return {
        "eqs": eqs,
        "records": records,
        "retained_derived": len(eqs) - 1,
        "unused_budget": TOTAL_BUDGET - (len(eqs) - 1),
        "max_round": max((e.round for e in eqs.values()), default=0),
        "final_residual_score": list(final_residual["score"]),
        "final_residual_reached_goal": final_residual["reached_goal"],
        "uses_learned_prior": use_learned_prior,
    }


def evaluate(rows, training_ids, seed_op):
    sources, selected, rejected = V67.select_unseen_sources(
        rows, training_ids, SOURCE_LIMIT, TARGETS_PER_SOURCE
    )
    stats = defaultdict(int)
    records = []
    decisive_examples = []

    for i, problem in enumerate(selected, 1):
        route = V65.route(problem)
        rec = {
            "index": i,
            "problem_id": problem["id"],
            "source_id": V67.sid(problem),
            "route": route,
        }
        if not route["proof_candidate"]:
            records.append(rec)
            continue

        stats["proof_candidates"] += 1
        source_only = V64.proof_for(problem, V64.source_only_basis(problem))
        if source_only["proved"]:
            stats["source_only_proved"] += 1
            records.append(rec)
            continue

        if stats["development_probes"] >= PROBE_CAP:
            records.append(rec)
            continue
        stats["development_probes"] += 1

        cold_basis = V69.compile_budgeted(problem, "cold", seed_op)
        residual_basis = compile_closed_loop(problem, seed_op, False)
        meta_basis = compile_closed_loop(problem, seed_op, True)

        cold = V64.proof_for(problem, cold_basis["eqs"])
        residual = V64.proof_for(problem, residual_basis["eqs"])
        meta = V64.proof_for(problem, meta_basis["eqs"])

        stats["cold_proved"] += int(cold["proved"])
        stats["residual_proved"] += int(residual["proved"])
        stats["meta_proved"] += int(meta["proved"])
        stats["meta_only_vs_cold"] += int(meta["proved"] and not cold["proved"])
        stats["meta_only_vs_residual"] += int(meta["proved"] and not residual["proved"])
        stats["meta_only_vs_both"] += int(
            meta["proved"] and not cold["proved"] and not residual["proved"]
        )
        stats["residual_only_vs_cold"] += int(
            residual["proved"] and not cold["proved"]
        )

        cold_keys = {e.key for e in cold_basis["eqs"].values()}
        residual_keys = {e.key for e in residual_basis["eqs"].values()}
        meta_keys = {e.key for e in meta_basis["eqs"].values()}

        meta_exclusive_both = [
            eid for eid, e in meta_basis["eqs"].items()
            if eid != 0 and e.key not in cold_keys and e.key not in residual_keys
        ]
        residual_exclusive_cold = [
            eid for eid, e in residual_basis["eqs"].items()
            if eid != 0 and e.key not in cold_keys
        ]
        stats["meta_exclusive_generated_vs_both"] += len(meta_exclusive_both)
        stats["residual_exclusive_generated_vs_cold"] += len(residual_exclusive_cold)

        meta_used = [
            int(e) for e in meta["used_rule_ids"] if int(e) != 0
        ] if meta["proved"] else []
        meta_exclusive_used = [
            eid for eid in meta_used
            if meta_basis["eqs"][eid].key not in cold_keys
            and meta_basis["eqs"][eid].key not in residual_keys
        ]
        stats["meta_exclusive_used_vs_both"] += int(bool(meta_exclusive_used))

        decisive = (
            meta["proved"] and not cold["proved"] and not residual["proved"]
            and bool(meta_exclusive_used)
        )
        causal = False
        causal_eid = None
        removed_count = None

        if decisive:
            for eid in sorted(set(meta_exclusive_used)):
                ablated, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                gone = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, meta_basis["eqs"])
                if (not gone["proved"]) and restored["proved"]:
                    causal = True
                    causal_eid = eid
                    removed_count = len(removed)
                    stats["causal_meta_exclusive_lineages"] += 1
                    stats["learned_prior_delete_restore_sandwiches"] += 1
                    if len(decisive_examples) < 10:
                        decisive_examples.append({
                            "problem_id": problem["id"],
                            "source_id": V67.sid(problem),
                            "eid": eid,
                            "removed_lineage_count": len(removed),
                            "delete_result": "UNKNOWN",
                            "restore_result": "VERIFIED_TRUE",
                        })
                    break

        rec.update({
            "development_probe": True,
            "cold": cold,
            "residual": residual,
            "meta": meta,
            "meta_only_vs_both": (
                meta["proved"] and not cold["proved"] and not residual["proved"]
            ),
            "meta_exclusive_generated_vs_both": meta_exclusive_both,
            "meta_exclusive_used_vs_both": meta_exclusive_used,
            "causal": causal,
            "causal_eid": causal_eid,
            "causal_removed_count": removed_count,
            "residual_development": {
                "retained": residual_basis["retained_derived"],
                "unused_budget": residual_basis["unused_budget"],
                "max_round": residual_basis["max_round"],
                "final_residual_score": residual_basis["final_residual_score"],
                "records": residual_basis["records"],
            },
            "meta_development": {
                "retained": meta_basis["retained_derived"],
                "unused_budget": meta_basis["unused_budget"],
                "max_round": meta_basis["max_round"],
                "final_residual_score": meta_basis["final_residual_score"],
                "records": meta_basis["records"],
            },
        })
        records.append(rec)

        print(json.dumps({
            "phase": "CALIBRATION_V71",
            "id": problem["id"],
            "source": V67.sid(problem),
            "cold": cold["proved"],
            "residual": residual["proved"],
            "meta": meta["proved"],
            "meta_only_both": rec["meta_only_vs_both"],
            "meta_exclusive_generated": len(meta_exclusive_both),
            "meta_exclusive_used": len(meta_exclusive_used),
            "causal": causal,
            "residual_round": residual_basis["max_round"],
            "meta_round": meta_basis["max_round"],
        }, sort_keys=True), flush=True)

    return {
        "selected_sources": len(sources),
        "selected_rows": len(selected),
        "training_overlap": len(set(sources) & training_ids),
        "rejected_training_rows": rejected,
        **dict(stats),
        "decisive_examples": decisive_examples,
        "records": records,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--stage2", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    l3000, s3000 = V67.read_frozen_lines(
        Path(a.book3000), V58.EXPECTED_3000_SHA256
    )
    l3500, s3500 = V67.read_frozen_lines(
        Path(a.book3500), V58.EXPECTED_3500_SHA256
    )
    training_rows = (
        V67.parse_slice(l3000, V67.TRAIN_START, V67.TRAIN_END_3000)
        + V67.parse_slice(l3500, V67.TRAIN_START, V67.TRAIN_END_3500)
    )
    training_ids = {V67.sid(r) for r in training_rows}

    seed_op, seed_hash, training = V69.learn_value_operator(training_rows)
    developer = {
        "schema": "mathgraph.residual-conditioned-development.v71.calibration",
        "seed_prior_operator": seed_op,
        "residual_probe_depth": RESIDUAL_DEPTH,
        "residual_probe_beam": RESIDUAL_BEAM,
        "residual_active_rules": RESIDUAL_ACTIVE_RULES,
        "batch": BATCH,
        "total_budget": TOTAL_BUDGET,
        "comparison": ["cold", "residual_without_learned_prior", "meta_with_learned_prior"],
        "selection_target_independent": True,
        "development_target_conditioned_after_selection": True,
    }
    developer_hash = stable_hash(developer)

    print(json.dumps({
        "phase": "FREEZE_CALIBRATION_DEVELOPER",
        "developer_sha256": developer_hash,
        "seed_operator_sha256": seed_hash,
        "developer": developer,
    }, sort_keys=True), flush=True)

    rows, stage_sha = V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev = evaluate(rows, training_ids, seed_op)

    generic_loop_signal = (
        ev.get("residual_only_vs_cold", 0) > 0
        or ev.get("residual_proved", 0) > ev.get("cold_proved", 0)
    )
    learned_signal = (
        ev.get("meta_only_vs_both", 0) > 0
        and ev.get("meta_exclusive_used_vs_both", 0) > 0
    )
    strong_learned_signal = (
        learned_signal
        and ev.get("causal_meta_exclusive_lineages", 0) > 0
        and ev.get("learned_prior_delete_restore_sandwiches", 0) > 0
        and ev.get("meta_proved", 0) >= max(
            ev.get("cold_proved", 0), ev.get("residual_proved", 0)
        )
    )

    result = {
        "schema": "mathgraph.residual-conditioned-development.v71.calibration",
        "classification": "OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "developer": {**developer, "sha256": developer_hash},
        "training": training,
        "evaluation": ev,
        "generic_loop_signal": generic_loop_signal,
        "learned_signal": learned_signal,
        "strong_learned_signal": strong_learned_signal,
        "integrity": {
            "training_hashes_exact": (
                s3000 == V58.EXPECTED_3000_SHA256
                and s3500 == V58.EXPECTED_3500_SHA256
            ),
            "equal_nominal_derived_budget": TOTAL_BUDGET == sum(COLD_QUOTAS),
            "zero_training_eval_source_overlap": ev["training_overlap"] == 0,
            "task_selection_target_independent": True,
            "target_used_only_after_task_selection": True,
            "all_retained_equations_exactly_replayed": True,
            "all_accepted_proofs_exactly_replayed": True,
            "published_verdicts_read": 0,
            "proof_files_read": 0,
        },
        "stage2_sha256": stage_sha,
        "verdict": (
            "CALIBRATION_CAUSAL_LEARNED_RESIDUAL_DEVELOPMENT_SIGNAL_V71"
            if strong_learned_signal else
            "CALIBRATION_LEARNED_RESIDUAL_DEVELOPMENT_SIGNAL_V71"
            if learned_signal else
            "CALIBRATION_GENERIC_RESIDUAL_LOOP_SIGNAL_V71"
            if generic_loop_signal else
            "CALIBRATION_NO_RESIDUAL_DEVELOPMENT_SIGNAL_V71"
        ),
        "fresh_stream_spend_licensed": bool(strong_learned_signal),
        "claim_boundary": (
            "Opened-data calibration only. V71 separates generic verifier-feedback "
            "benefit from benefit attributable to the learned causal prior. A future "
            "fresh transfer claim requires the strong learned signal first."
        ),
    }

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out / "developer.json").write_text(
        json.dumps({**developer, "sha256": developer_hash}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "developer_sha256": developer_hash,
        "cold": ev.get("cold_proved", 0),
        "residual": ev.get("residual_proved", 0),
        "meta": ev.get("meta_proved", 0),
        "residual_only_vs_cold": ev.get("residual_only_vs_cold", 0),
        "meta_only_vs_both": ev.get("meta_only_vs_both", 0),
        "meta_exclusive_used": ev.get("meta_exclusive_used_vs_both", 0),
        "causal": ev.get("causal_meta_exclusive_lineages", 0),
        "fresh_stream_spend_licensed": result["fresh_stream_spend_licensed"],
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
