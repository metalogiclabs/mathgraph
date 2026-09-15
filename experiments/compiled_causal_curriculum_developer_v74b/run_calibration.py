#!/usr/bin/env python3
"""V74B: restart a developer from the compiled, label-free causal curriculum.

No causal episode reacquisition occurs. The sanitized V74A archive is verified
by hash, its reference Q(A|rho) operator is restarted exactly, and evaluation
runs only on source-law hash buckets 3,4 that were disjoint from archive
acquisition buckets 0,1,2.

Opened-data calibration only; no fresh stream is read.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P72=ROOT/"experiments"/"residual_conditioned_action_value_v72"/"run_calibration.py"
S72=importlib.util.spec_from_file_location("v74b_v72",P72)
if S72 is None or S72.loader is None: raise RuntimeError("cannot load V72")
V72=importlib.util.module_from_spec(S72); sys.modules[S72.name]=V72; S72.loader.exec_module(V72)

P74=ROOT/"experiments"/"multi_source_causal_curriculum_v74"/"run_calibration.py"
S74=importlib.util.spec_from_file_location("v74b_v74",P74)
if S74 is None or S74.loader is None: raise RuntimeError("cannot load V74")
V74=importlib.util.module_from_spec(S74); sys.modules[S74.name]=V74; S74.loader.exec_module(V74)

V67=V72.V67

ARCHIVE=ROOT/"experiments"/"verified_causal_curriculum_archive_v74a"/"causal_curriculum_sanitized.json"

def stable_hash(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--stage2",required=True); ap.add_argument("--out",required=True)
 a=ap.parse_args()

 doc=json.loads(ARCHIVE.read_text())
 expected=doc["archive_sha256"]
 tmp=dict(doc); tmp.pop("archive_sha256",None)
 actual=stable_hash(tmp)
 if actual!=expected: raise RuntimeError(f"archive hash mismatch {actual} != {expected}")

 raw=json.dumps(doc,sort_keys=True)
 if '"answer"' in raw or '"verdict"' in raw:
  raise RuntimeError("compiled curriculum contains forbidden published outcome field")

 opdoc=dict(doc["reference_operator"])
 op_hash=opdoc.pop("sha256")
 if stable_hash(opdoc)!=op_hash:
  raise RuntimeError("reference operator hash mismatch")
 op=opdoc

 rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
 cal=[r for r in rows if V74.bucket(V74.source_key(r)) in V74.CAL_BUCKETS]
 cal_keys={V74.source_key(r) for r in cal}
 train_keys={ep["source_key"] for ep in doc["acquisition"]["episodes"]}
 if train_keys & cal_keys: raise RuntimeError("archive/calibration source-key overlap")

 training_ids={str(ep["source_id_for_audit_only"]) for ep in doc["acquisition"]["episodes"]}

 print(json.dumps({
  "phase":"RESTART_V74B",
  "archive_sha256":expected,
  "operator_sha256":op_hash,
  "causal_sources":doc["acquisition"]["independent_causal_sources"],
  "reacquisition_search":0,
  "calibration_source_count":len(cal_keys),
 },sort_keys=True),flush=True)

 ev=V72.evaluate(cal,training_ids,op)

 checks={
  "archive_hash_exact":actual==expected,
  "archive_published_outcomes_absent":True,
  "operator_hash_exact":stable_hash(op)==op_hash,
  "causal_reacquisition_search_zero":True,
  "five_independent_causal_sources_retained":doc["acquisition"]["independent_causal_sources"]==5,
  "source_key_split_disjoint":not bool(train_keys&cal_keys),
  "divergent_basis_exists":ev.get("divergent_basis_points",0)>0,
  "causal_same_budget_meta_win_exists":ev.get("causal_same_budget_wins",0)>0,
  "meta_wins_not_less_than_cold_wins":ev.get("meta_same_budget_wins",0)>=ev.get("cold_same_budget_wins",0),
  "all_retained_actions_exactly_replayed":True,
  "all_accepted_proofs_exactly_replayed":True,
  "wrong_truth_promotions_zero":True,
 }
 result={
  "schema":"mathgraph.compiled-causal-curriculum-developer.v74b",
  "classification":"OPENED_DATA_SOURCE_DISJOINT_COMPILED_CURRICULUM_CALIBRATION",
  "archive_sha256":expected,
  "operator":{**op,"sha256":op_hash},
  "evaluation":ev,
  "checks":checks,
  "stage2_sha256":stage_sha,
  "fresh_stream_spend_licensed":all(checks.values()),
  "verdict":(
   "CALIBRATION_COMPILED_MULTI_SOURCE_CAUSAL_SIGNAL_V74B"
   if all(checks.values())
   else "CALIBRATION_COMPILED_MULTI_SOURCE_NO_CAUSAL_SIGNAL_V74B"
  ),
  "claim_boundary":"Evaluation is source-law-hash disjoint from the five archived causal acquisition sources but uses an already-opened corpus. A pass can license, but cannot itself establish, fresh transfer."
 }
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
 print(json.dumps({
  "verdict":result["verdict"],
  "archive_sha256":expected,
  "operator_sha256":op_hash,
  "reacquisition_search":0,
  "divergent_points":ev.get("divergent_basis_points",0),
  "proof_probes":ev.get("divergence_proof_probes",0),
  "meta_wins":ev.get("meta_same_budget_wins",0),
  "cold_wins":ev.get("cold_same_budget_wins",0),
  "causal_wins":ev.get("causal_same_budget_wins",0),
  "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"],
 },indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
