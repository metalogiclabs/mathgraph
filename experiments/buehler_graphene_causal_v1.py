#!/usr/bin/env python3
"""
Exact causal replay of Buehler graphene discovery as a Crystal developmental loop.

No fitted surrogate. No outcome-derived threshold.
Source pin: lamm-mit/graphene-agent@401e5f1...
Evidence sequence:
  pre-registered Stage-7 predictions -> observed separator ->
  geometry-derived tip-overlap distinction -> later paper controls/predictions.

Physical truth remains outside this boundary: all outcomes are screened-REBO2 model results.
"""
import hashlib, json, math, statistics, urllib.request
from collections import Counter
from pathlib import Path

REPO="lamm-mit/graphene-agent"
COMMIT="401e5f1f2a7529d8370a75a9c6b403bf2b9679ab"
PATH="carbon_discovery/experiments/database/index.jsonl"
URL=f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{PATH}"
OUT=Path("evidence/buehler-graphene-causal-v1")
OUT.mkdir(parents=True,exist_ok=True)

def fetch():
    req=urllib.request.Request(URL,headers={"User-Agent":"MathGraph-Crystal/1"})
    with urllib.request.urlopen(req,timeout=90) as r:
        return r.read()

def ape(y,p): return abs(float(p)-float(y))/max(abs(float(y)),1e-12)
def median(xs): return float(statistics.median(xs))

raw=fetch()
recs=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
by_name={r.get("name"):r for r in recs}

hold=[
 r for r in recs
 if r.get("stage")=="stage7_holdouts"
 and (r.get("metrics") or {}).get("strength_Nm") is not None
 and (r.get("prediction") or {}).get("strength_Nm") is not None
]
hold_rows=[]
for r in hold:
    y=float(r["metrics"]["strength_Nm"]); p=float(r["prediction"]["strength_Nm"])
    hold_rows.append({"name":r["name"],"actual_Nm":y,"pred_Nm":p,"ape":ape(y,p),
                      "basis":r["prediction"].get("basis"),
                      "mechanism_text":r["prediction"].get("crack_path_or_mechanism")})
source_holdout={
    "n":len(hold_rows),
    "median_ape":median([x["ape"] for x in hold_rows]),
    "mae_Nm":sum(abs(x["pred_Nm"]-x["actual_Nm"]) for x in hold_rows)/len(hold_rows),
    "rows":sorted(hold_rows,key=lambda x:x["ape"],reverse=True),
}

# The Stage-7 unseen 20-degree slit is the causal separator.
s7=by_name["S7_slit_20deg"]
s7_y=float(s7["metrics"]["strength_Nm"]); s7_p=float(s7["prediction"]["strength_Nm"])
s7d=s7["design"]
s7_margin=float(s7d["slit_len"])*abs(math.sin(math.radians(float(s7d["angle_deg"]))))-float(s7d["period_y"])/2
separator={
    "name":"S7_slit_20deg",
    "prediction_was_frozen_before_outcome": s7.get("stage")=="stage7_holdouts" and "holdout" in (s7.get("tags") or []),
    "old_prediction_Nm":s7_p,
    "actual_Nm":s7_y,
    "ape":ape(s7_y,s7_p),
    "old_basis":s7["prediction"].get("basis"),
    "old_mechanism":s7["prediction"].get("crack_path_or_mechanism"),
    "tip_overlap_margin_A":s7_margin,
}

# Geometry-only separator. For staggered slit rows separated by half period_y,
# projected slit span across rows is slit_len*sin(angle). Positive margin predicts
# geometrical tip overlap. This rule uses design geometry, not outcome values.
control_names=["P2_slit_20deg_phi0.10","S7_slit_20deg","P2_slit_20deg_phi0.30"]
controls=[]
for name in control_names:
    r=by_name[name]; d=r["design"]
    margin=float(d["slit_len"])*abs(math.sin(math.radians(float(d["angle_deg"]))))-float(d["period_y"])/2
    controls.append({
        "name":name,"stage":r["stage"],"slit_len_A":float(d["slit_len"]),
        "angle_deg":float(d["angle_deg"]),"period_y_A":float(d["period_y"]),
        "tip_overlap_margin_A":margin,"tip_overlap":margin>0,
        "strength_Nm":float(r["metrics"]["strength_Nm"]),
        "min_solid_fraction":float(r["descriptors"]["min_solid_fraction_across_x"]),
        "rule_prediction_Nm":(r.get("prediction") or {}).get("strength_Nm_rule",(r.get("prediction") or {}).get("strength_Nm")),
        "mechanism_prediction_Nm":(r.get("prediction") or {}).get("strength_Nm_mechanism"),
    })
