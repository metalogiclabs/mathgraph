#!/usr/bin/env python3
"""V69 calibration: learn counterfactual developmental value from causal lineages.

V67 learned which individual retained lemmas resembled successful proof lineages.
V68 learned a fixed causal generator-action descriptor. Neither generalized.

V69 changes the learned object. For each possible round-1 source/self critical-pair
intervention, it performs a tiny source-only verified rollout of that intervention's
descendant cone. Training labels are the exact causal V66 roots recovered by
delete/restore. A pairwise ranker learns which *consequences of an intervention*
distinguish causal roots from alternative interventions.

Evaluation is deliberately on the already-opened V67 Stage2 stream, so this is
calibration, not fresh evidence. COLD and META receive the same 16+15 derived
lemma budget. META changes only the round-1 allocation; round 2 returns to the
same cold complexity ordering. Every retained equation and accepted proof is
exactly replayed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P68 = ROOT / "experiments" / "causal_generator_action_transfer_v68" / "run_calibration.py"
S68 = importlib.util.spec_from_file_location("v69_v68", P68)
if S68 is None or S68.loader is None:
    raise RuntimeError("cannot load V68")
V68 = importlib.util.module_from_spec(S68)
sys.modules[S68.name] = V68
S68.loader.exec_module(V68)

V67 = V68.V67
V65, V64, V63, V62, V58 = V67.V65, V67.V64, V67.V63, V67.V62, V67.V58

QUOTAS = V67.COLD_QUOTAS
TOTAL_BUDGET = sum(QUOTAS)
SOURCE_LIMIT = 100
TARGETS_PER_SOURCE = 2
PROBE_CAP = 36
ROLLOUT_DEPTH = 2
ROLLOUT_PER_ROUND = 12

FEATURE_NAMES = (
    "seed_complexity_ratio",
    "seed_compression",
    "seed_side_balance_ratio",
    "seed_variable_ratio",
    "overlap_depth",
    "same_direction",
    "forward_forward",
    "rollout_total",
    "rollout_round1",
    "rollout_round2",
    "compressed_descendants",
    "min_complexity_ratio",
    "mean_complexity_ratio",
    "complexity_level_count",
    "nonvar_position_mass",
    "self_overlap_descendants",
)

def stable_hash(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

def source_equation(problem):
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    return V62.Equation(0, lhs, rhs, key, {"kind": "SOURCE"}, 0)

def eq_complexity(eq):
    return V62.nodes(eq.lhs) + V62.nodes(eq.rhs)

def add_candidate(candidates, by_key, a, b, ad, bd, pos, round_no):
    out = V62.derive_overlap(a, b, ad, bd, pos)
    if out is None:
        return
    cl, cr, ck = out
    if ck in by_key:
        return
    proof = {
        "kind": "CRITICAL_PAIR",
        "a": int(a.eid),
        "b": int(b.eid),
        "a_dir": int(ad),
        "b_dir": int(bd),
        "pos": list(pos),
    }
    comp = V62.nodes(cl) + V62.nodes(cr)
    candidates.setdefault(ck, (comp, cl, cr, proof, round_no))

def enumerate_from_frontier(eqs, by_key, frontier, round_no):
    candidates = {}
    front = set(frontier)
    existing = sorted(eqs)
    for aid in existing:
        for bid in existing:
            if aid not in front and bid not in front:
                continue
            a, b = eqs[aid], eqs[bid]
            for ad in (0, 1):
                al, _ = V62.orientation(a, ad)
                if al[0] == "v":
                    continue
                for bd in (0, 1):
                    bl, _ = V62.orientation(b, bd)
                    if bl[0] == "v":
                        continue
                    for pos in V62.nonvar_positions(bl):
                        add_candidate(candidates, by_key, a, b, ad, bd, pos, round_no)
    return candidates

def enumerate_round1(problem):
    src = source_equation(problem)
    candidates = enumerate_from_frontier({0: src}, {src.key: 0}, [0], 1)
    out = []
    for ck, (comp, cl, cr, proof, rnd) in candidates.items():
        eq = V62.Equation(-1, cl, cr, ck, proof, rnd)
        trial = {0: src, 1: V62.Equation(1, cl, cr, ck, {
            **proof, "a": 0, "b": 0
        }, rnd)}
        if not V62.verify_overlap(trial[1], trial):
            raise RuntimeError(f"round1 replay failed: {ck}")
        out.append(eq)
    out.sort(key=lambda e: (eq_complexity(e), e.key))
    return src, out

def rollout_seed(src, seed):
    seed1 = V62.Equation(1, seed.lhs, seed.rhs, seed.key, {
        **seed.proof, "a": 0, "b": 0
    }, 1)
    eqs = {0: src, 1: seed1}
    by_key = {src.key: 0, seed1.key: 1}
    frontier = [1]
    next_id = 2
    added_rounds = []
    self_overlap_desc = 0

    if not V62.verify_overlap(seed1, eqs):
        raise RuntimeError("seed replay failure")

    for rr in range(1, ROLLOUT_DEPTH + 1):
        candidates = enumerate_from_frontier(eqs, by_key, frontier, rr + 1)
        ranked = sorted(candidates.items(), key=lambda kv: (kv[1][0], kv[0]))
        added = []
        for ck, (comp, cl, cr, proof, rnd) in ranked[:ROLLOUT_PER_ROUND]:
            child = V62.Equation(next_id, cl, cr, ck, proof, rnd)
            trial = dict(eqs)
            trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError(f"rollout replay failure: {ck}")
            if int(proof["a"]) == int(proof["b"]):
                self_overlap_desc += 1
            eqs[next_id] = child
            by_key[ck] = next_id
            added.append(next_id)
            next_id += 1
        added_rounds.append(added)
        frontier = added
        if not frontier:
            while len(added_rounds) < ROLLOUT_DEPTH:
                added_rounds.append([])
            break

    descendants = [eqs[i] for i in sorted(eqs) if i != 0]
    comps = [eq_complexity(e) for e in descendants]
    src_comp = max(1, eq_complexity(src))
    compressed = sum(1 for c in comps[1:] if c < src_comp)
    nonvar_mass = 0
    for e in descendants:
        nonvar_mass += len(V62.nonvar_positions(e.lhs))
        nonvar_mass += len(V62.nonvar_positions(e.rhs))

    return {
        "total": len(descendants),
        "round_counts": [len(x) for x in added_rounds],
        "compressed_descendants": compressed,
        "min_complexity": min(comps) if comps else src_comp,
        "mean_complexity": (sum(comps) / len(comps)) if comps else float(src_comp),
        "complexity_levels": len(set(comps)),
        "nonvar_position_mass": nonvar_mass,
        "self_overlap_descendants": self_overlap_desc,
    }

def raw_features(src, seed, roll):
    sc = max(1, eq_complexity(src))
    ec = eq_complexity(seed)
    lhsn, rhsn = V62.nodes(seed.lhs), V62.nodes(seed.rhs)
    src_vars = max(1, len(V62.vars_of(src.lhs) | V62.vars_of(src.rhs)))
    seed_vars = len(V62.vars_of(seed.lhs) | V62.vars_of(seed.rhs))
    p = seed.proof
    rcounts = roll["round_counts"] + [0, 0]
    return (
        ec / sc,
        float(sc - ec),
        abs(lhsn - rhsn) / sc,
        seed_vars / src_vars,
        float(len(p["pos"])),
        float(int(p["a_dir"] == p["b_dir"])),
        float(int(p["a_dir"] == 0 and p["b_dir"] == 0)),
        float(roll["total"]),
        float(rcounts[0]),
        float(rcounts[1]),
        float(roll["compressed_descendants"]),
        roll["min_complexity"] / sc,
        roll["mean_complexity"] / sc,
        float(roll["complexity_levels"]),
        float(roll["nonvar_position_mass"]),
        float(roll["self_overlap_descendants"]),
    )

def norm(raw, scales):
    return tuple(x / s for x, s in zip(raw, scales))

def dot(w, x):
    return sum(a * b for a, b in zip(w, x))

def learn_value_operator(training_rows):
    _, _, causal_summary = V68.learn_operator(training_rows)
    roots = causal_summary["roots_per_source"]
    groups = dict(V67.training_groups(training_rows))

    episodes = []
    records = []
    for source, eids in sorted(roots.items()):
        group = groups[source]
        basis = V64.compile_source(group[0])
        positive_keys = {basis["eqs"][int(eid)].key for eid in eids}
        src, seeds = enumerate_round1(group[0])
        raw_rows = []
        positives = []
        negatives = []
        for seed in seeds:
            roll = rollout_seed(src, seed)
            raw = raw_features(src, seed, roll)
            is_pos = seed.key in positive_keys
            raw_rows.append({
                "positive": is_pos,
                "key": seed.key,
                "proof": seed.proof,
                "complexity": eq_complexity(seed),
                "rollout": roll,
                "raw": list(raw),
            })
            (positives if is_pos else negatives).append(raw)
        if not positives:
            raise RuntimeError(f"causal root not found among round1 actions for source {source}")
        if not negatives:
            raise RuntimeError(f"no counterfactual negative actions for source {source}")
        episodes.append((positives, negatives))
        records.append({
            "source_id": source,
            "causal_root_count": len(positives),
            "alternative_action_count": len(negatives),
            "actions": raw_rows,
        })

    all_raw = [v for p, n in episodes for v in (p + n)]
    scales = [
        max(1.0, max(abs(v[i]) for v in all_raw))
        for i in range(len(FEATURE_NAMES))
    ]
    weights = [0.0] * len(FEATURE_NAMES)
    updates = 0
    margin = 0.08
    lr = 0.20
    for _ in range(24):
        for pos, negs in episodes:
            for pr in pos:
                p = norm(pr, scales)
                for nr in negs:
                    n = norm(nr, scales)
                    if dot(weights, p) <= dot(weights, n) + margin:
                        for i in range(len(weights)):
                            weights[i] += lr * (p[i] - n[i])
                        updates += 1

    operator = {
        "schema": "mathgraph.counterfactual-developmental-value.v69.calibration",
        "feature_names": list(FEATURE_NAMES),
        "feature_scales": [float(x) for x in scales],
        "weights": [float(x) for x in weights],
        "rollout_depth": ROLLOUT_DEPTH,
        "rollout_per_round": ROLLOUT_PER_ROUND,
        "round_quotas": list(QUOTAS),
        "total_derived_budget": TOTAL_BUDGET,
        "round1_policy": "rank_source_self_interventions_by_verified_descendant_rollout_value",
        "later_policy": "cold_complexity_order",
        "target_independent": True,
        "training_rule": "pairwise_rank_exact_causal_ablation_roots_against_counterfactual_interventions",
    }
    summary = {
        "independent_sources": len(records),
        "pairwise_updates": updates,
        "causal_root_count": sum(r["causal_root_count"] for r in records),
        "alternative_action_count": sum(r["alternative_action_count"] for r in records),
        "records": records,
    }
    return operator, stable_hash(operator), summary

def score_seed(src, seed, op):
    roll = rollout_seed(src, seed)
    raw = raw_features(src, seed, roll)
    return dot(op["weights"], norm(raw, op["feature_scales"])), roll, raw

def compile_budgeted(problem, mode, op):
    src, round1 = enumerate_round1(problem)
    eqs = {0: src}
    by_key = {src.key: 0}
    next_id = 1

    scored = []
    for seed in round1:
        comp = eq_complexity(seed)
        if mode == "meta":
            score, roll, raw = score_seed(src, seed, op)
        else:
            score, roll, raw = 0.0, None, None
        scored.append((score, comp, seed.key, seed, roll, raw))
    if mode == "meta":
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    else:
        scored.sort(key=lambda x: (x[1], x[2]))

    added1 = []
    selected_scores = []
    for score, comp, ck, seed, roll, raw in scored[:QUOTAS[0]]:
        proof = {**seed.proof, "a": 0, "b": 0}
        child = V62.Equation(next_id, seed.lhs, seed.rhs, seed.key, proof, 1)
        trial = dict(eqs); trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("selected seed replay failure")
        eqs[next_id] = child; by_key[ck] = next_id; added1.append(next_id)
        selected_scores.append({
            "eid": next_id, "key": ck, "score": score, "complexity": comp,
            "rollout": roll, "raw": list(raw) if raw is not None else None,
        })
        next_id += 1

    candidates2 = enumerate_from_frontier(eqs, by_key, added1, 2)
    ranked2 = sorted(candidates2.items(), key=lambda kv: (kv[1][0], kv[0]))
    added2 = []
    for ck, (comp, cl, cr, proof, rnd) in ranked2[:QUOTAS[1]]:
        child = V62.Equation(next_id, cl, cr, ck, proof, 2)
        trial = dict(eqs); trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("round2 replay failure")
        eqs[next_id] = child; by_key[ck] = next_id; added2.append(next_id)
        next_id += 1

    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored replay failure {eid}")

    return {
        "eqs": eqs,
        "rounds": [
            {"round": 1, "candidates": len(round1), "added": len(added1)},
            {"round": 2, "candidates": len(candidates2), "added": len(added2)},
        ],
        "selected_round1": selected_scores,
    }

def evaluate(rows, training_ids, op):
    sources, selected, rejected = V67.select_unseen_sources(
        rows, training_ids, SOURCE_LIMIT, TARGETS_PER_SOURCE
    )
    stats = defaultdict(int)
    records = []
    examples = []
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
        base = V64.proof_for(problem, V64.source_only_basis(problem))
        if base["proved"]:
            stats["source_only_proved"] += 1
            records.append(rec)
            continue
        if stats["development_probes"] >= PROBE_CAP:
            records.append(rec)
            continue
        stats["development_probes"] += 1

        cold_basis = compile_budgeted(problem, "cold", op)
        meta_basis = compile_budgeted(problem, "meta", op)
        cold = V64.proof_for(problem, cold_basis["eqs"])
        meta = V64.proof_for(problem, meta_basis["eqs"])
        stats["cold_proved"] += int(cold["proved"])
        stats["meta_proved"] += int(meta["proved"])
        meta_only = meta["proved"] and not cold["proved"]
        cold_only = cold["proved"] and not meta["proved"]
        stats["meta_only"] += int(meta_only)
        stats["cold_only"] += int(cold_only)

        cold_keys = {e.key for e in cold_basis["eqs"].values()}
        meta_keys = {e.key for e in meta_basis["eqs"].values()}
        meta_exclusive_generated = [
            eid for eid, e in meta_basis["eqs"].items()
            if eid != 0 and e.key not in cold_keys
        ]
        cold_exclusive_generated = [
            eid for eid, e in cold_basis["eqs"].items()
            if eid != 0 and e.key not in meta_keys
        ]
        stats["meta_exclusive_generated"] += len(meta_exclusive_generated)
        stats["cold_exclusive_generated"] += len(cold_exclusive_generated)

        meta_used = [int(e) for e in meta["used_rule_ids"] if int(e) != 0] if meta["proved"] else []
        exclusive_used = [
            eid for eid in meta_used
            if meta_basis["eqs"][eid].key not in cold_keys
        ]
        stats["meta_exclusive_used"] += int(bool(exclusive_used))

        causal = False
        if meta_only and exclusive_used:
            for eid in exclusive_used:
                ablated, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                gone = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, meta_basis["eqs"])
                if not gone["proved"] and restored["proved"]:
                    causal = True
                    stats["causal_lineages"] += 1
                    if len(examples) < 10:
                        examples.append({
                            "problem_id": problem["id"],
                            "source_id": V67.sid(problem),
                            "eid": eid,
                            "removed": len(removed),
                            "delete_result": "UNKNOWN",
                            "restore_result": "VERIFIED_TRUE",
                        })
                    break

        rec.update({
            "cold": cold,
            "meta": meta,
            "meta_only": meta_only,
            "cold_only": cold_only,
            "meta_exclusive_generated_ids": meta_exclusive_generated,
            "meta_exclusive_used_ids": exclusive_used,
            "causal": causal,
            "cold_rounds": cold_basis["rounds"],
            "meta_rounds": meta_basis["rounds"],
            "cold_round1": cold_basis["selected_round1"],
            "meta_round1": meta_basis["selected_round1"],
        })
        records.append(rec)
        print(json.dumps({
            "phase": "CALIBRATION",
            "id": problem["id"],
            "source": V67.sid(problem),
            "cold": cold["proved"],
            "meta": meta["proved"],
            "meta_only": meta_only,
            "cold_only": cold_only,
            "meta_exclusive_generated": len(meta_exclusive_generated),
            "exclusive_used": len(exclusive_used),
            "causal": causal,
        }, sort_keys=True), flush=True)

    return {
        "selected_sources": len(sources),
        "selected_rows": len(selected),
        "training_overlap": len(set(sources) & training_ids),
        "rejected_training_rows": rejected,
        **dict(stats),
        "causal_examples": examples,
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

    op, op_hash, training = learn_value_operator(training_rows)
    print(json.dumps({
        "phase": "FREEZE_CALIBRATION_OPERATOR",
        "operator_sha256": op_hash,
        "operator": op,
    }, sort_keys=True), flush=True)

    rows, stage_sha = V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev = evaluate(rows, training_ids, op)
    signal = (
        ev.get("meta_only", 0) > 0
        or ev.get("meta_exclusive_used", 0) > 0
        or ev.get("meta_proved", 0) > ev.get("cold_proved", 0)
    )
    strong_signal = (
        ev.get("meta_only", 0) > 0
        and ev.get("causal_lineages", 0) > 0
        and ev.get("meta_proved", 0) >= ev.get("cold_proved", 0)
    )

    result = {
        "schema": "mathgraph.counterfactual-developmental-value.v69.calibration",
        "classification": "OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "operator": {**op, "sha256": op_hash},
        "training": training,
        "evaluation": ev,
        "integrity": {
            "training_hashes_exact": (
                s3000 == V58.EXPECTED_3000_SHA256
                and s3500 == V58.EXPECTED_3500_SHA256
            ),
            "same_total_budget": sum(QUOTAS) == TOTAL_BUDGET,
            "zero_training_eval_source_overlap": ev["training_overlap"] == 0,
            "operator_target_independent": op["target_independent"],
            "counterfactual_rollouts_exactly_replayed": True,
            "all_retained_equations_exactly_replayed": True,
            "all_accepted_proofs_exactly_replayed": True,
            "published_verdicts_read": 0,
            "proof_files_read": 0,
        },
        "stage2_sha256": stage_sha,
        "signal": signal,
        "strong_signal": strong_signal,
        "verdict": (
            "CALIBRATION_CAUSAL_COUNTERFACTUAL_VALUE_SIGNAL_V69"
            if strong_signal else
            "CALIBRATION_COUNTERFACTUAL_VALUE_SIGNAL_V69"
            if signal else
            "CALIBRATION_NO_COUNTERFACTUAL_VALUE_SIGNAL_V69"
        ),
        "claim_boundary": (
            "Calibration only. The Stage2 stream was opened by V67. V69 tests whether "
            "a source-only value function over verified intervention rollouts is a better "
            "developmental abstraction than V67 lemma ranking or V68 fixed action syntax."
        ),
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "operator.json").write_text(json.dumps({**op, "sha256": op_hash}, indent=2, sort_keys=True))
    print(json.dumps({
        "verdict": result["verdict"],
        "operator_sha256": op_hash,
        "cold": ev.get("cold_proved", 0),
        "meta": ev.get("meta_proved", 0),
        "meta_only": ev.get("meta_only", 0),
        "cold_only": ev.get("cold_only", 0),
        "meta_exclusive_generated": ev.get("meta_exclusive_generated", 0),
        "exclusive_used": ev.get("meta_exclusive_used", 0),
        "causal": ev.get("causal_lineages", 0),
    }, indent=2, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
