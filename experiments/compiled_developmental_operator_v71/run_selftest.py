#!/usr/bin/env python3
"""V71 self-test: does the compiled developer compress the exact V66 causal episodes?"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"experiments"/"causal_action_budget_frontier_v70"/"run_calibration.py"
S=importlib.util.spec_from_file_location("v71s_v70",P)
if S is None or S.loader is None: raise RuntimeError("cannot load V70")
V70=importlib.util.module_from_spec(S); sys.modules[S.name]=V70; S.loader.exec_module(V70)
V69,V67,V64,V58=V70.V69,V70.V67,V70.V64,V70.V58

CAUSAL_IDS={
 "3501_to_53830","3501_to_41599","3892_to_50403",
 "3501_to_41655","3501_to_43370","3892_to_53038"
}
BUDGETS=(1,2,4,8,16,31)

def h(x):
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def sig(b):
 return tuple((eid,e.key) for eid,e in sorted(b["eqs"].items()))

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--book3500",required=True); ap.add_argument("--out",required=True)
 a=ap.parse_args()
 doc=json.loads((Path(__file__).parent/"frozen_operator_v69.json").read_text())
 op=doc["operator"]; digest=h(op)
 if digest!=doc["sha256"]: raise RuntimeError(f"operator hash mismatch {digest}")

 lines,sha=V67.read_frozen_lines(Path(a.book3500),V58.EXPECTED_3500_SHA256)
 rows=[json.loads(x) for x in lines[V69.RECURRENCE_START:V69.RECURRENCE_END] if x.strip()]
 chosen=[r for r in rows if r["id"] in CAUSAL_IDS]
 if {r["id"] for r in chosen}!=CAUSAL_IDS:
  raise RuntimeError("missing causal V66 episodes")

 records=[]; meta_left=0; identical_points=0; divergent_points=0
 for p in chosen:
  first_cold=None; first_meta=None; points=[]
  for b in BUDGETS:
   cb=V70.compile_budgeted(p,"cold",op,b); mb=V70.compile_budgeted(p,"meta",op,b)
   same=sig(cb)==sig(mb)
   if same:
    identical_points+=1
    cold=V64.proof_for(p,cb["eqs"]); meta=cold
   else:
    divergent_points+=1
    cold=V64.proof_for(p,cb["eqs"]); meta=V64.proof_for(p,mb["eqs"])
   if cold["proved"] and first_cold is None: first_cold=b
   if meta["proved"] and first_meta is None: first_meta=b
   points.append({"budget":b,"same_basis":same,"cold":cold["proved"],"meta":meta["proved"],
                  "scope_active":bool(mb["scoped_seed_ids"])})
   if first_cold is not None and first_meta is not None: break
  left=first_meta is not None and (first_cold is None or first_meta<first_cold)
  meta_left+=int(left)
  records.append({"problem_id":p["id"],"source_id":V69.source_id(p),
                  "first_cold_budget":first_cold,"first_meta_budget":first_meta,
                  "meta_left_shift":left,"points":points})
  print(json.dumps(records[-1],sort_keys=True),flush=True)

 result={"schema":"mathgraph.compiled-developer.v71.selftest",
  "classification":"TRAINING_HISTORY_SELF_CONSISTENCY_NOT_TRANSFER_EVIDENCE",
  "operator_sha256":digest,"dataset_sha256":sha,"causal_episode_count":len(chosen),
  "meta_left_shift_episodes":meta_left,"identical_basis_points":identical_points,
  "divergent_basis_points":divergent_points,"records":records,
  "self_consistent":meta_left>0,
  "verdict":"PASS_COMPILED_DEVELOPER_CAUSAL_SELFTEST_V71" if meta_left>0 else "FAIL_COMPILED_DEVELOPER_CAUSAL_SELFTEST_V71"}
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 (out/"selftest.json").write_text(json.dumps(result,indent=2,sort_keys=True))
 print(json.dumps({k:result[k] for k in ("verdict","meta_left_shift_episodes","divergent_basis_points")},indent=2),flush=True)
 if not result["self_consistent"]: raise SystemExit("compiled developer fails causal self-test")
if __name__=="__main__": main()
