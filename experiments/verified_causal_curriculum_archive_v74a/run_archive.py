#!/usr/bin/env python3
"""V74A: persist a replayable verified causal-development curriculum.

Uses only the already-opened Stage2 normal corpus. It performs the pre-outcome
source-hash split, harvests exact causal developmental episodes from the train
partition, and serializes the resulting episode feature sets plus the exact
source/target problem rows needed to reconstruct every acquisition later.

No calibration and no fresh stream are read here.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"experiments"/"multi_source_causal_curriculum_v74"/"run_calibration.py"
S=importlib.util.spec_from_file_location("v74a_v74",P)
if S is None or S.loader is None: raise RuntimeError("cannot load V74")
V74=importlib.util.module_from_spec(S); sys.modules[S.name]=V74; S.loader.exec_module(V74)
V67=V74.V67

def stable_hash(obj):
 return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--stage2",required=True); ap.add_argument("--out",required=True)
 a=ap.parse_args()

 rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
 train=[r for r in rows if V74.bucket(V74.source_key(r)) in V74.TRAIN_BUCKETS]
 cal=[r for r in rows if V74.bucket(V74.source_key(r)) in V74.CAL_BUCKETS]
 train_keys={V74.source_key(r) for r in train}; cal_keys={V74.source_key(r) for r in cal}
 if train_keys&cal_keys: raise RuntimeError("source partition overlap")

 # Archive every causal episode we can certify from the adaptive census,
 # without requiring a later calibration signal.
 V74.MIN_CAUSAL_SOURCES=3
 V74.MAX_TRAIN_SOURCE_PROBES=96
 V74.MAX_CAUSAL_SOURCE_EPISODES=10
 V74.TARGETS_PER_TRAIN_SOURCE=1

 op,op_hash,training=V74.learn_many(train)

 by_id={str(r["id"]):r for r in train}
 episode_rows=[]
 for rec in training["records"]:
  ep=rec.get("causal_episode")
  if not ep: continue
  pid=str(ep["problem_id_for_audit_only"])
  problem=by_id.get(pid)
  if problem is None: raise RuntimeError(f"missing archived problem row {pid}")
  episode_rows.append({
   "problem":problem,
   "source_key":V74.source_key(problem),
   "source_id_for_audit_only":ep["source_id_for_audit_only"],
   "problem_id_for_audit_only":pid,
   "positive_actions":ep["positive_actions"],
   "negative_actions":ep["negative_actions"],
   "action_labels":ep["action_labels"],
   "second_pass":bool(rec.get("second_pass",False)),
  })

 feature_eps=training.get("feature_episodes",[])
 if len(feature_eps)!=training["causal_target_episodes"]:
  raise RuntimeError("feature episode count mismatch")

 archive={
  "schema":"mathgraph.verified-causal-development-curriculum.v74a",
  "classification":"OPENED_DATA_REPLAYABLE_CAUSAL_TRAINING_ARCHIVE",
  "source":{
   "repository":"heathsanchez/equational-theories-lean-stage2",
   "commit":"374eb40ba5389915deb174fbc12cc92346214dd1",
   "path":"examples/problems/normal.jsonl",
   "sha256":stage_sha,
   "data_status":"opened_by_v67_not_fresh",
  },
  "split":{
   "rule":"sha256(canonical_source_key)[0] mod 5",
   "train_buckets":sorted(V74.TRAIN_BUCKETS),
   "calibration_buckets":sorted(V74.CAL_BUCKETS),
   "train_source_count":len(train_keys),
   "calibration_source_count":len(cal_keys),
   "zero_source_key_overlap":not bool(train_keys&cal_keys),
  },
  "acquisition":{
   "source_groups_scanned":training["source_groups_scanned"],
   "independent_causal_sources":training["independent_causal_sources"],
   "causal_target_episodes":training["causal_target_episodes"],
   "feature_names":list(op["feature_names"]),
   "episodes":episode_rows,
   "feature_episodes":feature_eps,
  },
  "reference_operator":{
   **op,"sha256":op_hash
  },
  "claim_boundary":"Each archived positive was admitted only after exact proof-lineage deletion destroyed a previously replayed proof and restoration restored it. The archive is training evidence from already-opened data, not fresh transfer evidence."
 }
 archive["archive_sha256"]=stable_hash(archive)

 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 (out/"causal_curriculum.json").write_text(json.dumps(archive,indent=2,sort_keys=True))
 (out/"reference_operator.json").write_text(json.dumps({**op,"sha256":op_hash},indent=2,sort_keys=True))
 print(json.dumps({
  "verdict":"PASS_VERIFIED_CAUSAL_CURRICULUM_ARCHIVE_V74A",
  "archive_sha256":archive["archive_sha256"],
  "independent_causal_sources":training["independent_causal_sources"],
  "causal_target_episodes":training["causal_target_episodes"],
  "train_source_count":len(train_keys),
  "calibration_source_count":len(cal_keys),
 },indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
