from __future__ import annotations
import json
from pathlib import Path
from mathgraph.programme_controller import Experiment, Residual, select_experiment

root = Path(__file__).resolve().parent
payload = json.loads((root / "prospective_round1.json").read_text())
residuals = [Residual(
    campaign=r["campaign"],
    protected_objective=r["protected_objective"],
    residual_id=r["residual_id"],
    residual_kind=r["residual_kind"],
    evidence_refs=tuple(r["evidence_refs"]),
) for r in payload["residuals"]]
experiments = [Experiment(
    experiment_id=e["experiment_id"],
    campaign=e["campaign"],
    residual_id=e["residual_id"],
    experiment_kind=e["experiment_kind"],
    expected_contraction=float(e["expected_contraction"]),
    cost=float(e["cost"]),
    executable=bool(e.get("executable", True)),
    evidence_refs=(),
) for e in payload["experiments"]]
d = select_experiment(residuals, experiments)
out = {
    "schema": "mathgraph.crystal-programme-prospective-selection-v1",
    "route": d.route,
    "campaign": d.residual.campaign if d.residual else None,
    "residual_id": d.residual.residual_id if d.residual else None,
    "experiment_id": d.experiment.experiment_id if d.experiment else None,
    "utility": d.experiment.utility if d.experiment else None,
    "reason": d.reason,
    "source_manifest": "prospective_round1.json"
}
(root / "SELECTION.json").write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
print(json.dumps(out, sort_keys=True))
