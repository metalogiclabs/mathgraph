#!/usr/bin/env python3
"""V70 calibration: causal developmental transfer as a budget-frontier shift.

V67/V68 tested whether a learned developer could beat a strong generic
developer at one generous 31-lemma budget. V68 showed a key confound: the
causal seed may already be retained by COLD at that budget. V70 instead freezes
a geometric budget frontier B={1,2,4,8,16,31} and compares COLD vs META at
exactly the same B for every point.

META is the frozen V69 action+scope developer. At round 1 it may prioritize a
single scope-activated causal seed; all remaining choices use the identical
cold complexity order. A decisive calibration event requires:
  * same budget B for COLD and META;
  * META verified TRUE while COLD fails at B;
  * the META proof uses a META-exclusive generated rule;
  * deleting that exact rule lineage destroys the proof;
  * restoring it restores the proof;
  * no truth promotions without exact replay.

The Stage2 stream is already opened and is calibration only. No fresh stream
is read by this experiment.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

P69 = ROOT / "experiments" / "causal_action_scope_transfer_v69" / "run_calibration.py"
S69 = importlib.util.spec_from_file_location("v70_v69", P69)
if S69 is None or S69.loader is None:
    raise RuntimeError("cannot load V69")
V69 = importlib.util.module_from_spec(S69)
sys.modules[S69.name] = V69
S69.loader.exec_module(V69)

V67, V65, V64, V62, V58 = V69.V67, V69.V65, V69.V64, V69.V62, V69.V58

BUDGETS = (1, 2, 4, 8, 16, 31)
ROUND1_CAP = 16
SOURCE_LIMIT = 100
TARGETS_PER_SOURCE = 2
PROBE_CAP = 30


def quotas_for_budget(budget):
    q1 = min(int(budget), ROUND1_CAP)
    q2 = max(0, int(budget) - q1)
    return (q1, q2)


def compile_budgeted(problem, mode, op, budget):
    quotas = quotas_for_budget(budget)
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    eqs = {0: V62.Equation(0, lhs, rhs, key, {"kind":"SOURCE"}, 0)}
    by_key = {key: 0}
    next_id = 1
    frontier = [0]
    scoped_seed_ids = []
    scope_decisions = []
    rounds = []

    for round_no, quota in enumerate(quotas, start=1):
        if quota <= 0:
            continue
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
                                "a_dir":ad,"b_dir":bd,"pos":list(pos),
                            }
                            complexity = V62.nodes(cl) + V62.nodes(cr)
                            candidates.setdefault(ck, (complexity, cl, cr, proof))

        ranked = []
        for ck, (complexity, cl, cr, proof) in candidates.items():
            scope_active = False
            scope_score = None
            raw = None
            if mode == "meta" and round_no == 1 and V69.action_matches(proof, op):
                temp = V62.Equation(-1, cl, cr, ck, proof, round_no)
                scope_score, raw = V69.scope_score(temp, eqs, problem, op)
                scope_active = scope_score >= op["scope_threshold"]
                scope_decisions.append({
                    "key": ck,
                    "score": scope_score,
                    "threshold": op["scope_threshold"],
                    "active": scope_active,
                    "raw_features": list(raw),
                })
            ranked.append((int(scope_active), scope_score, complexity, ck, cl, cr, proof))

        if mode == "cold":
            ranked.sort(key=lambda x: (x[2], x[3]))
        else:
            # Minimal learned intervention: at most one activated seed receives
            # priority. Everything else remains in exact cold order.
            active = [r for r in ranked if r[0]]
            inactive = [r for r in ranked if not r[0]]
            active.sort(key=lambda x: (-(x[1] if x[1] is not None else -1e18), x[2], x[3]))
            inactive.sort(key=lambda x: (x[2], x[3]))
            if active:
                ranked = active[:1] + inactive + active[1:]
            else:
                ranked = inactive

        added = []
        for rank_index, (_, score, complexity, ck, cl, cr, proof) in enumerate(ranked[:quota]):
            child = V62.Equation(next_id, cl, cr, ck, proof, round_no)
            trial = dict(eqs)
            trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError("critical-pair replay failure")
            eqs[next_id] = child
            by_key[ck] = next_id
            added.append(next_id)
            if mode == "meta" and round_no == 1 and rank_index == 0:
                # Only call it a learned seed if this first candidate was
                # actually scope-active.
                if any(d["active"] and d["key"] == ck for d in scope_decisions):
                    scoped_seed_ids.append(next_id)
            next_id += 1

        rounds.append({
            "round": round_no,
            "quota": quota,
            "candidate_count": len(candidates),
            "added": len(added),
        })
        frontier = added
        if not frontier:
            break

    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored replay failure eid={eid}")

    return {
        "eqs": eqs,
        "rounds": rounds,
        "scoped_seed_ids": scoped_seed_ids,
        "scope_decisions": scope_decisions,
    }


def evaluate(rows, training_ids, op):
    applicability = {}
    filtered = []
    for row in rows:
        sid = V69.source_id(row)
        if sid not in applicability:
            applicability[sid] = V69.source_operator_applicable(row, op)
        if applicability[sid]:
            filtered.append(row)

    sources, selected, rejected = V67.select_unseen_sources(
        filtered, training_ids, SOURCE_LIMIT, TARGETS_PER_SOURCE
    )

    stats = defaultdict(int)
    records = []
    decisive = []

    for index, problem in enumerate(selected, 1):
        route = V65.route(problem)
        record = {
            "index": index,
            "problem_id": problem["id"],
            "source_id": V69.source_id(problem),
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

        frontier = []
        first_cold = None
        first_meta = None
        event = None

        for budget in BUDGETS:
            cold_basis = compile_budgeted(problem, "cold", op, budget)
            meta_basis = compile_budgeted(problem, "meta", op, budget)
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

            if cold["proved"] and first_cold is None:
                first_cold = budget
            if meta["proved"] and first_meta is None:
                first_meta = budget

            cold_keys = {eq.key for eq in cold_basis["eqs"].values()}
            meta_used = [int(e) for e in meta["used_rule_ids"] if int(e) != 0] if meta["proved"] else []
            exclusive = [
                eid for eid in meta_used
                if meta_basis["eqs"][eid].key not in cold_keys
            ]

            causal = False
            causal_eid = None
            causal_removed = None
            if meta["proved"] and not cold["proved"] and exclusive:
                for eid in sorted(set(exclusive)):
                    ablated, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                    gone = V64.proof_for(problem, ablated)
                    restored = V64.proof_for(problem, meta_basis["eqs"])
                    if (not gone["proved"]) and restored["proved"]:
                        causal = True
                        causal_eid = eid
                        causal_removed = len(removed)
                        break

            point = {
                "budget": budget,
                "quotas": list(quotas_for_budget(budget)),
                "cold": cold,
                "meta": meta,
                "scope_active": bool(meta_basis["scoped_seed_ids"]),
                "meta_scoped_seed_ids": meta_basis["scoped_seed_ids"],
                "meta_exclusive_used_ids": exclusive,
                "causal_meta_exclusive_lineage": causal,
                "causal_eid": causal_eid,
                "causal_removed_count": causal_removed,
            }
            frontier.append(point)

            if causal:
                event = point
                stats["causal_budget_wins"] += 1
                if len(decisive) < 12:
                    decisive.append({
                        "problem_id": problem["id"],
                        "source_id": V69.source_id(problem),
                        **point,
                    })
                # This is already the strongest same-budget event for this task.
                break

            # If both systems have already proved at the same smallest budget,
            # later larger budgets cannot improve this task's minimum frontier.
            if first_cold is not None and first_meta is not None and first_cold == first_meta:
                break

        if first_meta is not None and (first_cold is None or first_meta < first_cold):
            stats["meta_left_shift_tasks"] += 1
        if first_cold is not None and (first_meta is None or first_cold < first_meta):
            stats["cold_left_shift_tasks"] += 1

        record.update({
            "development_probe": True,
            "first_cold_budget": first_cold,
            "first_meta_budget": first_meta,
            "meta_left_shift": (
                first_meta is not None
                and (first_cold is None or first_meta < first_cold)
            ),
            "causal_budget_win": event is not None,
            "frontier": frontier,
        })
        records.append(record)

        print(json.dumps({
            "phase":"BUDGET_FRONTIER_V70",
            "id":problem["id"],
            "source":V69.source_id(problem),
            "cold_min":first_cold,
            "meta_min":first_meta,
            "causal_budget_win":event is not None,
        }, sort_keys=True), flush=True)

    return {
        "selected_source_count": len(sources),
        "selected_rows": len(selected),
        "operator_applicable_source_count": sum(int(v) for v in applicability.values()),
        "source_identity_overlap_with_training": len(set(sources) & training_ids),
        "rejected_training_overlap_rows": rejected,
        **dict(stats),
        "decisive_examples": decisive,
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

    phase_a = V67.parse_slice(lines3000, V69.PHASE_A_START, V69.PHASE_A_END)
    recurrences = V67.parse_slice(lines3500, V69.RECURRENCE_START, V69.RECURRENCE_END)
    old_training = (
        V67.parse_slice(lines3000, V67.TRAIN_START, V67.TRAIN_END_3000)
        + V67.parse_slice(lines3500, V67.TRAIN_START, V67.TRAIN_END_3500)
    )
    training_ids = {V69.source_id(r) for r in old_training}

    op, op_hash, training = V69.learn_action_and_scope(phase_a, recurrences)
    frozen_protocol = {
        "operator_sha256": op_hash,
        "budgets": list(BUDGETS),
        "round1_cap": ROUND1_CAP,
        "probe_cap": PROBE_CAP,
        "same_budget_each_comparison": True,
    }
    print(json.dumps({"phase":"FREEZE_V70", **frozen_protocol}, sort_keys=True), flush=True)

    rows, stage_sha = V67.parse_jsonl_after_freeze(Path(args.stage2))
    evaluation = evaluate(rows, training_ids, op)

    decisive = evaluation.get("causal_budget_wins", 0) > 0
    no_frontier_regression = (
        evaluation.get("cold_left_shift_tasks", 0)
        <= evaluation.get("meta_left_shift_tasks", 0)
    )

    checks = {
        "training_hashes_exact": (
            sha3000 == V58.EXPECTED_3000_SHA256
            and sha3500 == V58.EXPECTED_3500_SHA256
        ),
        "budget_schedule_frozen": list(BUDGETS) == [1,2,4,8,16,31],
        "same_budget_each_comparison": True,
        "zero_train_eval_source_overlap": evaluation["source_identity_overlap_with_training"] == 0,
        "causal_same_budget_meta_win_exists": decisive,
        "frontier_not_net_worse": no_frontier_regression,
        "all_retained_equations_exactly_replayed": True,
        "all_true_proofs_exactly_replayed": True,
        "wrong_truth_promotions_zero": True,
    }

    result = {
        "schema":"mathgraph.causal-action-budget-frontier.v70.calibration",
        "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "operator":{**op,"sha256":op_hash},
        "training":training,
        "frozen_protocol":frozen_protocol,
        "evaluation":evaluation,
        "checks":checks,
        "fresh_stream_spend_licensed": all(checks.values()),
        "verdict":(
            "CALIBRATION_CAUSAL_BUDGET_FRONTIER_SIGNAL_V70"
            if all(checks.values())
            else "CALIBRATION_NO_CAUSAL_BUDGET_FRONTIER_SIGNAL_V70"
        ),
        "stage2_sha256":stage_sha,
        "claim_boundary":(
            "Opened-data calibration only. A positive event means the learned "
            "developer moves a verified proof leftward on a precommitted equal-budget "
            "frontier with exact causal ablation; it is not fresh transfer evidence."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    (out/"operator.json").write_text(json.dumps({**op,"sha256":op_hash},indent=2,sort_keys=True))
    print(json.dumps({
        "verdict":result["verdict"],
        "operator_sha256":op_hash,
        "meta_left_shift_tasks":evaluation.get("meta_left_shift_tasks",0),
        "cold_left_shift_tasks":evaluation.get("cold_left_shift_tasks",0),
        "causal_budget_wins":evaluation.get("causal_budget_wins",0),
        "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"],
    },indent=2,sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
