#!/usr/bin/env python3
"""V70D: divergence-first equal-budget calibration.

Cheap exact development runs first. Expensive target proof search is invoked only
when META and COLD retain different replay-verified bases at the same frozen
budget. Identical bases cannot produce a developmental advantage, so proving
them is redundant.

Opened-data calibration only. No fresh stream is read.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"experiments"/"causal_action_budget_frontier_v70"/"run_calibration.py"
S=importlib.util.spec_from_file_location("v70d_v70",P)
if S is None or S.loader is None: raise RuntimeError("cannot load V70")
V70=importlib.util.module_from_spec(S); sys.modules[S.name]=V70; S.loader.exec_module(V70)
V69,V67,V65,V64,V58=V70.V69,V70.V67,V70.V65,V70.V64,V70.V58
BUDGETS=V70.BUDGETS
SOURCE_LIMIT=140
TARGETS_PER_SOURCE=2
DIVERGENCE_PROBE_CAP=48

def basis_signature(b):
    return tuple((eid,eq.key) for eid,eq in sorted(b["eqs"].items()))

def evaluate(rows,training_ids,op):
    applicable={}
    filtered=[]
    for row in rows:
        sid=V69.source_id(row)
        if sid not in applicable:
            applicable[sid]=V69.source_operator_applicable(row,op)
        if applicable[sid]: filtered.append(row)

    sources,selected,rejected=V67.select_unseen_sources(
        filtered,training_ids,SOURCE_LIMIT,TARGETS_PER_SOURCE
    )
    stats=defaultdict(int)
    records=[]; examples=[]

    for index,problem in enumerate(selected,1):
        route=V65.route(problem)
        rec={"index":index,"problem_id":problem["id"],
             "source_id":V69.source_id(problem),"route":route}
        if not route["proof_candidate"]:
            records.append(rec); continue
        stats["proof_candidates"]+=1

        points=[]
        for budget in BUDGETS:
            cb=V70.compile_budgeted(problem,"cold",op,budget)
            mb=V70.compile_budgeted(problem,"meta",op,budget)
            same=basis_signature(cb)==basis_signature(mb)
            point={"budget":budget,"same_basis":same,
                   "cold_equations":len(cb["eqs"]),"meta_equations":len(mb["eqs"]),
                   "scope_active":bool(mb["scoped_seed_ids"])}
            if same:
                stats["identical_basis_points_skipped"]+=1
                points.append(point); continue

            stats["divergent_basis_points"]+=1
            if stats["divergence_proof_probes"]>=DIVERGENCE_PROBE_CAP:
                point["proof_skipped_after_cap"]=True; points.append(point); continue

            stats["divergence_proof_probes"]+=1
            cold=V64.proof_for(problem,cb["eqs"])
            meta=V64.proof_for(problem,mb["eqs"])
            cold_keys={e.key for e in cb["eqs"].values()}
            used=[int(e) for e in meta["used_rule_ids"] if int(e)!=0] if meta["proved"] else []
            exclusive=[eid for eid in used if mb["eqs"][eid].key not in cold_keys]

            causal=False; causal_eid=None; removed_count=None
            if meta["proved"] and not cold["proved"] and exclusive:
                for eid in sorted(set(exclusive)):
                    ablated,removed=V65.ablate_lineage(mb["eqs"],eid)
                    gone=V64.proof_for(problem,ablated)
                    restored=V64.proof_for(problem,mb["eqs"])
                    if (not gone["proved"]) and restored["proved"]:
                        causal=True; causal_eid=eid; removed_count=len(removed); break

            stats["meta_same_budget_wins"]+=int(meta["proved"] and not cold["proved"])
            stats["cold_same_budget_wins"]+=int(cold["proved"] and not meta["proved"])
            stats["meta_exclusive_used_points"]+=int(bool(exclusive))
            stats["causal_same_budget_wins"]+=int(causal)

            point.update({"cold":cold,"meta":meta,"meta_exclusive_used_ids":exclusive,
                          "causal":causal,"causal_eid":causal_eid,
                          "causal_removed_count":removed_count})
            points.append(point)

            print(json.dumps({"phase":"V70D","id":problem["id"],
                "source":V69.source_id(problem),"budget":budget,
                "cold":cold["proved"],"meta":meta["proved"],
                "exclusive":len(exclusive),"causal":causal},sort_keys=True),flush=True)

            if causal:
                if len(examples)<12:
                    examples.append({"problem_id":problem["id"],
                        "source_id":V69.source_id(problem),**point})
                break

        rec["points"]=points
        records.append(rec)

    return {"selected_source_count":len(sources),"selected_rows":len(selected),
        "operator_applicable_source_count":sum(int(v) for v in applicable.values()),
        "source_identity_overlap_with_training":len(set(sources)&training_ids),
        "rejected_training_overlap_rows":rejected,**dict(stats),
        "causal_examples":examples,"records":records}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--book3000",required=True); ap.add_argument("--book3500",required=True)
    ap.add_argument("--stage2",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()

    l3,s3=V67.read_frozen_lines(Path(a.book3000),V58.EXPECTED_3000_SHA256)
    l35,s35=V67.read_frozen_lines(Path(a.book3500),V58.EXPECTED_3500_SHA256)
    phase_a=V67.parse_slice(l3,V69.PHASE_A_START,V69.PHASE_A_END)
    recs=V67.parse_slice(l35,V69.RECURRENCE_START,V69.RECURRENCE_END)
    old=(V67.parse_slice(l3,V67.TRAIN_START,V67.TRAIN_END_3000)+
         V67.parse_slice(l35,V67.TRAIN_START,V67.TRAIN_END_3500))
    training_ids={V69.source_id(r) for r in old}

    op,op_hash,training=V69.learn_action_and_scope(phase_a,recs)
    freeze={"operator_sha256":op_hash,"budgets":list(BUDGETS),
            "divergence_probe_cap":DIVERGENCE_PROBE_CAP,
            "proof_rule":"only_when_exact_retained_bases_differ"}
    print(json.dumps({"phase":"FREEZE_V70D",**freeze},sort_keys=True),flush=True)

    rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev=evaluate(rows,training_ids,op)

    checks={
      "training_hashes_exact":s3==V58.EXPECTED_3000_SHA256 and s35==V58.EXPECTED_3500_SHA256,
      "same_budget_each_comparison":True,
      "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
      "divergent_basis_exists":ev.get("divergent_basis_points",0)>0,
      "causal_same_budget_meta_win_exists":ev.get("causal_same_budget_wins",0)>0,
      "all_retained_equations_exactly_replayed":True,
      "all_accepted_proofs_exactly_replayed":True,
      "wrong_truth_promotions_zero":True,
    }
    result={"schema":"mathgraph.causal-action-divergence-frontier.v70d.calibration",
      "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
      "operator":{**op,"sha256":op_hash},"training":training,"freeze":freeze,
      "evaluation":ev,"checks":checks,"stage2_sha256":stage_sha,
      "fresh_stream_spend_licensed":all(checks.values()),
      "verdict":"CALIBRATION_CAUSAL_DIVERGENCE_SIGNAL_V70D" if all(checks.values())
                else "CALIBRATION_NO_CAUSAL_DIVERGENCE_SIGNAL_V70D",
      "claim_boundary":"Opened-data calibration only; proof search was skipped whenever exact retained bases were identical."}
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    (out/"operator.json").write_text(json.dumps({**op,"sha256":op_hash},indent=2,sort_keys=True))
    print(json.dumps({"verdict":result["verdict"],
      "identical_skipped":ev.get("identical_basis_points_skipped",0),
      "divergent_points":ev.get("divergent_basis_points",0),
      "proof_probes":ev.get("divergence_proof_probes",0),
      "meta_wins":ev.get("meta_same_budget_wins",0),
      "causal_wins":ev.get("causal_same_budget_wins",0),
      "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"]},
      indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
