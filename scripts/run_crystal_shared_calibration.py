#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

SRC=Path("experiments/crystal_program_controller_v1/shared_calibration_v1.json")
OUT=Path("artifacts/crystal_program_controller_v1/shared_calibration_decision.json")

data=json.loads(SRC.read_text())
assert data["schema"]=="mathgraph.crystal-program-controller-shared-calibration.v1"
basis=data["measurement_boundary"]
assert basis["contraction_basis"]=="prospective_verified_obligations_fraction.v1"
assert basis["cost_basis"]=="github_actions_job_wall_seconds.v1"
samples=data["samples"]
assert len(samples)==2
assert {x["campaign"] for x in samples}=={"nucleus","cross-prover"}
for row in samples:
    total=int(row["obligations_total"])
    closed=int(row["obligations_closed"])
    wall=float(row["job_wall_seconds"])
    assert total>0 and 0<=closed<=total and wall>0
    fraction=closed/total
    rate=fraction/wall
    assert abs(fraction-float(row["verified_obligations_fraction"]))<1e-15
    assert abs(rate-float(row["verified_contraction_per_second"]))<1e-15

# A programme action requires positive evidence-backed calibrated contraction.
positive=[r for r in samples if float(r["verified_contraction_per_second"])>0]
assert not positive
decision=data["decision"]
assert decision["status"]=="HOLD_ZERO_CALIBRATED_CONTRACTION"
assert decision["selected_campaign_id"] is None
assert decision["selected_candidate_id"] is None

result={
    "schema":"mathgraph.crystal-program-controller-shared-calibration-decision.v1",
    "status":decision["status"],
    "measurement_boundary":basis,
    "sample_count":len(samples),
    "positive_sample_count":len(positive),
    "samples":samples,
    "selected_campaign_id":None,
    "selected_candidate_id":None,
    "rationale":decision["reason"],
    "promotion_boundary":data["promotion_boundary"],
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps({
    "status":result["status"],
    "sample_count":result["sample_count"],
    "positive_sample_count":result["positive_sample_count"],
    "rates":{r["campaign"]:r["verified_contraction_per_second"] for r in samples},
},sort_keys=True))
