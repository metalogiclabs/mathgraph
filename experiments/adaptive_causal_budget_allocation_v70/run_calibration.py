#!/usr/bin/env python3
"""V70 calibration: adaptive causal budget allocation.

V69 counterfactual-value ranking was scientifically null because the frozen
16-rule first-round quota usually retained the same entire shallow action set as
COLD. V70 changes the *allocation geometry*, not the verifier or total budget.

Training is unchanged: recover V66 exact causal roots and learn a source-only
seed value function from tiny replay-verified descendant rollouts.

COLD: 16 shallow round-1 rules + 15 complexity-ranked round-2 rules.
META: retain only 8 highest-valued round-1 seeds, then spend the remaining
23-rule budget recursively. At each step, candidate descendants are valued by
(1) inherited learned seed value, (2) exact one-step counterfactual novelty
unlocked if the candidate is retained, and (3) structural compression.
Every retained equation is exact critical-pair replay verified.

Evaluation uses the already-opened V67 Stage2 stream and is calibration only.
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
P69 = ROOT / "experiments" / "counterfactual_developmental_value_v69" / "run_calibration.py"
S69 = importlib.util.spec_from_file_location("v70_v69", P69)
if S69 is None or S69.loader is None:
    raise RuntimeError("cannot load V69")
V69 = importlib.util.module_from_spec(S69)
sys.modules[S69.name] = V69
S69.loader.exec_module(V69)

V67 = V69.V67
V65, V64, V62, V58 = V69.V65, V69.V64, V69.V62, V69.V58

TOTAL_BUDGET = V69.TOTAL_BUDGET
COLD_QUOTAS = V69.QUOTAS
META_BREADTH = 8
META_REMAINING = TOTAL_BUDGET - META_BREADTH
ADAPTIVE_BATCH = 6
PROBE_CAP = V69.PROBE_CAP
SOURCE_LIMIT = V69.SOURCE_LIMIT
TARGETS_PER_SOURCE = V69.TARGETS_PER_SOURCE

def stable_hash(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

def child_complexity(cl, cr):
    return V62.nodes(cl) + V62.nodes(cr)

def one_step_unlock_count(eqs, by_key, next_id, cl, cr, ck, proof, round_no):
    child = V62.Equation(next_id, cl, cr, ck, proof, round_no)
    trial = dict(eqs)
    trial[next_id] = child
    if not V62.verify_overlap(child, trial):
        raise RuntimeError("counterfactual child replay failure")
    trial_keys = dict(by_key)
    trial_keys[ck] = next_id
    unlocked = V69.enumerate_from_frontier(trial, trial_keys, [next_id], round_no + 1)
    return len(unlocked)

def compile_adaptive(problem, op):
    src, seeds = V69.enumerate_round1(problem)
    src_comp = max(1, V69.eq_complexity(src))
    eqs = {0: src}
    by_key = {src.key: 0}
    next_id = 1

    scored = []
    for seed in seeds:
        score, roll, raw = V69.score_seed(src, seed, op)
        scored.append((score, V69.eq_complexity(seed), seed.key, seed, roll, raw))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))

    frontier = []
    lineage_score = {0: 0.0}
    seed_records = []
    for score, comp, ck, seed, roll, raw in scored[:META_BREADTH]:
        proof = {**seed.proof, "a": 0, "b": 0}
        child = V62.Equation(next_id, seed.lhs, seed.rhs, seed.key, proof, 1)
        trial = dict(eqs); trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("seed replay failure")
        eqs[next_id] = child
        by_key[ck] = next_id
        frontier.append(next_id)
        lineage_score[next_id] = float(score)
        seed_records.append({
            "eid": next_id,
            "key": ck,
            "score": float(score),
            "complexity": comp,
            "rollout": roll,
            "raw": list(raw),
        })
        next_id += 1

    adaptive_records = []
    remaining = TOTAL_BUDGET - len(frontier)
    round_no = 2
    while remaining > 0 and frontier:
        candidates = V69.enumerate_from_frontier(eqs, by_key, frontier, round_no)
        ranked = []
        for ck, (comp, cl, cr, proof, rnd) in candidates.items():
            parents = [int(proof["a"]), int(proof["b"])]
            inherited = max(lineage_score.get(p, 0.0) for p in parents)
            unlock = one_step_unlock_count(
                eqs, by_key, next_id, cl, cr, ck, proof, round_no
            )
            compression = max(0.0, (src_comp - comp) / src_comp)
            complexity_penalty = 0.04 * (comp / src_comp)
            priority = inherited + (unlock / 64.0) + 0.35 * compression - complexity_penalty
            ranked.append((
                priority, inherited, unlock, compression, comp, ck, cl, cr, proof
            ))
        ranked.sort(key=lambda x: (-x[0], x[4], x[5]))
        take = min(ADAPTIVE_BATCH, remaining, len(ranked))
        added = []
        for priority, inherited, unlock, compression, comp, ck, cl, cr, proof in ranked[:take]:
            child = V62.Equation(next_id, cl, cr, ck, proof, round_no)
            trial = dict(eqs); trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError("adaptive replay failure")
            eqs[next_id] = child
            by_key[ck] = next_id
            added.append(next_id)
            lineage_score[next_id] = inherited
            adaptive_records.append({
                "eid": next_id,
                "round": round_no,
                "key": ck,
                "priority": float(priority),
                "inherited_seed_value": float(inherited),
                "unlock_count": int(unlock),
                "compression": float(compression),
                "complexity": int(comp),
                "parents": [int(proof["a"]), int(proof["b"])],
            })
            next_id += 1
        remaining -= len(added)
        frontier = added
        round_no += 1

    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored adaptive equation replay failure {eid}")

    return {
        "eqs": eqs,
        "seed_records": seed_records,
        "adaptive_records": adaptive_records,
        "retained_derived": len(eqs) - 1,
        "unused_budget": max(0, TOTAL_BUDGET - (len(eqs) - 1)),
        "max_round": max((eq.round for eq in eqs.values()), default=0),
    }

def evaluate(rows, training_ids, op):
    sources, selected, rejected = V67.select_unseen_sources(
        rows, training_ids, SOURCE_LIMIT, TARGETS_PER_SOURCE
    )
    stats = defaultdict(int)
    records = []
    causal_examples = []

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

        cold_basis = V69.compile_budgeted(problem, "cold", op)
        meta_basis = compile_adaptive(problem, op)
        cold = V64.proof_for(problem, cold_basis["eqs"])
        meta = V64.proof_for(problem, meta_basis["eqs"])

        stats["cold_proved"] += int(cold["proved"])
        stats["meta_proved"] += int(meta["proved"])
        meta_only = meta["proved"] and not cold["proved"]
        cold_only = cold["proved"] and not meta["proved"]
        stats["meta_only"] += int(meta_only)
        stats["cold_only"] += int(cold_only)
        stats["meta_unused_budget_total"] += meta_basis["unused_budget"]

        cold_keys = {e.key for e in cold_basis["eqs"].values()}
        meta_keys = {e.key for e in meta_basis["eqs"].values()}
        meta_exclusive = [
            eid for eid, e in meta_basis["eqs"].items()
            if eid != 0 and e.key not in cold_keys
        ]
        cold_exclusive = [
            eid for eid, e in cold_basis["eqs"].items()
            if eid != 0 and e.key not in meta_keys
        ]
        stats["meta_exclusive_generated"] += len(meta_exclusive)
        stats["cold_exclusive_generated"] += len(cold_exclusive)

        meta_used = [int(e) for e in meta["used_rule_ids"] if int(e) != 0] if meta["proved"] else []
        exclusive_used = [
            eid for eid in meta_used if meta_basis["eqs"][eid].key not in cold_keys
        ]
        stats["meta_exclusive_used"] += int(bool(exclusive_used))

        causal = False
        if meta_only and exclusive_used:
            for eid in sorted(set(exclusive_used)):
                ablated, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                gone = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, meta_basis["eqs"])
                if (not gone["proved"]) and restored["proved"]:
                    causal = True
                    stats["causal_lineages"] += 1
                    if len(causal_examples) < 10:
                        causal_examples.append({
                            "problem_id": problem["id"],
                            "source_id": V67.sid(problem),
                            "eid": eid,
                            "removed_lineage_count": len(removed),
                            "delete_result": "UNKNOWN",
                            "restore_result": "VERIFIED_TRUE",
                        })
                    break

        rec.update({
            "cold": cold,
            "meta": meta,
            "meta_only": meta_only,
            "cold_only": cold_only,
            "causal": causal,
            "meta_exclusive_generated_ids": meta_exclusive,
            "meta_exclusive_used_ids": exclusive_used,
            "meta_retained_derived": meta_basis["retained_derived"],
            "meta_unused_budget": meta_basis["unused_budget"],
            "meta_max_round": meta_basis["max_round"],
            "meta_seed_records": meta_basis["seed_records"],
            "meta_adaptive_records": meta_basis["adaptive_records"],
        })
        records.append(rec)

        print(json.dumps({
            "phase": "CALIBRATION_V70",
            "id": problem["id"],
            "source": V67.sid(problem),
            "cold": cold["proved"],
            "meta": meta["proved"],
            "meta_only": meta_only,
            "cold_only": cold_only,
            "meta_exclusive_generated": len(meta_exclusive),
            "exclusive_used": len(exclusive_used),
            "causal": causal,
            "max_round": meta_basis["max_round"],
            "unused_budget": meta_basis["unused_budget"],
        }, sort_keys=True), flush=True)

    return {
        "selected_sources": len(sources),
        "selected_rows": len(selected),
        "training_overlap": len(set(sources) & training_ids),
        "rejected_training_rows": rejected,
        **dict(stats),
        "causal_examples": causal_examples,
        "records": records,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--stage2", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    l3000, s3000 = V67.read_frozen_lines(Path(a.book3000), V58.EXPECTED_3000_SHA256)
    l3500, s3500 = V67.read_frozen_lines(Path(a.book3500), V58.EXPECTED_3500_SHA256)
    training_rows = (
        V67.parse_slice(l3000, V67.TRAIN_START, V67.TRAIN_END_3000)
        + V67.parse_slice(l3500, V67.TRAIN_START, V67.TRAIN_END_3500)
    )
    training_ids = {V67.sid(r) for r in training_rows}

    seed_op, seed_hash, training = V69.learn_value_operator(training_rows)
    developer = {
        "schema": "mathgraph.adaptive-causal-budget-allocation.v70.calibration",
        "seed_value_operator": seed_op,
        "meta_breadth": META_BREADTH,
        "total_budget": TOTAL_BUDGET,
        "adaptive_batch": ADAPTIVE_BATCH,
        "adaptive_priority": "inherited_seed_value_plus_exact_one_step_unlock_plus_compression",
        "target_independent": True,
    }
    dev_hash = stable_hash(developer)
    print(json.dumps({
        "phase": "FREEZE_CALIBRATION_DEVELOPER",
        "developer_sha256": dev_hash,
        "seed_operator_sha256": seed_hash,
        "developer": developer,
    }, sort_keys=True), flush=True)

    rows, stage_sha = V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev = evaluate(rows, training_ids, seed_op)

    signal = (
        ev.get("meta_exclusive_generated", 0) > 0
        and (
            ev.get("meta_only", 0) > 0
            or ev.get("meta_exclusive_used", 0) > 0
            or ev.get("meta_proved", 0) > ev.get("cold_proved", 0)
        )
    )
    strong_signal = (
        ev.get("meta_only", 0) > 0
        and ev.get("causal_lineages", 0) > 0
        and ev.get("meta_proved", 0) >= ev.get("cold_proved", 0)
        and ev.get("meta_unused_budget_total", 0) == 0
    )

    result = {
        "schema": "mathgraph.adaptive-causal-budget-allocation.v70.calibration",
        "classification": "OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "developer": {**developer, "sha256": dev_hash},
        "training": training,
        "evaluation": ev,
        "integrity": {
            "training_hashes_exact": (
                s3000 == V58.EXPECTED_3000_SHA256
                and s3500 == V58.EXPECTED_3500_SHA256
            ),
            "same_nominal_total_budget": TOTAL_BUDGET == sum(COLD_QUOTAS),
            "zero_training_eval_source_overlap": ev["training_overlap"] == 0,
            "developer_target_independent": True,
            "counterfactual_unlocks_exactly_replayed": True,
            "all_retained_equations_exactly_replayed": True,
            "all_accepted_proofs_exactly_replayed": True,
            "published_verdicts_read": 0,
            "proof_files_read": 0,
        },
        "stage2_sha256": stage_sha,
        "signal": signal,
        "strong_signal": strong_signal,
        "verdict": (
            "CALIBRATION_CAUSAL_ADAPTIVE_DEPTH_SIGNAL_V70"
            if strong_signal else
            "CALIBRATION_ADAPTIVE_DEPTH_SIGNAL_V70"
            if signal else
            "CALIBRATION_NO_ADAPTIVE_DEPTH_SIGNAL_V70"
        ),
        "claim_boundary": (
            "Calibration only on a stream opened by V67. V70 tests whether the "
            "developmental advantage lies in nonlinear allocation of a fixed verified "
            "budget into causally promising depth rather than shallow ranking."
        ),
    }

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "developer.json").write_text(json.dumps({**developer, "sha256": dev_hash}, indent=2, sort_keys=True))
    print(json.dumps({
        "verdict": result["verdict"],
        "developer_sha256": dev_hash,
        "cold": ev.get("cold_proved", 0),
        "meta": ev.get("meta_proved", 0),
        "meta_only": ev.get("meta_only", 0),
        "cold_only": ev.get("cold_only", 0),
        "meta_exclusive_generated": ev.get("meta_exclusive_generated", 0),
        "exclusive_used": ev.get("meta_exclusive_used", 0),
        "causal": ev.get("causal_lineages", 0),
        "unused_budget_total": ev.get("meta_unused_budget_total", 0),
    }, indent=2, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
