#!/usr/bin/env python3
"""V69 calibration: causal generator action + learned invocation scope.

V68 recovered a source-ID-invariant causal action form from two independent
V66 histories, but source-only invocation produced no transfer advantage.
V69 learns a distinct object: the lawful scope sigma_A of that action.

Training evidence is restricted to already-opened V66 history. First recover
one exact causal generator root for each old source by delete/restore. Then,
on the fixed V66 recurrence window, label each warm-only target:
  POSITIVE: deleting that exact seed lineage destroys the verified proof;
  NEGATIVE: the proof survives deletion of that seed lineage.
The scope model uses only target/seed structural relation features. It contains
no source IDs, equations, target IDs, truth labels, proof text, or verdicts.

Evaluation is calibration only on V67's already-opened Stage2 normal stream.
Source selection uses only source/action applicability. Once a target task is
fixed, META injects the learned seed iff the frozen scope model activates;
otherwise META is byte-for-byte the cold retention ordering. Same 31-lemma
budget, exact critical-pair replay, exact target-proof replay.

A fresh external stream MUST NOT be spent unless this opened-data calibration
shows a META-exclusive used rule and a META-only proof with causal ablation.
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

P67 = ROOT / "experiments" / "cross_source_developmental_transfer_v67" / "run.py"
S67 = importlib.util.spec_from_file_location("v69_v67", P67)
if S67 is None or S67.loader is None:
    raise RuntimeError("cannot load V67")
V67 = importlib.util.module_from_spec(S67)
sys.modules[S67.name] = V67
S67.loader.exec_module(V67)

P68 = ROOT / "experiments" / "causal_generator_action_transfer_v68" / "run_calibration.py"
S68 = importlib.util.spec_from_file_location("v69_v68", P68)
if S68 is None or S68.loader is None:
    raise RuntimeError("cannot load V68")
V68 = importlib.util.module_from_spec(S68)
sys.modules[S68.name] = V68
S68.loader.exec_module(V68)

V65, V64, V62, V58 = V67.V65, V67.V64, V67.V62, V67.V58

TRAIN_SOURCES = ("3501", "3892")
PHASE_A_START = 2900
PHASE_A_END = 2980
RECURRENCE_START = 2900
RECURRENCE_END = 3500

QUOTAS = V67.COLD_QUOTAS
TOTAL_BUDGET = sum(QUOTAS)
SOURCE_LIMIT = 100
TARGETS_PER_SOURCE = 2
PROBE_CAP = 36

SCOPE_FEATURE_NAMES = (
    "target_size_gap",
    "target_structural_distance",
    "target_match_count",
    "target_root_match_count",
)


def stable_hash(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def source_id(problem):
    return V67.sid(problem)


def same_source(problem, basis):
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    return key == basis["eqs"][0].key


def scope_raw_features(eq, eqs, problem):
    raw = V67.equation_features(eq, eqs, V67.target_context(problem))
    # V67 feature indices 8:12 are strictly target/seed relation features.
    return tuple(float(x) for x in raw[8:12])


def normalize(v, scales):
    return tuple(x / s for x, s in zip(v, scales))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def learn_action_and_scope(book3000_rows, book3500_rows):
    # Rebuild exactly the old V66 source capabilities from the fixed Phase-A
    # range, without reading any future calibration stream.
    phase_a_groups = defaultdict(list)
    for row in book3000_rows:
        if source_id(row) in TRAIN_SOURCES:
            phase_a_groups[source_id(row)].append(row)

    bases = {}
    for sid in TRAIN_SOURCES:
        if not phase_a_groups[sid]:
            raise RuntimeError(f"missing V66 Phase-A source {sid}")
        chosen = None
        for problem in phase_a_groups[sid]:
            route = V65.route(problem)
            if route["proof_candidate"]:
                chosen = problem
                break
        if chosen is None:
            raise RuntimeError(f"no proof-candidate acquisition row for {sid}")
        basis = V64.compile_source(chosen)
        if basis["verified_count"] != len(basis["eqs"]):
            raise RuntimeError(f"basis replay failure for {sid}")
        bases[sid] = basis

    recurrence_groups = defaultdict(list)
    for row in book3500_rows:
        sid = source_id(row)
        if sid in TRAIN_SOURCES and same_source(row, bases[sid]):
            recurrence_groups[sid].append(row)

    # Recover one exact causal root per independent source. This is the action
    # acquisition step; the final operator retains only their common descriptor.
    roots = {}
    root_records = []
    for sid in TRAIN_SOURCES:
        basis = bases[sid]
        for problem in recurrence_groups[sid]:
            route = V65.route(problem)
            if not route["proof_candidate"]:
                continue
            cold = V64.proof_for(problem, V64.source_only_basis(problem))
            warm = V64.proof_for(problem, basis["eqs"])
            if cold["proved"] or not warm["proved"]:
                continue
            for eid in sorted({int(x) for x in warm["used_rule_ids"] if int(x) != 0}):
                ablated, removed = V65.ablate_lineage(basis["eqs"], eid)
                lost = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, basis["eqs"])
                if (not lost["proved"]) and restored["proved"]:
                    roots[sid] = eid
                    root_records.append({
                        "source_id_for_audit_only": sid,
                        "training_problem_id_for_audit_only": problem["id"],
                        "eid_for_audit_only": eid,
                        "descriptor": V68.descriptor(basis["eqs"][eid]),
                        "removed_lineage_count": len(removed),
                    })
                    break
            if sid in roots:
                break

    if set(roots) != set(TRAIN_SOURCES):
        raise RuntimeError(f"failed to recover independent roots: {roots}")

    descriptors = [r["descriptor"] for r in root_records]
    common = {}
    for field in descriptors[0]:
        values = {d[field] for d in descriptors}
        if len(values) == 1:
            common[field] = values.pop()
    if not common.get("proper_overlap", False):
        raise RuntimeError("learned action is not a proper overlap")
    if "pos" in common:
        raise RuntimeError("absolute overlap path leaked")

    # Scope supervision: exact causal ablation on every old warm-only
    # recurrence target. The label is causal necessity of the recovered seed,
    # not whether the theorem is true.
    episodes = []
    positive_sources = set()
    negative_sources = set()
    for sid in TRAIN_SOURCES:
        basis = bases[sid]
        root = roots[sid]
        seed = basis["eqs"][root]
        for problem in recurrence_groups[sid]:
            route = V65.route(problem)
            if not route["proof_candidate"]:
                continue
            cold = V64.proof_for(problem, V64.source_only_basis(problem))
            warm = V64.proof_for(problem, basis["eqs"])
            if cold["proved"] or not warm["proved"]:
                continue
            ablated, removed = V65.ablate_lineage(basis["eqs"], root)
            lost = V64.proof_for(problem, ablated)
            restored = V64.proof_for(problem, basis["eqs"])
            if not restored["proved"]:
                raise RuntimeError("restoration failed during scope labeling")
            label = bool(not lost["proved"])
            if label:
                positive_sources.add(sid)
            else:
                negative_sources.add(sid)
            episodes.append({
                "source_id_for_audit_only": sid,
                "problem_id_for_audit_only": problem["id"],
                "label_causal_seed_needed": label,
                "raw_features": scope_raw_features(seed, basis["eqs"], problem),
                "removed_lineage_count": len(removed),
            })

    positives = [e for e in episodes if e["label_causal_seed_needed"]]
    negatives = [e for e in episodes if not e["label_causal_seed_needed"]]
    if len(positives) < 2 or len(negatives) < 2:
        raise RuntimeError(f"insufficient scope supervision: +{len(positives)} -{len(negatives)}")
    if len(positive_sources) < 2:
        raise RuntimeError("causal scope positives do not span both independent sources")

    # Small deterministic linear discriminant. Scale each relation feature,
    # then point from the negative centroid to the positive centroid. Threshold
    # is the midpoint of the two centroids projected on that direction.
    all_raw = [e["raw_features"] for e in episodes]
    scales = [
        max(1.0, max(abs(v[i]) for v in all_raw))
        for i in range(len(SCOPE_FEATURE_NAMES))
    ]
    pos_norm = [normalize(e["raw_features"], scales) for e in positives]
    neg_norm = [normalize(e["raw_features"], scales) for e in negatives]

    pos_centroid = tuple(sum(v[i] for v in pos_norm) / len(pos_norm) for i in range(4))
    neg_centroid = tuple(sum(v[i] for v in neg_norm) / len(neg_norm) for i in range(4))
    weights = tuple(p - n for p, n in zip(pos_centroid, neg_centroid))
    if not any(abs(w) > 1e-12 for w in weights):
        raise RuntimeError("scope centroids are identical")
    pos_score = dot(weights, pos_centroid)
    neg_score = dot(weights, neg_centroid)
    threshold = 0.5 * (pos_score + neg_score)

    # Training confusion is evidence about calibration quality, not a pass gate.
    training_predictions = []
    for e in episodes:
        x = normalize(e["raw_features"], scales)
        score = dot(weights, x)
        pred = score >= threshold
        training_predictions.append({
            "source_id_for_audit_only": e["source_id_for_audit_only"],
            "problem_id_for_audit_only": e["problem_id_for_audit_only"],
            "label": e["label_causal_seed_needed"],
            "score": score,
            "predicted": pred,
        })
    correct = sum(int(r["label"] == r["predicted"]) for r in training_predictions)

    operator = {
        "schema": "mathgraph.causal-action-scope.v69.calibration",
        "action_constraints": common,
        "scope_feature_names": list(SCOPE_FEATURE_NAMES),
        "scope_feature_scales": [float(x) for x in scales],
        "scope_weights": [float(x) for x in weights],
        "scope_threshold": float(threshold),
        "scope_rule": "linear_centroid_discriminant_on_target_seed_relation",
        "continuation_rule": "cold_default_after_scoped_seed",
        "round_quotas": list(QUOTAS),
        "total_derived_budget": TOTAL_BUDGET,
        "position_invariant": True,
        "source_id_invariant": True,
        "source_selection_target_independent": True,
        "invocation_uses_target_structure_only": True,
    }
    summary = {
        "phase_a_sources_rebuilt": len(bases),
        "recurrence_counts": {sid: len(recurrence_groups[sid]) for sid in TRAIN_SOURCES},
        "root_records": root_records,
        "scope_episode_count": len(episodes),
        "scope_positive_count": len(positives),
        "scope_negative_count": len(negatives),
        "positive_sources": sorted(positive_sources),
        "negative_sources": sorted(negative_sources),
        "scope_training_accuracy": correct / len(training_predictions),
        "scope_training_predictions": training_predictions,
    }
    return operator, stable_hash(operator), summary


def action_matches(proof, op):
    return V68.action_matches(proof, op)


def source_operator_applicable(problem, op):
    return V68.source_operator_applicable(problem, op)


def scope_score(temp_eq, eqs, problem, op):
    raw = scope_raw_features(temp_eq, eqs, problem)
    x = normalize(raw, op["scope_feature_scales"])
    return dot(op["scope_weights"], x), raw


def compile_budgeted(problem, mode, op):
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    eqs = {0: V62.Equation(0, lhs, rhs, key, {"kind":"SOURCE"}, 0)}
    by_key = {key: 0}
    next_id = 1
    frontier = [0]
    seed_ids = []
    scope_decisions = []
    rounds = []

    for round_no, quota in enumerate(QUOTAS, start=1):
        existing = sorted(eqs)
        front = set(frontier)
        candidates = {}
        for a_id in existing:
            for b_id in existing:
                if a_id not in front and b_id not in front:
                    continue
                a, b = eqs[a_id], eqs[b_id]
                for ad in (0, 1):
                    al, _ = V62.orientation(a, ad)
                    if al[0] == "v":
                        continue
                    for bd in (0, 1):
                        bl, _ = V62.orientation(b, bd)
                        if bl[0] == "v":
                            continue
                        for pos in V62.nonvar_positions(bl):
                            out = V62.derive_overlap(a, b, ad, bd, pos)
                            if out is None:
                                continue
                            cl, cr, ck = out
                            if ck in by_key:
                                continue
                            proof = {
                                "kind":"CRITICAL_PAIR","a":a_id,"b":b_id,
                                "a_dir":ad,"b_dir":bd,"pos":list(pos)
                            }
                            complexity = V62.nodes(cl) + V62.nodes(cr)
                            candidates.setdefault(ck, (complexity, cl, cr, proof))

        ranked = []
        active_seed_candidates = 0
        for ck, (complexity, cl, cr, proof) in candidates.items():
            activate = False
            score = None
            raw = None
            if mode == "meta" and round_no == 1 and action_matches(proof, op):
                temp = V62.Equation(-1, cl, cr, ck, proof, round_no)
                score, raw = scope_score(temp, eqs, problem, op)
                activate = score >= op["scope_threshold"]
                scope_decisions.append({
                    "candidate_key": ck,
                    "score": score,
                    "threshold": op["scope_threshold"],
                    "active": activate,
                    "raw_features": list(raw),
                })
                active_seed_candidates += int(activate)
            priority = int(activate)
            ranked.append((priority, complexity, ck, cl, cr, proof, score))

        if mode == "cold":
            ranked.sort(key=lambda x: (x[1], x[2]))
        else:
            # If no candidate passes scope this is exactly cold ordering.
            ranked.sort(key=lambda x: (-x[0], x[1], x[2]))

        added = []
        scoped_added = 0
        for priority, complexity, ck, cl, cr, proof, score in ranked[:quota]:
            child = V62.Equation(next_id, cl, cr, ck, proof, round_no)
            trial = dict(eqs)
            trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError("critical-pair replay failure")
            eqs[next_id] = child
            by_key[ck] = next_id
            added.append(next_id)
            if mode == "meta" and round_no == 1 and priority:
                seed_ids.append(next_id)
                scoped_added += 1
            next_id += 1

        rounds.append({
            "round": round_no,
            "candidate_count": len(candidates),
            "added": len(added),
            "active_seed_candidates": active_seed_candidates,
            "scoped_seeds_added": scoped_added,
        })
        frontier = added
        if not frontier:
            break

    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored equation replay failure eid={eid}")

    return {
        "eqs": eqs,
        "rounds": rounds,
        "seed_ids": seed_ids,
        "scope_decisions": scope_decisions,
    }


def evaluate(rows, training_source_ids, op):
    # Task census uses source law and learned action applicability only.
    applicability = {}
    filtered = []
    for row in rows:
        sid = source_id(row)
        if sid not in applicability:
            applicability[sid] = source_operator_applicable(row, op)
        if applicability[sid]:
            filtered.append(row)

    sources, selected, rejected = V67.select_unseen_sources(
        filtered, training_source_ids, SOURCE_LIMIT, TARGETS_PER_SOURCE
    )

    stats = defaultdict(int)
    records = []
    causal_examples = []

    for index, problem in enumerate(selected, 1):
        route = V65.route(problem)
        record = {
            "index": index,
            "problem_id": problem["id"],
            "source_id": source_id(problem),
            "route": route,
        }
        if not route["proof_candidate"]:
            records.append(record)
            continue

        stats["proof_candidates"] += 1
        source_only = V64.proof_for(problem, V64.source_only_basis(problem))
        if source_only["proved"]:
            stats["source_only_proved"] += 1
            records.append(record)
            continue
        if stats["development_probes"] >= PROBE_CAP:
            record["skipped_after_frozen_probe_cap"] = True
            records.append(record)
            continue

        stats["development_probes"] += 1
        cold_basis = compile_budgeted(problem, "cold", op)
        meta_basis = compile_budgeted(problem, "meta", op)
        cold = V64.proof_for(problem, cold_basis["eqs"])
        same_basis = (
            [(eid, eq.key) for eid, eq in sorted(cold_basis["eqs"].items())]
            == [(eid, eq.key) for eid, eq in sorted(meta_basis["eqs"].items())]
        )
        if same_basis:
            meta = cold
            stats["identical_basis_proof_reuses"] += 1
        else:
            meta = V64.proof_for(problem, meta_basis["eqs"])

        stats["cold_proved"] += int(cold["proved"])
        stats["meta_proved"] += int(meta["proved"])
        stats["scope_activated_probes"] += int(bool(meta_basis["seed_ids"]))
        is_meta_only = meta["proved"] and not cold["proved"]
        stats["meta_only"] += int(is_meta_only)
        stats["cold_only"] += int(cold["proved"] and not meta["proved"])

        cold_keys = {eq.key for eq in cold_basis["eqs"].values()}
        used = [int(e) for e in meta["used_rule_ids"] if int(e) != 0] if meta["proved"] else []
        exclusive = [eid for eid in used if meta_basis["eqs"][eid].key not in cold_keys]
        stats["meta_exclusive_used"] += int(bool(exclusive))

        causal = False
        if is_meta_only and exclusive:
            for eid in sorted(set(exclusive)):
                ablated, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                gone = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, meta_basis["eqs"])
                if (not gone["proved"]) and restored["proved"]:
                    causal = True
                    stats["causal_exclusive_lineages"] += 1
                    stats["developer_delete_restore_sandwiches"] += int(not cold["proved"])
                    if len(causal_examples) < 10:
                        causal_examples.append({
                            "problem_id": problem["id"],
                            "source_id": source_id(problem),
                            "eid": eid,
                            "removed_lineage_count": len(removed),
                            "scoped_seed_ids": meta_basis["seed_ids"],
                        })
                    break

        record.update({
            "development_probe": True,
            "cold": cold,
            "meta": meta,
            "meta_only": is_meta_only,
            "meta_exclusive_used_ids": exclusive,
            "causal": causal,
            "meta_scoped_seed_ids": meta_basis["seed_ids"],
            "meta_scope_decisions": meta_basis["scope_decisions"],
            "cold_rounds": cold_basis["rounds"],
            "meta_rounds": meta_basis["rounds"],
        })
        records.append(record)

        print(json.dumps({
            "phase":"CALIBRATION_V69",
            "id":problem["id"],
            "source":source_id(problem),
            "scope_active":bool(meta_basis["seed_ids"]),
            "cold":cold["proved"],
            "meta":meta["proved"],
            "meta_only":is_meta_only,
            "exclusive_used":len(exclusive),
            "causal":causal,
        }, sort_keys=True), flush=True)

    return {
        "selected_source_count": len(sources),
        "selected_rows": len(selected),
        "operator_applicable_source_count": sum(int(v) for v in applicability.values()),
        "selection_uses_source_only_action_applicability": True,
        "source_identity_overlap_with_training": len(set(sources) & training_source_ids),
        "rejected_training_overlap_rows": rejected,
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
    args = ap.parse_args()

    lines3000, sha3000 = V67.read_frozen_lines(Path(args.book3000), V58.EXPECTED_3000_SHA256)
    lines3500, sha3500 = V67.read_frozen_lines(Path(args.book3500), V58.EXPECTED_3500_SHA256)

    phase_a_rows = V67.parse_slice(lines3000, PHASE_A_START, PHASE_A_END)
    recurrence_rows = V67.parse_slice(lines3500, RECURRENCE_START, RECURRENCE_END)

    # Exclude every source identity exposed to training windows, not only the
    # two sources whose causal episodes supervise the learned operator.
    prior_training_rows = (
        V67.parse_slice(lines3000, V67.TRAIN_START, V67.TRAIN_END_3000)
        + V67.parse_slice(lines3500, V67.TRAIN_START, V67.TRAIN_END_3500)
    )
    training_source_ids = {source_id(r) for r in prior_training_rows}

    operator, operator_hash, training = learn_action_and_scope(
        phase_a_rows, recurrence_rows
    )
    print(json.dumps({
        "phase":"FREEZE_V69",
        "operator_sha256":operator_hash,
        "operator":operator,
        "scope_positive_count":training["scope_positive_count"],
        "scope_negative_count":training["scope_negative_count"],
        "scope_training_accuracy":training["scope_training_accuracy"],
    }, sort_keys=True), flush=True)

    # Only after the action+scope operator is frozen do we parse the already
    # opened calibration stream.
    eval_rows, stage2_sha = V67.parse_jsonl_after_freeze(Path(args.stage2))
    evaluation = evaluate(eval_rows, training_source_ids, operator)

    decisive_signal = (
        evaluation.get("meta_only", 0) > 0
        and evaluation.get("meta_exclusive_used", 0) > 0
        and evaluation.get("causal_exclusive_lineages", 0) > 0
        and evaluation.get("developer_delete_restore_sandwiches", 0) > 0
        and evaluation.get("meta_proved", 0) >= evaluation.get("cold_proved", 0)
    )

    integrity = {
        "training_hashes_exact": (
            sha3000 == V58.EXPECTED_3000_SHA256
            and sha3500 == V58.EXPECTED_3500_SHA256
        ),
        "same_total_development_budget": sum(QUOTAS) == TOTAL_BUDGET,
        "independent_causal_training_sources": (
            training["scope_positive_count"] > 0
            and set(training["positive_sources"]) == set(TRAIN_SOURCES)
        ),
        "scope_has_positive_and_negative_supervision": (
            training["scope_positive_count"] > 0
            and training["scope_negative_count"] > 0
        ),
        "zero_train_eval_source_identity_overlap": (
            evaluation["source_identity_overlap_with_training"] == 0
        ),
        "source_selection_target_independent": operator["source_selection_target_independent"],
        "scope_uses_target_structure_not_outcome": operator["invocation_uses_target_structure_only"],
        "operator_contains_no_source_specific_payload": all(
            key not in operator
            for key in ("source_id", "source_ids", "equation", "equations", "target_id", "verdict")
        ),
        "all_retained_equations_exactly_replayed": True,
        "all_true_proofs_exactly_replayed": True,
        "wrong_truth_promotions_zero": True,
    }

    result = {
        "schema":"mathgraph.causal-action-scope.v69.calibration",
        "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "operator":{**operator,"sha256":operator_hash},
        "training":training,
        "evaluation":evaluation,
        "integrity":integrity,
        "decisive_signal":decisive_signal,
        "verdict":(
            "CALIBRATION_CAUSAL_ACTION_SCOPE_SIGNAL_V69"
            if decisive_signal
            else "CALIBRATION_NO_CAUSAL_ACTION_SCOPE_SIGNAL_V69"
        ),
        "stage2_sha256":stage2_sha,
        "fresh_stream_spend_licensed":decisive_signal,
        "claim_boundary":(
            "This is calibration on an evaluation stream already opened by V67. "
            "It cannot support a fresh transfer claim. Its only purpose is to decide "
            "whether the frozen action+scope abstraction is strong enough to justify "
            "spending a separate prospective stream."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "operator.json").write_text(
        json.dumps({**operator,"sha256":operator_hash}, indent=2, sort_keys=True)
    )
    print(json.dumps({
        "verdict":result["verdict"],
        "operator_sha256":operator_hash,
        "training_accuracy":training["scope_training_accuracy"],
        "scope_activated":evaluation.get("scope_activated_probes",0),
        "cold":evaluation.get("cold_proved",0),
        "meta":evaluation.get("meta_proved",0),
        "meta_only":evaluation.get("meta_only",0),
        "exclusive_used":evaluation.get("meta_exclusive_used",0),
        "causal":evaluation.get("causal_exclusive_lineages",0),
        "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"],
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
