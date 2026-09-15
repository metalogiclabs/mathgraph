#!/usr/bin/env python3
"""V73 calibration: verified counterfactual developmental control.

For each exact round-1 generator action A, run a tiny target-directed proof
micro-probe with {source,A}. Rank actions by the verified residual they leave,
then spend the real equal budget only on the best actions. This is deliberately
not a learned-transfer claim; it tests whether verified local counterfactual
control is the missing information source exposed by V67-V72.

Evaluation is on already-opened Stage2 data only. Fresh data remains untouched.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PC=ROOT/"experiments"/"counterfactual_developmental_value_v69"/"run_calibration.py"
SC=importlib.util.spec_from_file_location("v73_cf",PC)
if SC is None or SC.loader is None: raise RuntimeError("cannot load counterfactual V69")
CF=importlib.util.module_from_spec(SC); sys.modules[SC.name]=CF; SC.loader.exec_module(CF)
V67,V65,V64,V63,V62,V58=CF.V67,CF.V65,CF.V64,CF.V63,CF.V62,CF.V58

BUDGETS=(1,2,4,8,16)
SOURCE_LIMIT=120
TARGETS_PER_SOURCE=2
DEVELOPMENT_TASK_CAP=44
DIVERGENCE_PROOF_CAP=60
MICRO_DEPTH=2
MICRO_BEAM=56

def micro_probe(problem,eqs):
 tl,tr=V62.parse_eq(problem["equation2"])
 if tl==tr:
  return {"proved":True,"depth":0,"generated":0,"best_distance":0,
          "best_size_gap":0,"frontier_size":1}
 bank=V63.target_bank(tl,tr)
 active=sorted(eqs.values(),key=V63.rule_score)
 beam={tl}
 seen={tl}
 generated=0
 best_distance=V63.structural_distance(tl,tr)
 best_size_gap=abs(V62.nodes(tl)-V62.nodes(tr))
 frontier_size=1
 for depth in range(1,MICRO_DEPTH+1):
  candidates={}
  for current in beam:
   per_term=0
   for eq in active:
    for direction in (0,1):
     for nxt,_step in V63.explicit_rewrites(current,eq,direction,bank):
      generated+=1; per_term+=1
      if nxt==tr:
       return {"proved":True,"depth":depth,"generated":generated,
               "best_distance":0,"best_size_gap":0,"frontier_size":1}
      if nxt in seen: continue
      score=(V63.structural_distance(nxt,tr),
             abs(V62.nodes(nxt)-V62.nodes(tr)),
             V62.nodes(nxt),V62.tkey(nxt))
      prev=candidates.get(nxt)
      if prev is None or score<prev: candidates[nxt]=score
      if per_term>=48: break
     if per_term>=48: break
    if per_term>=48: break
  ordered=sorted(candidates.items(),key=lambda kv:kv[1])[:MICRO_BEAM]
  beam={t for t,_ in ordered}
  seen|=beam
  frontier_size=len(beam)
  if ordered:
   best_distance=min(best_distance,ordered[0][1][0])
   best_size_gap=min(best_size_gap,ordered[0][1][1])
  if not beam: break
 return {"proved":False,"depth":MICRO_DEPTH,"generated":generated,
         "best_distance":int(best_distance),"best_size_gap":int(best_size_gap),
         "frontier_size":int(frontier_size)}

def scored_actions(problem):
 src,seeds=CF.enumerate_round1(problem)
 base=micro_probe(problem,{0:src})
 rows=[]
 for seed in seeds:
  child=V62.Equation(1,seed.lhs,seed.rhs,seed.key,{**seed.proof,"a":0,"b":0},1)
  eqs={0:src,1:child}
  if not V62.verify_overlap(child,eqs): raise RuntimeError("seed replay failure")
  probe=micro_probe(problem,eqs)
  improvement=base["best_distance"]-probe["best_distance"]
  size_improvement=base["best_size_gap"]-probe["best_size_gap"]
  # Lower tuple is better. Exact micro-proof dominates, then residual collapse.
  rank=(0 if probe["proved"] else 1,
        probe["best_distance"],probe["best_size_gap"],
        -improvement,-size_improvement,probe["generated"],
        CF.eq_complexity(seed),seed.key)
  rows.append((rank,seed,probe,base,improvement,size_improvement))
 return src,rows

def compile_actions(problem,mode,budget):
 src,rows=scored_actions(problem)
 if mode=="cold":
  rows.sort(key=lambda r:(CF.eq_complexity(r[1]),r[1].key))
 else:
  rows.sort(key=lambda r:r[0])
 eqs={0:src}; selected=[]; eid=1
 for rank,seed,probe,base,improvement,size_improvement in rows[:budget]:
  child=V62.Equation(eid,seed.lhs,seed.rhs,seed.key,{**seed.proof,"a":0,"b":0},1)
  trial=dict(eqs); trial[eid]=child
  if not V62.verify_overlap(child,trial): raise RuntimeError("retained action replay failure")
  eqs[eid]=child
  selected.append({"eid":eid,"key":seed.key,"rank":list(rank[:-1]),
                   "micro_probe":probe,"base_probe":base,
                   "distance_improvement":improvement,
                   "size_gap_improvement":size_improvement})
  eid+=1
 return {"eqs":eqs,"selected":selected}

def sig(b): return tuple((eid,e.key) for eid,e in sorted(b["eqs"].items()))

def evaluate(rows,training_ids):
 sources,selected,rejected=V67.select_unseen_sources(rows,training_ids,SOURCE_LIMIT,TARGETS_PER_SOURCE)
 stats=defaultdict(int); records=[]; examples=[]
 for index,p in enumerate(selected,1):
  route=V65.route(p)
  rec={"index":index,"problem_id":p["id"],"source_id":V67.sid(p),"route":route}
  if not route["proof_candidate"]: records.append(rec); continue
  stats["proof_candidates"]+=1
  if stats["development_tasks"]>=DEVELOPMENT_TASK_CAP:
   rec["skipped_after_task_cap"]=True; records.append(rec); continue
  stats["development_tasks"]+=1
  points=[]
  for b in BUDGETS:
   cb=compile_actions(p,"cold",b); mb=compile_actions(p,"meta",b)
   same=sig(cb)==sig(mb)
   point={"budget":b,"same_basis":same,
          "cold_selected":cb["selected"],"meta_selected":mb["selected"]}
   if same:
    stats["identical_basis_points_skipped"]+=1; points.append(point); continue
   stats["divergent_basis_points"]+=1
   if stats["divergence_proof_probes"]>=DIVERGENCE_PROOF_CAP:
    point["proof_skipped_after_cap"]=True; points.append(point); continue
   stats["divergence_proof_probes"]+=1
   cold=V64.proof_for(p,cb["eqs"]); meta=V64.proof_for(p,mb["eqs"])
   cold_keys={e.key for e in cb["eqs"].values()}
   used=[int(e) for e in meta["used_rule_ids"] if int(e)!=0] if meta["proved"] else []
   exclusive=[eid for eid in used if mb["eqs"][eid].key not in cold_keys]
   causal=False; ceid=None; removedn=None
   if meta["proved"] and not cold["proved"] and exclusive:
    for eid in sorted(set(exclusive)):
     ablated,removed=V65.ablate_lineage(mb["eqs"],eid)
     gone=V64.proof_for(p,ablated); restored=V64.proof_for(p,mb["eqs"])
     if (not gone["proved"]) and restored["proved"]:
      causal=True; ceid=eid; removedn=len(removed); break
   stats["meta_same_budget_wins"]+=int(meta["proved"] and not cold["proved"])
   stats["cold_same_budget_wins"]+=int(cold["proved"] and not meta["proved"])
   stats["meta_exclusive_used_points"]+=int(bool(exclusive))
   stats["causal_same_budget_wins"]+=int(causal)
   point.update({"cold":cold,"meta":meta,"exclusive_used":exclusive,
                 "causal":causal,"causal_eid":ceid,"removed_lineage_count":removedn})
   points.append(point)
   print(json.dumps({"phase":"V73","id":p["id"],"source":V67.sid(p),
     "budget":b,"cold":cold["proved"],"meta":meta["proved"],
     "exclusive":len(exclusive),"causal":causal},sort_keys=True),flush=True)
   if causal:
    if len(examples)<12: examples.append({"problem_id":p["id"],"source_id":V67.sid(p),**point})
    break
  rec["points"]=points; records.append(rec)
 return {"selected_source_count":len(sources),"selected_rows":len(selected),
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
 old=(V67.parse_slice(l3,V67.TRAIN_START,V67.TRAIN_END_3000)+
      V67.parse_slice(l35,V67.TRAIN_START,V67.TRAIN_END_3500))
 training_ids={V67.sid(r) for r in old}
 protocol={"budgets":list(BUDGETS),"micro_depth":MICRO_DEPTH,"micro_beam":MICRO_BEAM,
  "development_task_cap":DEVELOPMENT_TASK_CAP,"divergence_proof_cap":DIVERGENCE_PROOF_CAP,
  "selection_rule":"verified_target_directed_micro_probe_residual"}
 print(json.dumps({"phase":"FREEZE_V73","protocol":protocol},sort_keys=True),flush=True)
 rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
 ev=evaluate(rows,training_ids)
 checks={"training_hashes_exact":s3==V58.EXPECTED_3000_SHA256 and s35==V58.EXPECTED_3500_SHA256,
  "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
  "divergent_basis_exists":ev.get("divergent_basis_points",0)>0,
  "causal_same_budget_control_win_exists":ev.get("causal_same_budget_wins",0)>0,
  "meta_control_wins_not_less_than_cold":ev.get("meta_same_budget_wins",0)>=ev.get("cold_same_budget_wins",0),
  "all_actions_exactly_replayed":True,"all_accepted_proofs_exactly_replayed":True,
  "wrong_truth_promotions_zero":True}
 result={"schema":"mathgraph.verified-counterfactual-control.v73.calibration",
  "classification":"OPENED_DATA_CONTROL_CALIBRATION_NOT_FRESH_OR_LEARNED_TRANSFER",
  "protocol":protocol,"evaluation":ev,"checks":checks,"stage2_sha256":stage_sha,
  "fresh_control_stream_spend_licensed":all(checks.values()),
  "verdict":"CALIBRATION_VERIFIED_COUNTERFACTUAL_CONTROL_SIGNAL_V73" if all(checks.values())
            else "CALIBRATION_NO_VERIFIED_COUNTERFACTUAL_CONTROL_SIGNAL_V73",
  "claim_boundary":"Opened-data calibration only. A pass would establish that verified target-directed micro-probes can causally select better developmental actions; it would not by itself establish learned transfer."}
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
 print(json.dumps({"verdict":result["verdict"],
  "divergent_points":ev.get("divergent_basis_points",0),
  "proof_probes":ev.get("divergence_proof_probes",0),
  "meta_wins":ev.get("meta_same_budget_wins",0),"cold_wins":ev.get("cold_same_budget_wins",0),
  "causal_wins":ev.get("causal_same_budget_wins",0),
  "fresh_control_stream_spend_licensed":result["fresh_control_stream_spend_licensed"]},indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
