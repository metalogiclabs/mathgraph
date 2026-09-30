#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

BASE=Path("experiments/crystal_program_controller_v1/shared_calibration_v2.json")
EXT=Path("experiments/crystal_program_controller_v1/shared_calibration_v2_ethereum_extension.json")
OUT=Path("artifacts/crystal_program_controller_v1/shared_calibration_decision_v2_ethereum.json")

base=json.loads(BASE.read_text())
ext=json.loads(EXT.read_text())

assert base["measurement_boundary"]["contraction_basis"] == (
    "prospective_typed_residual_occurrence_contraction_fraction.v2"
)
assert base["measurement_boundary"]["cost_basis"] == "github_actions_job_wall_seconds.v1"
assert ext["measurement_boundary"]["unchanged_from_parent"] is True
assert ext["measurement_boundary"]["contraction_basis"] == base["measurement_boundary"]["contraction_basis"]
assert ext["measurement_boundary"]["cost_basis"] == base["measurement_boundary"]["cost_basis"]

rows=list(base["samples"])+[ext["sample"]]
for row in rows:
    before=int(row["occurrences_before"])
    after=int(row["occurrences_after"])
    contracted=int(row["typed_residual_occurrences_contracted"])
    wall=float(row["job_wall_seconds"])
    assert before>0
    assert 0<=after<=before
    assert contracted==before-after
    assert wall>0
    fraction=contracted/before
    rate=fraction/wall
    assert abs(fraction-float(row["contraction_fraction"]))<1e-15
    assert abs(rate-float(row["contraction_per_second"]))<1e-15

rates={r["campaign"]:r["contraction_per_second"] for r in rows}
assert rates["nucleus"] > rates["ethereum"] > rates["cross-prover"]
assert ext["decision"]["selected_current_campaign_id"] is None

result={
  "schema":"mathgraph.crystal-program-controller-shared-calibration-decision.v2.ethereum-extension",
  "status":"COMMON_MEASUREMENT_EXTENDED_NO_CURRENT_FORECAST",
  "measurement_boundary":base["measurement_boundary"],
  "completed_observed_order":ext["decision"]["completed_observed_order"],
  "rates":rates,
  "samples":rows,
  "selected_current_campaign_id":None,
  "selected_current_candidate_id":None,
  "rationale":ext["decision"]["reason"],
  "promotion_boundary":(
    "This extends the corrected V2 measurement to the prospectively frozen Ethereum V22 "
    "action. It compares completed experiment productivity only and does not forecast "
    "new live candidates."
  )
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps({
  "status":result["status"],
  "completed_observed_order":result["completed_observed_order"],
  "rates":rates,
  "selected_current_campaign_id":None,
},sort_keys=True))
