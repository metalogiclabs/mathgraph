from __future__ import annotations
import json
from pathlib import Path
from mathgraph.programme_controller import Experiment, Residual, select_experiment

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "history.json").read_text())
rows = []
for case in data["cases"]:
    rr = case["residual"]
    residual = Residual(**rr)
    exps = []
    for row in case["experiments"]:
        exps.append(Experiment(
            experiment_id=row["experiment_id"],
            campaign=rr["campaign"],
            residual_id=rr["residual_id"],
            experiment_kind="retrospective_candidate",
            expected_contraction=row["expected_contraction"],
            cost=row["cost"],
            evidence_refs=tuple(rr["evidence_refs"]),
            requires_unearned_distinction=row.get("requires_unearned_distinction", False),
            repeats_superseded_route=row.get("repeats_superseded_route", False),
        ))
    d = select_experiment([residual], exps)
    got = d.experiment.experiment_id if d.experiment else d.route
    rows.append({"case": case["name"], "expected": case["expected"], "got": got, "pass": got == case["expected"]})
assert all(r["pass"] for r in rows), rows
out = {"schema": "mathgraph.crystal-programme-controller-replay-v1", "cases": rows, "passed": len(rows), "total": len(rows)}
(ROOT / "RESULT.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps(out, sort_keys=True))