no_ov=[x["strength_Nm"] for x in controls if not x["tip_overlap"]]
ov=[x["strength_Nm"] for x in controls if x["tip_overlap"]]
overlap_test={
    "law":"tip_overlap iff slit_len * abs(sin(angle_deg)) > period_y/2 for the staggered slit-row geometry",
    "rows":controls,
    "expected_pattern":["P2_slit_20deg_phi0.10:no_overlap","S7_slit_20deg:overlap","P2_slit_20deg_phi0.30:overlap"],
    "observed_pattern":[f'{x["name"]}:{"overlap" if x["tip_overlap"] else "no_overlap"}' for x in controls],
    "no_overlap_strength_median_Nm":median(no_ov),
    "overlap_strength_median_Nm":median(ov),
}
overlap_test["passed_geometry_control"]=(
    overlap_test["observed_pattern"]==overlap_test["expected_pattern"]
    and overlap_test["no_overlap_strength_median_Nm"]>overlap_test["overlap_strength_median_Nm"]
)

paper=[
 r for r in recs if r.get("stage")=="paper_sweeps"
 and (r.get("metrics") or {}).get("strength_Nm") is not None
 and (r.get("prediction") or {}).get("strength_Nm_rule") is not None
 and (r.get("prediction") or {}).get("strength_Nm_mechanism") is not None
]
paper_rows=[]
for r in paper:
    y=float(r["metrics"]["strength_Nm"])
    pr=float(r["prediction"]["strength_Nm_rule"])
    pm=float(r["prediction"]["strength_Nm_mechanism"])
    er,em=ape(y,pr),ape(y,pm)
    paper_rows.append({"name":r["name"],"family":r["family"],"actual_Nm":y,
                       "rule_Nm":pr,"mechanism_Nm":pm,"rule_ape":er,"mechanism_ape":em,
                       "mechanism_better":em<er})
paper_eval={
    "n":len(paper_rows),
    "rule_median_ape":median([x["rule_ape"] for x in paper_rows]),
    "mechanism_median_ape":median([x["mechanism_ape"] for x in paper_rows]),
    "rule_mae_Nm":sum(abs(x["rule_Nm"]-x["actual_Nm"]) for x in paper_rows)/len(paper_rows),
    "mechanism_mae_Nm":sum(abs(x["mechanism_Nm"]-x["actual_Nm"]) for x in paper_rows)/len(paper_rows),
    "mechanism_wins":sum(x["mechanism_better"] for x in paper_rows),
    "rule_wins_or_ties":sum(not x["mechanism_better"] for x in paper_rows),
    "rows":paper_rows,
}
paper_eval["passed_revision_test"]=(
    paper_eval["mechanism_median_ape"] < paper_eval["rule_median_ape"]
    and paper_eval["mechanism_wins"] > paper_eval["rule_wins_or_ties"]
)

checksums=sorted({str((r.get("engine") or {}).get("parameter_checksum"))
                  for r in recs if (r.get("engine") or {}).get("parameter_checksum")})

result={
 "schema":"mathgraph.crystal-buehler-graphene-causal-v1",
 "source":{"repo":REPO,"commit":COMMIT,"path":PATH,"raw_sha256":hashlib.sha256(raw).hexdigest(),
           "record_count":len(recs),"stage_counts":dict(Counter(r.get("stage") for r in recs))},
 "boundary":{
   "claim":"bounded executable evidence for residual-driven model refinement inside the source's screened-REBO2 world",
   "nonclaim":"no experimental validation and no cross-potential physical truth claim",
 },
 "stage7_preregistered_strength_prediction":source_holdout,
 "separator":separator,
 "overlap_refinement":overlap_test,
 "later_rule_vs_mechanism":paper_eval,
 "physical_model_perturbation":{
   "status":"UNKNOWN_NO_ALTERNATE_POTENTIAL_OUTCOMES",
   "parameter_checksums":checksums,
   "reason":"representation ablation is not a substitute for changing the physical law",
 },
}
result["promotion"]={
 "stage7_separator":"WARRANTED_BOUNDED" if separator["prediction_was_frozen_before_outcome"] and separator["ape"]>1.0 else "UNKNOWN",
 "tip_overlap_distinction":"WARRANTED_BOUNDED" if overlap_test["passed_geometry_control"] else "UNKNOWN",
 "residual_driven_mechanism_revision":"WARRANTED_BOUNDED" if paper_eval["passed_revision_test"] else "REJECTED_OR_UNKNOWN",
 "generic_minimum_interface":"UNKNOWN_NOT_ESTABLISHED_BY_THIS_REPLAY",
 "cross_potential_physical_robustness":"UNKNOWN",
}
result["next_residual"]=(
 "Freeze the warranted separator/distinction as a reusable consequence interface and test it on an "
 "independently generated alternate-potential or experimental graphene corpus. Until that passes, "
 "the mechanism remains model-bound."
)

assert len(recs)==132
assert len(hold_rows)==12
assert len(paper_rows)==18
assert overlap_test["passed_geometry_control"]
assert paper_eval["passed_revision_test"]

(OUT/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
print("SOURCE",result["source"])
print("STAGE7",source_holdout["median_ape"],source_holdout["mae_Nm"])
print("SEPARATOR",separator)
print("OVERLAP",overlap_test)
print("PAPER", {k:v for k,v in paper_eval.items() if k!="rows"})
print("PROMOTION",result["promotion"])
