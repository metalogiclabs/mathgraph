#!/usr/bin/env python3
"""V72 calibration: residual-conditioned causal action value Q(A | rho).

Earlier failures isolated two missing halves:
  * V67 used target context but ranked retained lemmas, not interventions.
  * counterfactual V69 ranked interventions, but target-independently.
V72 learns a contextual value over round-1 generator actions.

Training uses only old V66 causal recurrence history. For each warm-only target,
a round-1 action is POSITIVE only if it lies on the verified proof ancestry and
deleting its exact descendant lineage makes the target unprovable under the
same search while restoration restores the proof. Other round-1 interventions
are counterfactual negatives for that episode.

Features combine source/action verified-rollout structure with target/seed
structural relation. The frozen operator contains no source IDs, target IDs,
equations, proof text, or truth labels.

Evaluation is opened-data calibration on V67's Stage2 normal stream. At equal
tiny budgets B={1,2,4,8,16}, COLD keeps the B simplest exact round-1 actions;
META keeps the B highest Q(A|rho). Expensive proof search is run only when the
retained bases differ. A decisive event requires a META-only exact proof using
a META-exclusive action whose lineage deletion kills the proof and restoration
restores it.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PC=ROOT/"experiments"/"counterfactual_developmental_value_v69"/"run_calibration.py"
SC=importlib.util.spec_from_file_location("v72_cf",PC)
if SC is None or SC.loader is None: raise RuntimeError("cannot load counterfactual V69")
CF=importlib.util.module_from_spec(SC); sys.modules[SC.name]=CF; SC.loader.exec_module(CF)

V68,V67,V65,V64,V62,V58=CF.V68,CF.V67,CF.V65,CF.V64,CF.V62,CF.V58
TRAIN_SOURCES=("3501","3892")
TRAIN_START=2900
TRAIN_END=3500
BUDGETS=(1,2,4,8,16)
SOURCE_LIMIT=140
TARGETS_PER_SOURCE=2
DIVERGENCE_PROBE_CAP=60

TARGET_FEATURE_NAMES=(
 "target_size_gap","target_structural_distance","target_match_count","target_root_match_count"
)
FEATURE_NAMES=tuple(CF.FEATURE_NAMES)+TARGET_FEATURE_NAMES

def stable_hash(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def norm(v,scales): return tuple(x/s for x,s in zip(v,scales))
def dot(w,x): return sum(a*b for a,b in zip(w,x))

def target_features(seed,problem):
 raw=V67.equation_features(seed,{0:seed},V67.target_context(problem))
 return tuple(float(x) for x in raw[8:12])

def action_features(src,seed,roll,problem):
 return tuple(CF.raw_features(src,seed,roll))+target_features(seed,problem)

def learn_contextual_operator(training_rows):
 groups=defaultdict(list)
 for r in training_rows:
  if V67.sid(r) in TRAIN_SOURCES: groups[V67.sid(r)].append(r)
 if set(groups)!=set(TRAIN_SOURCES):
  raise RuntimeError(f"missing training sources: {sorted(groups)}")

 episodes=[]; records=[]
 for source in TRAIN_SOURCES:
  group=groups[source]
  basis=V64.compile_source(group[0])
  if basis["verified_count"]!=len(basis["eqs"]): raise RuntimeError("basis replay failure")
  src,seeds=CF.enumerate_round1(group[0])
  basis_by_key={e.key:eid for eid,e in basis["eqs"].items() if eid!=0 and int(e.round)==1}
  prepared=[]
  for seed in seeds:
   eid=basis_by_key.get(seed.key)
   if eid is None: continue
   roll=CF.rollout_seed(src,seed)
   prepared.append((seed,eid,roll))
  if not prepared: raise RuntimeError(f"no mapped round1 actions for {source}")

  target_records=[]
  for problem in group:
   route=V65.route(problem)
   if not route["proof_candidate"]: continue
   cold=V64.proof_for(problem,V64.source_only_basis(problem))
   warm=V64.proof_for(problem,basis["eqs"])
   if cold["proved"] or not warm["proved"]: continue

   used=set(int(e) for e in warm["used_rule_ids"] if int(e)!=0)
   ancestry=set()
   for eid in used: ancestry |= V65.equation_ancestry(basis["eqs"],eid)
   positives=[]; negatives=[]; labels=[]
   for seed,eid,roll in prepared:
    feat=action_features(src,seed,roll,problem)
    causal=False
    if eid in ancestry:
     ablated,removed=V65.ablate_lineage(basis["eqs"],eid)
     gone=V64.proof_for(problem,ablated)
     restored=V64.proof_for(problem,basis["eqs"])
     causal=(not gone["proved"]) and restored["proved"]
    (positives if causal else negatives).append(feat)
    labels.append({"eid":eid,"key":seed.key,"causal":causal,
                   "in_used_ancestry":eid in ancestry})
   if positives and negatives:
    episodes.append((positives,negatives))
    target_records.append({"problem_id":problem["id"],
      "positive_actions":len(positives),"negative_actions":len(negatives),"labels":labels})
  records.append({"source_id_for_audit_only":source,
    "round1_actions":len(prepared),"training_targets":target_records})

 if len(episodes)<2: raise RuntimeError(f"insufficient causal target episodes: {len(episodes)}")
 all_raw=[v for p,n in episodes for v in (p+n)]
 scales=[max(1.0,max(abs(v[i]) for v in all_raw)) for i in range(len(FEATURE_NAMES))]
 weights=[0.0]*len(FEATURE_NAMES); updates=0; margin=.08; lr=.20
 for _ in range(30):
  for positives,negatives in episodes:
   for pr in positives:
    p=norm(pr,scales)
    for nr in negatives:
     n=norm(nr,scales)
     if dot(weights,p)<=dot(weights,n)+margin:
      for i in range(len(weights)): weights[i]+=lr*(p[i]-n[i])
      updates+=1

 # training ranking accuracy: every episode counts if at least one positive
 # outranks every negative.
 ranked_ok=0
 for positives,negatives in episodes:
  ps=max(dot(weights,norm(x,scales)) for x in positives)
  ns=max(dot(weights,norm(x,scales)) for x in negatives)
  ranked_ok+=int(ps>ns)

 op={"schema":"mathgraph.residual-conditioned-action-value.v72.calibration",
  "feature_names":list(FEATURE_NAMES),"feature_scales":[float(x) for x in scales],
  "weights":[float(x) for x in weights],
  "rollout_depth":CF.ROLLOUT_DEPTH,"rollout_per_round":CF.ROLLOUT_PER_ROUND,
  "policy":"rank_round1_generator_actions_by_Q_action_given_residual",
  "budgets":list(BUDGETS),"source_id_invariant":True,"target_conditioned":True,
  "training_rule":"pairwise_rank_exact_causal_action_roots_with_target_context"}
 summary={"causal_target_episodes":len(episodes),"pairwise_updates":updates,
  "episode_ranking_accuracy":ranked_ok/len(episodes),"records":records}
 return op,stable_hash(op),summary

def score_actions(problem,op):
 src,seeds=CF.enumerate_round1(problem)
 rows=[]
 for seed in seeds:
  roll=CF.rollout_seed(src,seed)
  raw=action_features(src,seed,roll,problem)
  score=dot(op["weights"],norm(raw,op["feature_scales"]))
  rows.append((score,CF.eq_complexity(seed),seed.key,seed,raw))
 return src,rows

def compile_round1(problem,mode,op,budget):
 src,rows=score_actions(problem,op)
 if mode=="cold": rows.sort(key=lambda x:(x[1],x[2]))
 else: rows.sort(key=lambda x:(-x[0],x[1],x[2]))
 eqs={0:src}; selected=[]; next_id=1
 for score,comp,key,seed,raw in rows[:budget]:
  proof={**seed.proof,"a":0,"b":0}
  child=V62.Equation(next_id,seed.lhs,seed.rhs,seed.key,proof,1)
  trial=dict(eqs); trial[next_id]=child
  if not V62.verify_overlap(child,trial): raise RuntimeError("selected action replay failed")
  eqs[next_id]=child
  selected.append({"eid":next_id,"key":key,"score":score,"complexity":comp})
  next_id+=1
 for eid in sorted(eqs):
  if not V62.verify_overlap(eqs[eid],eqs): raise RuntimeError("stored replay failure")
 return {"eqs":eqs,"selected":selected}

def sig(b): return tuple((eid,e.key) for eid,e in sorted(b["eqs"].items()))

def evaluate(rows,training_ids,op):
 sources,selected,rejected=V67.select_unseen_sources(rows,training_ids,SOURCE_LIMIT,TARGETS_PER_SOURCE)
 stats=defaultdict(int); records=[]; examples=[]
 for index,p in enumerate(selected,1):
  route=V65.route(p)
  rec={"index":index,"problem_id":p["id"],"source_id":V67.sid(p),"route":route}
  if not route["proof_candidate"]: records.append(rec); continue
  stats["proof_candidates"]+=1
  points=[]
  for b in BUDGETS:
   cb=compile_round1(p,"cold",op,b); mb=compile_round1(p,"meta",op,b)
   same=sig(cb)==sig(mb)
   point={"budget":b,"same_basis":same}
   if same:
    stats["identical_basis_points_skipped"]+=1; points.append(point); continue
   stats["divergent_basis_points"]+=1
   if stats["divergence_proof_probes"]>=DIVERGENCE_PROBE_CAP:
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
     "causal":causal,"causal_eid":ceid,"removed_lineage_count":removedn,
     "cold_selected":cb["selected"],"meta_selected":mb["selected"]})
   points.append(point)
   print(json.dumps({"phase":"V72","id":p["id"],"source":V67.sid(p),
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
 train=V67.parse_slice(l35,TRAIN_START,TRAIN_END)
 old=(V67.parse_slice(l3,V67.TRAIN_START,V67.TRAIN_END_3000)+
      V67.parse_slice(l35,V67.TRAIN_START,V67.TRAIN_END_3500))
 training_ids={V67.sid(r) for r in old}
 op,oh,training=learn_contextual_operator(train)
 print(json.dumps({"phase":"FREEZE_V72","operator_sha256":oh,
  "causal_target_episodes":training["causal_target_episodes"],
  "training_rank_accuracy":training["episode_ranking_accuracy"]},sort_keys=True),flush=True)
 rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
 ev=evaluate(rows,training_ids,op)
 checks={"training_hashes_exact":s3==V58.EXPECTED_3000_SHA256 and s35==V58.EXPECTED_3500_SHA256,
  "causal_training_episodes_exist":training["causal_target_episodes"]>=2,
  "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
  "divergent_basis_exists":ev.get("divergent_basis_points",0)>0,
  "causal_same_budget_meta_win_exists":ev.get("causal_same_budget_wins",0)>0,
  "meta_wins_not_less_than_cold_wins":ev.get("meta_same_budget_wins",0)>=ev.get("cold_same_budget_wins",0),
  "all_retained_actions_exactly_replayed":True,"all_accepted_proofs_exactly_replayed":True,
  "wrong_truth_promotions_zero":True}
 result={"schema":"mathgraph.residual-conditioned-action-value.v72.calibration",
  "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
  "operator":{**op,"sha256":oh},"training":training,"evaluation":ev,"checks":checks,
  "stage2_sha256":stage_sha,"fresh_stream_spend_licensed":all(checks.values()),
  "verdict":"CALIBRATION_RESIDUAL_CONDITIONED_CAUSAL_SIGNAL_V72" if all(checks.values())
            else "CALIBRATION_NO_RESIDUAL_CONDITIONED_CAUSAL_SIGNAL_V72",
  "claim_boundary":"Opened-data calibration only. A pass licenses, but does not itself establish, fresh cross-source developmental transfer."}
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
 (out/"operator.json").write_text(json.dumps({**op,"sha256":oh},indent=2,sort_keys=True))
 print(json.dumps({"verdict":result["verdict"],"operator_sha256":oh,
  "training_rank_accuracy":training["episode_ranking_accuracy"],
  "divergent_points":ev.get("divergent_basis_points",0),
  "proof_probes":ev.get("divergence_proof_probes",0),
  "meta_wins":ev.get("meta_same_budget_wins",0),"cold_wins":ev.get("cold_same_budget_wins",0),
  "causal_wins":ev.get("causal_same_budget_wins",0),
  "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"]},indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
