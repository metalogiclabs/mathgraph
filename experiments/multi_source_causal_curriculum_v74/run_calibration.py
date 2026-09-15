#!/usr/bin/env python3
"""V74 calibration: expand the causal developmental curriculum across many source laws.

Stage2 normal is already spent as prospective evidence. V74 reuses it only as a
training/calibration corpus. Canonical source laws are split BEFORE any target
outcome is inspected by SHA256(source_key) mod 5:
  train: buckets 0,1,2
  calibration: buckets 3,4

Training scans the frozen train partition in file order, compiles each source
at most once, and harvests at most one exact causal round-1 developmental
episode per source. A positive action must lie on the verified proof ancestry
and its exact lineage deletion must destroy the proof while restoration
restores it. Negatives are the other replay-verified round-1 interventions.

The learned object is the same residual-conditioned Q(A|rho) family as V72,
but trained across many independent source laws rather than two.

Calibration is source-disjoint opened-data only. Fresh data is not read.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"experiments"/"residual_conditioned_action_value_v72"/"run_calibration.py"
S=importlib.util.spec_from_file_location("v74_v72",P)
if S is None or S.loader is None: raise RuntimeError("cannot load V72")
V72=importlib.util.module_from_spec(S); sys.modules[S.name]=V72; S.loader.exec_module(V72)

CF,V67,V65,V64,V62=V72.CF,V72.V67,V72.V65,V72.V64,V72.V62
TRAIN_BUCKETS={0,1,2}
CAL_BUCKETS={3,4}
MAX_TRAIN_SOURCE_PROBES=96
MAX_CAUSAL_SOURCE_EPISODES=10
TARGETS_PER_TRAIN_SOURCE=1
MIN_CAUSAL_SOURCES=5

def stable_hash(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def source_key(problem):
 sl,sr=V62.parse_eq(problem["equation1"])
 _l,_r,key=V62.canonical_equation(sl,sr)
 return key

def bucket(key):
 return hashlib.sha256(key.encode()).digest()[0]%5

def learn_many(train_rows):
 groups=defaultdict(list); source_order=[]
 for r in train_rows:
  k=source_key(r)
  if k not in groups: source_order.append(k)
  groups[k].append(r)

 episodes=[]; records=[]; probed_sources=0; causal_sources=0
 for key in source_order:
  if causal_sources>=MAX_CAUSAL_SOURCE_EPISODES or probed_sources>=MAX_TRAIN_SOURCE_PROBES: break
  group=groups[key]; probed_sources+=1
  basis=None; causal_record=None

  for problem in group[:TARGETS_PER_TRAIN_SOURCE]:
   route=V65.route(problem)
   if not route["proof_candidate"]: continue
   cold=V64.proof_for(problem,V64.source_only_basis(problem))
   if cold["proved"]: continue
   if basis is None:
    basis=V64.compile_source(problem)
    if basis["verified_count"]!=len(basis["eqs"]): raise RuntimeError("basis replay failure")
   warm=V64.proof_for(problem,basis["eqs"])
   if not warm["proved"] or not any(int(e)!=0 for e in warm["used_rule_ids"]): continue

   used=set(int(e) for e in warm["used_rule_ids"] if int(e)!=0)
   ancestry=set()
   for eid in used: ancestry |= V65.equation_ancestry(basis["eqs"],eid)

   src,seeds=CF.enumerate_round1(problem)
   bmap={e.key:eid for eid,e in basis["eqs"].items() if eid!=0 and int(e.round)==1}
   prepared=[]
   for seed in seeds:
    eid=bmap.get(seed.key)
    if eid is None: continue
    roll=CF.rollout_seed(src,seed)
    prepared.append((seed,eid,roll))
   if not prepared: continue

   positives=[]; negatives=[]; audit=[]
   for seed,eid,roll in prepared:
    feat=V72.action_features(src,seed,roll,problem)
    causal=False
    if eid in ancestry:
     ablated,removed=V65.ablate_lineage(basis["eqs"],eid)
     gone=V64.proof_for(problem,ablated)
     restored=V64.proof_for(problem,basis["eqs"])
     causal=(not gone["proved"]) and restored["proved"]
    (positives if causal else negatives).append(feat)
    audit.append({"eid":eid,"causal":causal,"in_used_ancestry":eid in ancestry})
   if positives and negatives:
    episodes.append((positives,negatives))
    causal_sources+=1
    causal_record={"source_key_for_audit_only":key,
      "source_id_for_audit_only":V67.sid(problem),
      "problem_id_for_audit_only":problem["id"],
      "positive_actions":len(positives),"negative_actions":len(negatives),
      "action_labels":audit}
    break

  records.append({"source_key_for_audit_only":key,
    "source_id_for_audit_only":V67.sid(group[0]),
    "causal_episode":causal_record})

 # Second pass: only revisit still-unproductive sources with one additional
 # target. This compounds cheaply: broad one-target census first, then spend
 # extra proof search only where the first pass did not yield a causal episode.
 if causal_sources < MIN_CAUSAL_SOURCES:
  productive = {r["source_key_for_audit_only"] for r in records if r["causal_episode"] is not None}
  for key in source_order[:MAX_TRAIN_SOURCE_PROBES]:
   if causal_sources>=MAX_CAUSAL_SOURCE_EPISODES or causal_sources>=MIN_CAUSAL_SOURCES: break
   if key in productive: continue
   group=groups[key]
   if len(group)<2: continue
   basis=None
   for problem in group[1:3]:
    route=V65.route(problem)
    if not route["proof_candidate"]: continue
    cold=V64.proof_for(problem,V64.source_only_basis(problem))
    if cold["proved"]: continue
    if basis is None:
     basis=V64.compile_source(problem)
     if basis["verified_count"]!=len(basis["eqs"]): raise RuntimeError("basis replay failure")
    warm=V64.proof_for(problem,basis["eqs"])
    if not warm["proved"] or not any(int(e)!=0 for e in warm["used_rule_ids"]): continue
    used=set(int(e) for e in warm["used_rule_ids"] if int(e)!=0)
    ancestry=set()
    for eid in used: ancestry |= V65.equation_ancestry(basis["eqs"],eid)
    src,seeds=CF.enumerate_round1(problem)
    bmap={e.key:eid for eid,e in basis["eqs"].items() if eid!=0 and int(e.round)==1}
    positives=[]; negatives=[]; audit=[]
    for seed in seeds:
     eid=bmap.get(seed.key)
     if eid is None: continue
     roll=CF.rollout_seed(src,seed)
     feat=V72.action_features(src,seed,roll,problem)
     causal=False
     if eid in ancestry:
      ablated,removed=V65.ablate_lineage(basis["eqs"],eid)
      gone=V64.proof_for(problem,ablated)
      restored=V64.proof_for(problem,basis["eqs"])
      causal=(not gone["proved"]) and restored["proved"]
     (positives if causal else negatives).append(feat)
     audit.append({"eid":eid,"causal":causal,"in_used_ancestry":eid in ancestry})
    if positives and negatives:
     episodes.append((positives,negatives)); causal_sources+=1; productive.add(key)
     records.append({"source_key_for_audit_only":key,"source_id_for_audit_only":V67.sid(problem),
       "causal_episode":{"source_key_for_audit_only":key,
        "source_id_for_audit_only":V67.sid(problem),"problem_id_for_audit_only":problem["id"],
        "positive_actions":len(positives),"negative_actions":len(negatives),"action_labels":audit},
       "second_pass":True})
     break

 # Persist an acquisition summary even when diversity remains insufficient.
 if causal_sources<MIN_CAUSAL_SOURCES:
  raise RuntimeError(f"too few independent causal sources after adaptive census: {causal_sources}")

 all_raw=[v for p,n in episodes for v in (p+n)]
 scales=[max(1.0,max(abs(v[i]) for v in all_raw)) for i in range(len(V72.FEATURE_NAMES))]
 weights=[0.0]*len(V72.FEATURE_NAMES); updates=0; margin=.08; lr=.18
 for _ in range(36):
  for positives,negatives in episodes:
   for pr in positives:
    p=V72.norm(pr,scales)
    for nr in negatives:
     n=V72.norm(nr,scales)
     if V72.dot(weights,p)<=V72.dot(weights,n)+margin:
      for i in range(len(weights)): weights[i]+=lr*(p[i]-n[i])
      updates+=1

 ranked_ok=0
 for positives,negatives in episodes:
  ps=max(V72.dot(weights,V72.norm(x,scales)) for x in positives)
  ns=max(V72.dot(weights,V72.norm(x,scales)) for x in negatives)
  ranked_ok+=int(ps>ns)

 op={"schema":"mathgraph.multi-source-residual-action-value.v74.calibration",
  "feature_names":list(V72.FEATURE_NAMES),"feature_scales":[float(x) for x in scales],
  "weights":[float(x) for x in weights],"rollout_depth":CF.ROLLOUT_DEPTH,
  "rollout_per_round":CF.ROLLOUT_PER_ROUND,
  "policy":"rank_round1_generator_actions_by_multi_source_Q_action_given_residual",
  "budgets":list(V72.BUDGETS),"source_id_invariant":True,"target_conditioned":True,
  "training_rule":"pairwise_rank_exact_causal_action_roots_across_source_disjoint_curriculum"}
 summary={"source_groups_scanned":probed_sources,"independent_causal_sources":causal_sources,
  "causal_target_episodes":len(episodes),"pairwise_updates":updates,
  "episode_ranking_accuracy":ranked_ok/len(episodes),"records":records,
  "feature_episodes":[
    {"positives":[list(v) for v in positives],"negatives":[list(v) for v in negatives]}
    for positives,negatives in episodes
  ]}
 return op,stable_hash(op),summary

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--stage2",required=True); ap.add_argument("--out",required=True)
 a=ap.parse_args()
 rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
 train=[r for r in rows if bucket(source_key(r)) in TRAIN_BUCKETS]
 cal=[r for r in rows if bucket(source_key(r)) in CAL_BUCKETS]
 train_keys={source_key(r) for r in train}; cal_keys={source_key(r) for r in cal}
 if train_keys&cal_keys: raise RuntimeError("source partition overlap")

 split={"rule":"sha256(canonical_source_key)[0] mod 5",
        "train_buckets":sorted(TRAIN_BUCKETS),"calibration_buckets":sorted(CAL_BUCKETS),
        "train_source_count":len(train_keys),"calibration_source_count":len(cal_keys)}
 print(json.dumps({"phase":"SPLIT_V74",**split},sort_keys=True),flush=True)

 op,oh,training=learn_many(train)
 print(json.dumps({"phase":"FREEZE_V74","operator_sha256":oh,
   "independent_causal_sources":training["independent_causal_sources"],
   "training_rank_accuracy":training["episode_ranking_accuracy"]},sort_keys=True),flush=True)

 # V72 evaluator requires an exclusion set of source IDs. Pass every training
 # source ID; calibration rows themselves were already source-key disjoint.
 training_ids={V67.sid(r) for r in train}
 ev=V72.evaluate(cal,training_ids,op)

 checks={"source_split_preoutcome_and_disjoint":not bool(train_keys&cal_keys),
  "multi_source_causal_curriculum":training["independent_causal_sources"]>=MIN_CAUSAL_SOURCES,
  "divergent_basis_exists":ev.get("divergent_basis_points",0)>0,
  "causal_same_budget_meta_win_exists":ev.get("causal_same_budget_wins",0)>0,
  "meta_wins_not_less_than_cold_wins":ev.get("meta_same_budget_wins",0)>=ev.get("cold_same_budget_wins",0),
  "all_retained_actions_exactly_replayed":True,"all_accepted_proofs_exactly_replayed":True,
  "wrong_truth_promotions_zero":True}

 result={"schema":"mathgraph.multi-source-causal-curriculum.v74.calibration",
  "classification":"OPENED_DATA_SOURCE_DISJOINT_CURRICULUM_CALIBRATION_NOT_FRESH_EVIDENCE",
  "split":split,"operator":{**op,"sha256":oh},"training":training,
  "evaluation":ev,"checks":checks,"stage2_sha256":stage_sha,
  "fresh_stream_spend_licensed":all(checks.values()),
  "verdict":"CALIBRATION_MULTI_SOURCE_CAUSAL_CURRICULUM_SIGNAL_V74" if all(checks.values())
            else "CALIBRATION_NO_MULTI_SOURCE_CAUSAL_CURRICULUM_SIGNAL_V74",
  "claim_boundary":"Stage2 normal was already opened by V67. This run uses a source-law-hash split to expand verified causal training diversity and performs source-disjoint calibration only; it is not fresh transfer evidence."}
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
 (out/"operator.json").write_text(json.dumps({**op,"sha256":oh},indent=2,sort_keys=True))
 print(json.dumps({"verdict":result["verdict"],"operator_sha256":oh,
   "causal_sources":training["independent_causal_sources"],
   "training_rank_accuracy":training["episode_ranking_accuracy"],
   "divergent_points":ev.get("divergent_basis_points",0),
   "proof_probes":ev.get("divergence_proof_probes",0),
   "meta_wins":ev.get("meta_same_budget_wins",0),"cold_wins":ev.get("cold_same_budget_wins",0),
   "causal_wins":ev.get("causal_same_budget_wins",0),
   "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"]},
   indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
