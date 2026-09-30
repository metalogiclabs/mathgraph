#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

SRC=Path("experiments/crystal_program_controller_v1/shared_calibration_v2.json")
OUT=Path("artifacts/crystal_program_controller_v1/shared_calibration_decision_v2.json")
data=json.loads(SRC.read_text())
assert data["schema"]=="mathgraph.crystal-program-controller-shared-calibration.v2"
basis=data["measurement_boundary"]
assert basis["contraction_basis"]=="prospective_typed_residual_occurrence_contraction_fraction.v2"
assert basis["cost_basis"]=="github_actions_job_wall_seconds.v1"
rows=data["samples"]
assert len(rows)==2
for row in rows:
    before=int(row["occurrences_before"])
    after=int(row["occurrences_after"])
    contracted=int(row["typed_residual_occurrences_contracted"])
    wall=float(row["job_wall_seconds"])
    assert before>0 and 0<=after<=before and contracted==before-after
    assert wall>0
    fraction=contracted/before
    rate=fraction/wall
    assert abs(fraction-float(row["contraction_fraction"]))<1e-15
    assert abs(rate-float(row["contraction_per_second"]))<1e-15

by={r["campaign"]:r for r in rows}
assert by["nucleus"]["occurrences_before"]==11
assert by["nucleus"]["occurrences_after"]==0
assert by["nucleus"]["total_residual_before"]==by["nucleus"]["total_residual_after"]==30
assert by["cross-prover"]["occurrences_before"]==32
assert by["cross-prover"]["occurrences_after"]==32
assert by["nucleus"]["contraction_per_second"]>by["cross-prover"]["contraction_per_second"]

decision=data["decision"]
assert decision["status"]=="COMMON_MEASUREMENT_EARNED_NO_NEW_GLOBAL_PICK"
assert decision["observed_best_sample"]=="nucleus"
assert decision["selected_current_campaign_id"] is None
assert decision["selected_current_candidate_id"] is None

result={
  "schema":"mathgraph.crystal-program-controller-shared-calibration-decision.v2",
  "status":decision["status"],
  "measurement_boundary":basis,
  "observed_best_sample":decision["observed_best_sample"],
  "rates":{r["campaign"]:r["contraction_per_second"] for r in rows},
  "samples":rows,
  "selected_current_campaign_id":None,
  "selected_current_candidate_id":None,
  "rationale":decision["reason"],
  "promotion_boundary":data["promotion_boundary"],
  "supersedes":data["supersedes"],
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps({
  "status":result["status"],
  "observed_best_sample":result["observed_best_sample"],
  "rates":result["rates"],
  "selected_current_campaign_id":None,
},sort_keys=True))
