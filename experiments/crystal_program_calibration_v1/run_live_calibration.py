from __future__ import annotations

import json
from pathlib import Path

from mathgraph.research_controller import (
    calibration_from_dict,
    campaign_state_from_dict,
    candidate_from_dict,
    decide_calibrated_continuation,
)

ROOT = Path(__file__).resolve().parent
snapshot = json.loads((ROOT / "live_ros_snapshot_v2.json").read_text())
calibration_doc = json.loads((ROOT / "calibration_records.json").read_text())

states = [campaign_state_from_dict(row["state"]) for row in snapshot["campaigns"]]
candidates = [
    candidate_from_dict(candidate)
    for row in snapshot["campaigns"]
    for candidate in row.get("candidates", [])
]
records = [calibration_from_dict(row) for row in calibration_doc["records"]]

decision = decide_calibrated_continuation(
    states,
    candidates,
    records,
    calibration_epoch=snapshot["calibration_epoch"],
)

expected = snapshot["expected_calibrated_status"]
expected_missing = sorted(snapshot["expected_missing_calibration_campaigns"])
assert decision.status == expected, decision.to_dict()
assert sorted(decision.missing_campaign_ids) == expected_missing, decision.to_dict()

scores = {
    row.campaign_id: row.observed_score
    for row in records
}
out = {
    "schema": "mathgraph.crystal-program-calibrated-live-decision.v1",
    "snapshot": "live_ros_snapshot_v2.json",
    "calibration_epoch": snapshot["calibration_epoch"],
    "decision": decision.to_dict(),
    "measured_scores": scores,
    "nucleus_over_cross_prover": (
        scores["nucleus"] > scores["cross-prover"]
    ),
    "programme_claim": (
        "HOLD: Nucleus beats cross-prover on the measured pilot basis, "
        "but ACC and Collatz lack fresh calibration records for their current states."
    ),
}
(ROOT / "LIVE_CALIBRATED_DECISION.json").write_text(
    json.dumps(out, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(out, sort_keys=True))
