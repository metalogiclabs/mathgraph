from __future__ import annotations
import json
from pathlib import Path
from mathgraph.programme_controller import Experiment, Residual, select_experiment

ROOT=Path(__file__).resolve().parent
src=json.loads((ROOT/"prospective_20260930.json").read_text())
residuals=[Residual(
    campaign=r["campaign"], protected_objective=r["protected_objective"],
    residual_id=r["residual_id"], residual_kind=r["residual_kind"],
    evidence_refs=tuple(r["evidence_refs"])
) for r in src["residuals"]]
experiments=[Experiment(
    experiment_id=e["experiment_id"], campaign=e["campaign"],
    residual_id=e["residual_id"], experiment_kind=e["experiment_kind"],
    expected_contraction=e["expected_contraction"], cost=e["cost"],
    evidence_refs=tuple(e["evidence_refs"])
) for e in src["experiments"]]
d=select_experiment(residuals, experiments)
out={
 "schema":"mathgraph.crystal-programme-prospective-selection-v1",
 "snapshot_commit_expected_parent":"506f4d71e1e242424addbffecd3437e945dbd313",
 "route":d.route,
 "campaign":d.residual.campaign if d.residual else None,
 "residual_id":d.residual.residual_id if d.residual else None,
 "experiment_id":d.experiment.experiment_id if d.experiment else None,
 "reason":d.reason,
 "utility":d.experiment.utility if d.experiment else None
}
(ROOT/"PROSPECTIVE_SELECTION.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps(out,sort_keys=True))
