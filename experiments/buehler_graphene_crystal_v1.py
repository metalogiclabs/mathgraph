#!/usr/bin/env python3
"""
Crystal / Buehler exact graphene experiment V1.

Purpose
-------
Test a bounded ROS/Crystal claim on Buehler's exact autonomous graphene corpus:

  1. Freeze the source at an exact Git commit.
  2. Use discovery stages only to recover a small structural interface for strength.
  3. Qualify it once on the source-declared Stage-7 holdouts.
  4. Treat the 20-degree slit failure as a separator, derive the geometric
     tip-overlap distinction without using later outcomes, then test that
     distinction against later paper controls.
  5. Keep physical-model perturbation UNKNOWN because all mechanical outcomes
     in this corpus use the same screened REBO2 potential.

This is archive replay and bounded predictive/mechanistic evidence. It is not
experimental validation of graphene physics.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline

SOURCE_REPO = "lamm-mit/graphene-agent"
SOURCE_COMMIT = "401e5f1f2a7529d8370a75a9c6b403bf2b9679ab"
SOURCE_PATH = "carbon_discovery/experiments/database/index.jsonl"
SOURCE_URL = (
    f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_PATH}"
)

OUT = Path("evidence/buehler-graphene-crystal-v1")
OUT.mkdir(parents=True, exist_ok=True)

PRE_HOLDOUT_STAGES = {
    "stage1_baselines",
    "stage2_reconnaissance",
    "stage4_discriminating",
    "stage5_deep",
    "stage6_seeds",
}
HOLDOUT_STAGE = "stage7_holdouts"
PAPER_STAGE = "paper_sweeps"

FEATURE_POOL = [
    "min_solid_fraction_across_x",
    "porosity",
    "alignment_x",
    "anisotropy_index",
    "tortuosity_x",
    "hierarchy_depth_measured",
    "coarse_ligament_solid_fraction",
    "n_ligament_scales",
    "ligament_scale_ratio",
    "pore_size_std_A",
    "ligament_width_std_A",
    "fraction_undercoordinated",
    "cyclomatic_per_atom",
]
BASELINE_FEATURES = ["min_solid_fraction_across_x", "porosity"]

def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "MathGraph-Crystal/1"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def mape(y, p) -> float:
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    return float(np.median(np.abs(p - y) / np.maximum(np.abs(y), 1e-12)))

def ape(y: float, p: float) -> float:
    return abs(float(p) - float(y)) / max(abs(float(y)), 1e-12)

def model(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=240,
                    min_samples_leaf=2,
                    max_features=1.0,
                    random_state=seed,
                    n_jobs=-1,
                ),
            ),
        ]
    )

def structural_row(r: dict) -> dict:
    d = r.get("descriptors") or {}
    deg = d.get("ligament_orientation_deg")
    alignment = None if deg is None else abs(math.cos(math.radians(float(deg))))
    row = {
        "run_id": r.get("run_id"),
        "name": r.get("name"),
        "family": r.get("family"),
        "campaign": r.get("campaign"),
        "stage": r.get("stage"),
        "batch_name": r.get("batch_name") or r.get("stage") or r.get("run_id"),
        "strength_Nm": (r.get("metrics") or {}).get("strength_Nm"),
        "failure_strain": (r.get("metrics") or {}).get("failure_strain"),
        "work_to_failure_J_m2": (r.get("metrics") or {}).get("work_to_failure_J_m2"),
        "source_prediction_strength": (r.get("prediction") or {}).get("strength_Nm"),
        "source_rule_strength": (r.get("prediction") or {}).get("strength_Nm_rule"),
        "source_mechanism_strength": (r.get("prediction") or {}).get("strength_Nm_mechanism"),
        "min_solid_fraction_across_x": d.get("min_solid_fraction_across_x"),
        "porosity": d.get("porosity"),
        "alignment_x": alignment,
        "anisotropy_index": d.get("anisotropy_index"),
        "tortuosity_x": d.get("tortuosity_x"),
        "hierarchy_depth_measured": d.get("hierarchy_depth_measured"),
        "coarse_ligament_solid_fraction": d.get("coarse_ligament_solid_fraction"),
        "n_ligament_scales": d.get("n_ligament_scales"),
        "ligament_scale_ratio": d.get("ligament_scale_ratio"),
        "pore_size_std_A": d.get("pore_size_std_A"),
        "ligament_width_std_A": d.get("ligament_width_std_A"),
        "fraction_undercoordinated": d.get("fraction_undercoordinated"),
        "cyclomatic_per_atom": d.get("cyclomatic_per_atom"),
    }
    design = r.get("design") or {}
    for key in ("slit_len", "slit_w", "period_x", "period_y", "angle_deg"):
        row[key] = design.get(key)
    if r.get("family") == "slit_array":
        try:
            # Staggered rows are separated by half the y-period.  The projected
            # slit span normal to the row direction determines whether tips can
            # geometrically overlap/link between adjacent rows.
            margin = float(design["slit_len"]) * abs(
                math.sin(math.radians(float(design["angle_deg"])))
            ) - float(design["period_y"]) / 2.0
            row["tip_overlap_margin_A"] = margin
            row["tip_overlap"] = 1.0 if margin > 0 else 0.0
        except Exception:
            row["tip_overlap_margin_A"] = 0.0
            row["tip_overlap"] = 0.0
    else:
        row["tip_overlap_margin_A"] = 0.0
        row["tip_overlap"] = 0.0
    return row

def cv_predict_score(df: pd.DataFrame, feats: list[str], seed: int = 37) -> dict:
    x = df[feats]
    y = df["strength_Nm"].to_numpy(float)
    groups = df["batch_name"].astype(str).to_numpy()
    ng = len(np.unique(groups))
    if len(df) < 20 or ng < 3:
        return {"status": "UNKNOWN_INSUFFICIENT_CV", "median_ape": None}
    k = min(5, ng)
    cv = GroupKFold(n_splits=k)
    pred = cross_val_predict(model(seed), x, y, cv=cv, groups=groups, n_jobs=1)
    return {
        "status": "MEASURED",
        "median_ape": mape(y, pred),
        "mae_Nm": float(mean_absolute_error(y, pred)),
        "n": int(len(df)),
        "groups": int(ng),
    }

def eval_fit(train: pd.DataFrame, test: pd.DataFrame, feats: list[str], seed: int) -> dict:
    tr = train.dropna(subset=["strength_Nm"]).copy()
    te = test.dropna(subset=["strength_Nm"]).copy()
    if len(tr) < 10 or len(te) < 1:
        return {"status": "UNKNOWN_INSUFFICIENT_ROWS", "n_train": len(tr), "n_test": len(te)}
    pipe = model(seed)
    pipe.fit(tr[feats], tr["strength_Nm"].to_numpy(float))
    p = pipe.predict(te[feats])
    y = te["strength_Nm"].to_numpy(float)
    rows = []
    for (_, rr), yy, pp in zip(te.iterrows(), y, p):
        rows.append(
            {
                "name": rr["name"],
                "run_id": rr["run_id"],
                "family": rr["family"],
                "actual_Nm": float(yy),
                "pred_Nm": float(pp),
                "ape": ape(yy, pp),
            }
        )
    return {
        "status": "MEASURED",
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "median_ape": mape(y, p),
        "mae_Nm": float(mean_absolute_error(y, p)),
        "rows": rows,
    }

def select_min_interface(train: pd.DataFrame) -> dict:
    singles = []
    for feat in FEATURE_POOL:
        s = cv_predict_score(train, [feat], seed=101)
        singles.append({"features": [feat], **s})
    ranked = [
        x["features"][0]
        for x in sorted(
            [x for x in singles if x.get("median_ape") is not None],
            key=lambda z: (z["median_ape"], z["features"][0]),
        )[:8]
    ]
    trials = []
    for k in range(1, min(4, len(ranked)) + 1):
        for combo in itertools.combinations(ranked, k):
            s = cv_predict_score(train, list(combo), seed=103 + k)
            if s.get("median_ape") is not None:
                trials.append({"features": list(combo), **s})
    if not trials:
        return {"status": "UNKNOWN_NO_CV_TRIALS", "singles": singles}
    best_score = min(x["median_ape"] for x in trials)
    tolerance = max(0.01, 0.05 * best_score)
    admissible = [x for x in trials if x["median_ape"] <= best_score + tolerance]
    chosen = sorted(admissible, key=lambda x: (len(x["features"]), x["median_ape"], x["features"]))[0]
    baseline_cv = cv_predict_score(train, BASELINE_FEATURES, seed=107)
    full_cv = cv_predict_score(train, FEATURE_POOL, seed=109)
    return {
        "status": "FROZEN_BEFORE_HOLDOUT",
        "selection_rule": (
            "rank features by single-feature grouped CV; enumerate subsets of top 8 up to size 4; "
            "choose the smallest subset within max(0.01, 5%) median-APE of the best enumerated subset"
        ),
        "grouping": "GroupKFold by source batch_name",
        "ranked_top8": ranked,
        "best_enumerated_median_ape": best_score,
        "admissible_tolerance": tolerance,
        "chosen": chosen,
        "baseline_cv": baseline_cv,
        "full_pool_cv": full_cv,
        "singles": singles,
        "top_trials": sorted(trials, key=lambda x: (x["median_ape"], len(x["features"])))[:30],
    }

def source_prediction_eval(df: pd.DataFrame, col: str) -> dict:
    sub = df.dropna(subset=["strength_Nm", col]).copy()
    if len(sub) == 0:
        return {"status": "UNKNOWN_NO_PREDICTIONS", "n": 0}
    y = sub["strength_Nm"].to_numpy(float)
    p = sub[col].to_numpy(float)
    rows = [
        {
            "name": rr["name"],
            "actual_Nm": float(yy),
            "pred_Nm": float(pp),
            "ape": ape(yy, pp),
        }
        for (_, rr), yy, pp in zip(sub.iterrows(), y, p)
    ]
    return {
        "status": "MEASURED",
        "n": int(len(sub)),
        "median_ape": mape(y, p),
        "mae_Nm": float(mean_absolute_error(y, p)),
        "rows": rows,
    }

def paper_rule_vs_mechanism(df: pd.DataFrame) -> dict:
    sub = df.dropna(subset=["strength_Nm", "source_rule_strength", "source_mechanism_strength"]).copy()
    rows = []
    for _, r in sub.iterrows():
        y = float(r["strength_Nm"])
        er = ape(y, float(r["source_rule_strength"]))
        em = ape(y, float(r["source_mechanism_strength"]))
        rows.append(
            {
                "name": r["name"],
                "family": r["family"],
                "actual_Nm": y,
                "rule_Nm": float(r["source_rule_strength"]),
                "mechanism_Nm": float(r["source_mechanism_strength"]),
                "rule_ape": er,
                "mechanism_ape": em,
                "mechanism_better": em < er,
            }
        )
    if not rows:
        return {"status": "UNKNOWN_NO_COMPARABLE_PREDICTIONS", "n": 0}
    return {
        "status": "MEASURED",
        "n": len(rows),
        "rule_median_ape": float(np.median([x["rule_ape"] for x in rows])),
        "mechanism_median_ape": float(np.median([x["mechanism_ape"] for x in rows])),
        "rule_mae_Nm": float(np.mean([abs(x["rule_Nm"] - x["actual_Nm"]) for x in rows])),
        "mechanism_mae_Nm": float(np.mean([abs(x["mechanism_Nm"] - x["actual_Nm"]) for x in rows])),
        "mechanism_wins": int(sum(x["mechanism_better"] for x in rows)),
        "rule_wins_or_ties": int(sum(not x["mechanism_better"] for x in rows)),
        "rows": rows,
    }

def main() -> int:
    raw = get_bytes(SOURCE_URL)
    sha256 = hashlib.sha256(raw).hexdigest()
    records = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    df = pd.DataFrame([structural_row(r) for r in records])
    train = df[df["stage"].isin(PRE_HOLDOUT_STAGES)].copy()
    hold = df[df["stage"] == HOLDOUT_STAGE].copy()
    paper = df[df["stage"] == PAPER_STAGE].copy()

    out = {
        "schema": "mathgraph.crystal-buehler-graphene-v1",
        "source": {
            "repo": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "raw_sha256": sha256,
            "record_count": len(records),
            "stage_counts": dict(Counter(r.get("stage") for r in records)),
            "campaign_counts": dict(Counter(r.get("campaign") for r in records)),
        },
        "boundary": {
            "protected_target": "metrics.strength_Nm",
            "pre_holdout_stages": sorted(PRE_HOLDOUT_STAGES),
            "qualification_stage": HOLDOUT_STAGE,
            "later_transfer_stage": PAPER_STAGE,
            "feature_policy": "structure-only descriptors; no fracture/damage/outcome descriptors; no family identity",
            "physical_scope": "all outcomes are source-model results under screened REBO2; no experimental-truth claim",
        },
        "counts": {
            "pre_holdout_train": int(len(train)),
            "stage7_holdout": int(len(hold)),
            "paper_transfer": int(len(paper)),
        },
    }

    selection = select_min_interface(train)
    out["pre_holdout_interface_selection"] = selection

    if selection.get("status") != "FROZEN_BEFORE_HOLDOUT":
        out["overall_status"] = "UNKNOWN"
        out["residual"] = "Could not freeze a training-only structural interface."
        (OUT / "result.json").write_text(json.dumps(out, indent=2, sort_keys=True))
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    chosen = selection["chosen"]["features"]
    source_stage7 = source_prediction_eval(hold, "source_prediction_strength")
    chosen_stage7 = eval_fit(train, hold, chosen, seed=131)
    baseline_stage7 = eval_fit(train, hold, BASELINE_FEATURES, seed=137)
    out["stage7_qualification"] = {
        "chosen_features": chosen,
        "source_preregistered": source_stage7,
        "crystal_selected": chosen_stage7,
        "learned_net_section_baseline": baseline_stage7,
    }

    # Pre-declared bounded qualification condition.  The learned representation must
    # be compact, useful on the frozen holdout, and not worse than the source's
    # already pre-registered Stage-7 strength predictor.
    qualify = (
        chosen_stage7.get("status") == "MEASURED"
        and source_stage7.get("status") == "MEASURED"
        and len(chosen) <= 4
        and chosen_stage7["median_ape"] <= 0.20
        and chosen_stage7["median_ape"] <= source_stage7["median_ape"] + 1e-12
    )
    out["stage7_qualification"]["criterion"] = (
        "chosen size <=4, Stage-7 median APE <=20%, and no worse than source pre-registered Stage-7 median APE"
    )
    out["stage7_qualification"]["passed"] = bool(qualify)

    # Exact Stage-7 separator: source forecast vs outcome for the unseen 20-degree slit.
    sep = hold[hold["name"] == "S7_slit_20deg"]
    separator = {"status": "UNKNOWN_MISSING_S7_SLIT20"}
    if len(sep) == 1:
        r = sep.iloc[0]
        separator = {
            "status": "OBSERVED_SEPARATOR",
            "name": r["name"],
            "source_prediction_Nm": float(r["source_prediction_strength"]),
            "actual_Nm": float(r["strength_Nm"]),
            "ape": ape(float(r["strength_Nm"]), float(r["source_prediction_strength"])),
            "design": {
                "slit_len_A": float(r["slit_len"]),
                "period_y_A": float(r["period_y"]),
                "angle_deg": float(r["angle_deg"]),
                "tip_overlap_margin_A": float(r["tip_overlap_margin_A"]),
                "tip_overlap": int(r["tip_overlap"]),
            },
        }
    out["stage7_separator"] = separator

    # Later 20-degree controls.  This geometric distinction is derived from design
    # geometry, not their outcomes: projected slit span across adjacent staggered
    # rows versus half-row spacing.
    names = {"P2_slit_20deg_phi0.10", "S7_slit_20deg", "P2_slit_20deg_phi0.30"}
    controls = df[df["name"].isin(names)].copy()
    control_rows = []
    for _, r in controls.sort_values("slit_len").iterrows():
        control_rows.append(
            {
                "name": r["name"],
                "stage": r["stage"],
                "slit_len_A": float(r["slit_len"]),
                "angle_deg": float(r["angle_deg"]),
                "period_y_A": float(r["period_y"]),
                "tip_overlap_margin_A": float(r["tip_overlap_margin_A"]),
                "tip_overlap": int(r["tip_overlap"]),
                "min_solid_fraction": float(r["min_solid_fraction_across_x"]),
                "strength_Nm": float(r["strength_Nm"]),
            }
        )
    no_ov = [x["strength_Nm"] for x in control_rows if x["tip_overlap"] == 0]
    ov = [x["strength_Nm"] for x in control_rows if x["tip_overlap"] == 1]
    out["overlap_refinement"] = {
        "status": "MEASURED" if len(control_rows) == 3 and no_ov and ov else "UNKNOWN_INCOMPLETE_CONTROLS",
        "derived_law": "tip_overlap iff slit_len * abs(sin(angle_deg)) > period_y / 2 for staggered slit rows",
        "rows": control_rows,
        "no_overlap_strength_median_Nm": float(np.median(no_ov)) if no_ov else None,
        "overlap_strength_median_Nm": float(np.median(ov)) if ov else None,
    }

    # Later source-authored paper predictions explicitly record both the old rule
    # prediction and revised mechanism prediction.  Treat this as independent
    # archive evidence for whether mechanism revision improved prediction.
    out["paper_rule_vs_mechanism"] = paper_rule_vs_mechanism(paper)

    # Test whether the acquired overlap distinction has future predictive consequence.
    # Fit after Stage 7 (the separator is now allowed into live state), then test only
    # on later paper sweeps.
    post_train = pd.concat([train, hold], ignore_index=True)
    generic_paper = eval_fit(post_train, paper, chosen, seed=149)
    overlap_feats = list(dict.fromkeys(chosen + ["tip_overlap", "tip_overlap_margin_A"]))
    overlap_paper = eval_fit(post_train, paper, overlap_feats, seed=151)
    paper_slit = paper[paper["family"] == "slit_array"].copy()
    generic_slit = eval_fit(post_train, paper_slit, chosen, seed=157)
    overlap_slit = eval_fit(post_train, paper_slit, overlap_feats, seed=163)
    out["post_separator_transfer"] = {
        "training_boundary": "pre-holdout discovery + Stage-7 after separator observation",
        "test_boundary": "later paper_sweeps only",
        "generic_features": chosen,
        "refined_features": overlap_feats,
        "all_paper_generic": generic_paper,
        "all_paper_refined": overlap_paper,
        "slit_paper_generic": generic_slit,
        "slit_paper_refined": overlap_slit,
    }

    # Model falsification boundary: all 132 records use the same declared screened REBO2
    # potential lineage; without an independently simulated alternate-potential corpus,
    # physical-law robustness must remain UNKNOWN.
    parameter_checksums = sorted(
        {
            str((r.get("engine") or {}).get("parameter_checksum"))
            for r in records
            if (r.get("engine") or {}).get("parameter_checksum")
        }
    )
    out["physical_model_perturbation"] = {
        "status": "UNKNOWN_NO_INDEPENDENT_ALTERNATE_POTENTIAL_CORPUS",
        "observed_parameter_checksums": parameter_checksums,
        "reason": (
            "The archive qualifies consequences inside one screened-REBO2 model lineage. "
            "A representation ablation is not a substitute for changing the physical law."
        ),
    }

    paper_cmp = out["paper_rule_vs_mechanism"]
    overlap_ok = (
        out["overlap_refinement"]["status"] == "MEASURED"
        and out["overlap_refinement"]["no_overlap_strength_median_Nm"]
        > out["overlap_refinement"]["overlap_strength_median_Nm"]
    )
    mechanism_improved = (
        paper_cmp.get("status") == "MEASURED"
        and paper_cmp["mechanism_median_ape"] < paper_cmp["rule_median_ape"]
        and paper_cmp["mechanism_wins"] > paper_cmp["rule_wins_or_ties"]
    )

    out["promotion"] = {
        "compact_predictive_interface": (
            "WARRANTED_BOUNDED" if qualify else "REJECTED_ON_STAGE7_QUALIFICATION"
        ),
        "stage7_20deg_separator": (
            "WARRANTED_BOUNDED" if separator.get("status") == "OBSERVED_SEPARATOR" else "UNKNOWN"
        ),
        "tip_overlap_refinement": "WARRANTED_BOUNDED" if overlap_ok else "UNKNOWN",
        "mechanism_revision_improves_paper_predictions": (
            "WARRANTED_BOUNDED" if mechanism_improved else "REJECTED_OR_UNKNOWN"
        ),
        "physical_model_robustness": "UNKNOWN",
    }
    out["overall_status"] = "COMPLETE_BOUNDED_EXPERIMENT"
    out["next_residual"] = (
        "Run the frozen compiled interface against an independently generated alternate-potential "
        "or experimental graphene corpus; until then all mechanics claims remain REBO2-model-bound."
    )

    (OUT / "result.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print("SOURCE_SHA256", sha256)
    print("COUNTS", out["counts"])
    print("CHOSEN", chosen)
    print("STAGE7_SOURCE_MEDIAN_APE", source_stage7.get("median_ape"))
    print("STAGE7_CRYSTAL_MEDIAN_APE", chosen_stage7.get("median_ape"))
    print("STAGE7_BASELINE_MEDIAN_APE", baseline_stage7.get("median_ape"))
    print("STAGE7_QUALIFIED", qualify)
    print("SEPARATOR", json.dumps(separator, sort_keys=True))
    print("OVERLAP", json.dumps(out["overlap_refinement"], sort_keys=True))
    print("PAPER_RULE_VS_MECH", json.dumps(paper_cmp, sort_keys=True))
    print("POST_SEPARATOR", json.dumps(out["post_separator_transfer"], sort_keys=True))
    print("PROMOTION", json.dumps(out["promotion"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
