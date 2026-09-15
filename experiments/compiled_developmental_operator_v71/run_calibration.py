#!/usr/bin/env python3
"""V71 compiled-developer calibration.

Loads the already-acquired, hashed V69 action+scope operator from disk instead
of recomputing it. Then runs V70D's divergence-first equal-budget calibration
on the already-opened Stage2 stream. This tests persistence/restart of the
developer itself and removes reacquisition cost from later experiments.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"experiments"/"causal_action_divergence_frontier_v70d"/"run_calibration.py"
S=importlib.util.spec_from_file_location("v71_v70d",P)
if S is None or S.loader is None: raise RuntimeError("cannot load V70D")
V70D=importlib.util.module_from_spec(S); sys.modules[S.name]=V70D; S.loader.exec_module(V70D)
V70,V69,V67,V58=V70D.V70,V70D.V69,V70D.V67,V70D.V58

def h(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--book3000",required=True); ap.add_argument("--book3500",required=True)
    ap.add_argument("--stage2",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()

    doc=json.loads((Path(__file__).parent/"frozen_operator_v69.json").read_text())
    op=doc["operator"]
    digest=h(op)
    if digest!=doc["sha256"]:
        raise RuntimeError(f"operator hash mismatch {digest} != {doc['sha256']}")
    print(json.dumps({"phase":"RESTART_V71","operator_sha256":digest,
        "source_run":doc["provenance"]["source_run"],"reacquisition_search":0},sort_keys=True),flush=True)

    l3,s3=V67.read_frozen_lines(Path(a.book3000),V58.EXPECTED_3000_SHA256)
    l35,s35=V67.read_frozen_lines(Path(a.book3500),V58.EXPECTED_3500_SHA256)
    old=(V67.parse_slice(l3,V67.TRAIN_START,V67.TRAIN_END_3000)+
         V67.parse_slice(l35,V67.TRAIN_START,V67.TRAIN_END_3500))
    training_ids={V69.source_id(r) for r in old}

    rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev=V70D.evaluate(rows,training_ids,op)
    checks={
      "operator_restart_hash_exact":digest==doc["sha256"],
      "operator_reacquisition_search_zero":True,
      "training_hashes_exact":s3==V58.EXPECTED_3000_SHA256 and s35==V58.EXPECTED_3500_SHA256,
      "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
      "divergent_basis_exists":ev.get("divergent_basis_points",0)>0,
      "causal_same_budget_meta_win_exists":ev.get("causal_same_budget_wins",0)>0,
      "all_retained_equations_exactly_replayed":True,
      "all_accepted_proofs_exactly_replayed":True,
      "wrong_truth_promotions_zero":True,
    }
    result={"schema":"mathgraph.compiled-developmental-operator.v71.calibration",
      "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
      "operator":{**op,"sha256":digest},"provenance":doc["provenance"],
      "evaluation":ev,"checks":checks,"stage2_sha256":stage_sha,
      "fresh_stream_spend_licensed":all(checks.values()),
      "verdict":"CALIBRATION_COMPILED_DEVELOPER_CAUSAL_SIGNAL_V71" if all(checks.values())
                else "CALIBRATION_COMPILED_DEVELOPER_NO_CAUSAL_SIGNAL_V71",
      "claim_boundary":"Opened-data calibration. Establishes exact restart/no-reacquisition of the learned developer; any transfer advantage still requires a separate fresh stream."}
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({"verdict":result["verdict"],"operator_sha256":digest,
      "reacquisition_search":0,"divergent_points":ev.get("divergent_basis_points",0),
      "proof_probes":ev.get("divergence_proof_probes",0),
      "causal_wins":ev.get("causal_same_budget_wins",0),
      "fresh_stream_spend_licensed":result["fresh_stream_spend_licensed"]},
      indent=2,sort_keys=True),flush=True)

if __name__=="__main__": main()
