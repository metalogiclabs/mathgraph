#!/usr/bin/env python3
"""
Crystal / Buehler physical-loop V1.

Boundary:
- First probes public LAMM Hugging Face metadata for an exact graphene/REBO archive.
- If that exact archive is not publicly discoverable, DOES NOT pretend otherwise.
- Executes the same consequential-interface test on the pinned public
  lamm-mit/MetaMaterialsDiscovery Run 3 archive as a proxy.
- Uses only pre-simulation-looking design descriptors to predict protected
  mechanical consequences.
- Selects the smallest interface on training-only CV, freezes it, then evaluates
  source-recorded holdouts.
- Tests geometry-family transfer when discoverable.
- Tests an alternate beam-theory world (Euler/Timoshenko) when both are present;
  otherwise reports UNKNOWN rather than synthesizing a fake physical perturbation.

This is an empirical archive-replay experiment, not proof of physical truth.
"""

from __future__ import annotations
import csv, hashlib, itertools, json, math, os, re, sys, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import median_absolute_error
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

HF_REPO = "lamm-mit/MetaMaterialsDiscovery"
HF_REV = "b79e437cd7866bc33e2f8e0ff50d1353593d8111"
RUN3 = "data/Run 3/RESULTS_Run 3"
OUT = Path("evidence/buehler-physical-loop-v1")
OUT.mkdir(parents=True, exist_ok=True)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def fetch_url(url: str, timeout=60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "MathGraph-Crystal/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def hf_file(path: str) -> tuple[bytes, str]:
    qpath = urllib.parse.quote(path, safe="/")
    url = f"https://huggingface.co/{HF_REPO}/resolve/{HF_REV}/{qpath}"
    data = fetch_url(url)
    return data, url

def probe_exact_graphene_source():
    probes = {}
    terms = ("graphene", "rebo", "atomistic", "metamaterial")
    endpoints = [
        ("models", "https://huggingface.co/api/models?author=lamm-mit&limit=200&full=true"),
        ("datasets", "https://huggingface.co/api/datasets?author=lamm-mit&limit=200&full=true"),
    ]
    candidates = []
    for kind, url in endpoints:
        try:
            raw = fetch_url(url)
            arr = json.loads(raw)
            probes[kind] = {"count": len(arr), "sha256": sha256_bytes(raw)}
            for obj in arr:
                ident = str(obj.get("id") or obj.get("modelId") or "")
                blob = json.dumps(obj).lower()
                score = sum(t in blob for t in terms)
                if score:
                    candidates.append({
                        "kind": kind,
                        "id": ident,
                        "score": score,
                        "lastModified": obj.get("lastModified"),
                        "sha": obj.get("sha"),
                    })
        except Exception as e:
            probes[kind] = {"error": repr(e)}
    candidates.sort(key=lambda x: (-x["score"], str(x.get("lastModified") or "")), reverse=False)
    # Exact means we can identify a 2026 archive whose metadata itself contains both graphene and REBO.
    exact = [c for c in candidates if c["score"] >= 2 and "2026" in str(c.get("lastModified") or "")]
    return {
        "status": "FOUND_CANDIDATE" if exact else "UNKNOWN_PUBLIC_SOURCE",
        "criteria": "public LAMM HF metadata contains >=2 of {graphene,rebo,atomistic,metamaterial} and a 2026 modification",
        "exact_candidates": exact[:20],
        "near_candidates": candidates[:20],
        "probe": probes,
    }

def write_raw(rel: str, data: bytes):
    p = OUT / "source" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)

def load_proxy_sources():
    requested = [
        "README.md",
        f"{RUN3}/README.md",
        f"{RUN3}/manifest.json",
        f"{RUN3}/data/holdout_predictions.json",
        f"{RUN3}/data/processed/runs_table.csv",
        f"{RUN3}/data/processed/holdout_comparison.csv",
        f"{RUN3}/analysis/predict_holdout.py",
        f"{RUN3}/analysis/holdout_eval.py",
    ]
    got, missing = {}, {}
    for path in requested:
        try:
            data, url = hf_file(path)
            got[path] = {"bytes": len(data), "sha256": sha256_bytes(data), "url": url}
            write_raw(path.replace("/", "__"), data)
        except Exception as e:
            missing[path] = repr(e)
    return got, missing

def read_saved(rel_source_name: str) -> bytes | None:
    p = OUT / "source" / rel_source_name.replace("/", "__")
    return p.read_bytes() if p.exists() else None

def flatten_values(x):
    vals = []
    if isinstance(x, dict):
        for k, v in x.items():
            vals.append(k)
            vals.extend(flatten_values(v))
    elif isinstance(x, list):
        for v in x:
            vals.extend(flatten_values(v))
    elif isinstance(x, (str, int, float)):
        vals.append(x)
    return vals

OUTCOME_TOKENS = (
    "force","load","work","energy","stiff","fail","damage","avalanche","drop",
    "residual","converg","disp","strain","stress","metric","pred","error",
    "tough","strength","response","event","step","time"
)
DESIGN_HINTS = (
    "hier","gamma","ratio","density","width","angle","orient","disorder","level",
    "branch","family","preset","design","geometry","interface","kappa","seed","span",
    "cell","nx","ny","scale","topology","pattern","depth","material"
)
ID_HINTS = ("run_id","design_id","id","name","label","case","specimen")

def normalize(s):
    return re.sub(r"[^a-z0-9]+","_",str(s).lower()).strip("_")

def map_holdout_ids(runs: pd.DataFrame, hold: pd.DataFrame | None, pred_json) -> tuple[str|None,set[str],dict]:
    info = {}
    run_cols = {normalize(c): c for c in runs.columns}
    idcol = None
    for hint in ID_HINTS:
        if hint in run_cols:
            idcol = run_cols[hint]; break
    if idcol is None:
        for c in runs.columns:
            if runs[c].dtype == object and runs[c].nunique(dropna=True) >= max(5, int(0.3*len(runs))):
                idcol = c; break
    if idcol is None:
        return None, set(), {"reason":"no plausible id column"}

    runids = {str(v) for v in runs[idcol].dropna().tolist()}
    ids = set()

    if hold is not None:
        for c in hold.columns:
            vals = {str(v) for v in hold[c].dropna().tolist()}
            overlap = vals & runids
            if overlap:
                ids |= overlap
                info[f"holdout_col:{c}"] = len(overlap)

    if pred_json is not None:
        vals = {str(v) for v in flatten_values(pred_json)}
        overlap = vals & runids
        if overlap:
            ids |= overlap
            info["prediction_json_matches"] = len(overlap)

    return idcol, ids, info

def protected_targets(runs: pd.DataFrame):
    groups = {
        "peak_force": ("peak_force","peakload","peak_load","f_peak","max_force"),
        "work_to_failure": ("work_to_failure","work_failure","work","energy_to_failure"),
        "initial_stiffness": ("initial_stiffness","stiffness","k_initial"),
    }
    norm = {normalize(c): c for c in runs.columns}
    out = {}
    for g, aliases in groups.items():
        for a in aliases:
            for nc, c in norm.items():
                if nc == a or nc.endswith("_"+a) or a in nc:
                    if pd.api.types.is_numeric_dtype(runs[c]):
                        out[g] = c
                        break
            if g in out: break
    return out

def candidate_features(runs: pd.DataFrame, target_cols, idcol):
    feats = []
    for c in runs.columns:
        nc = normalize(c)
        if c == idcol or c in target_cols: continue
        if any(tok in nc for tok in OUTCOME_TOKENS): continue
        nunq = runs[c].nunique(dropna=True)
        if nunq <= 1: continue
        if pd.api.types.is_numeric_dtype(runs[c]):
            if any(h in nc for h in DESIGN_HINTS) or len(feats) < 12:
                feats.append(c)
        elif nunq <= 20 and any(h in nc for h in DESIGN_HINTS):
            feats.append(c)
    # cap to avoid combinatorial bloat; preserve explicit design-hint columns first
    feats = sorted(feats, key=lambda c: (0 if any(h in normalize(c) for h in DESIGN_HINTS) else 1, str(c)))
    return feats[:16]

def median_ape(y_true, y_pred):
    y_true=np.asarray(y_true,float); y_pred=np.asarray(y_pred,float)
    denom=np.maximum(np.abs(y_true), 1e-12)
    return float(np.median(np.abs(y_pred-y_true)/denom))

def build_model(X: pd.DataFrame, features, random_state=37):
    cat=[c for c in features if not pd.api.types.is_numeric_dtype(X[c])]
    num=[c for c in features if c not in cat]
    ct=ColumnTransformer([
        ("num","passthrough",num),
        ("cat",OneHotEncoder(handle_unknown="ignore"),cat)
    ], remainder="drop")
    rf=RandomForestRegressor(
        n_estimators=240, min_samples_leaf=2, random_state=random_state, n_jobs=-1
    )
    return Pipeline([("prep",ct),("rf",rf)])

def cv_error(df, features, target, seed=37):
    data=df[features+[target]].dropna()
    if len(data)<20: return math.inf
    y=data[target].to_numpy()
    X=data[features]
    n_splits=min(5, max(2, len(data)//8))
    kf=KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    try:
        pred=cross_val_predict(build_model(X,features,seed), X, y, cv=kf, n_jobs=1)
        return median_ape(y,pred)
    except Exception:
        return math.inf

def rank_features(df, features, target):
    scores=[]
    for f in features:
        e=cv_error(df,[f],target)
        scores.append((e,f))
    scores.sort(key=lambda z:(z[0],z[1]))
    return [f for _,f in scores]

def select_min_interface(train, features, target):
    all_cv=cv_error(train,features,target)
    ranked=rank_features(train,features,target)[:8]
    threshold=max(all_cv*1.15, all_cv+0.03)
    best=None
    trials=[]
    for k in range(1,min(4,len(ranked))+1):
        for subset in itertools.combinations(ranked,k):
            e=cv_error(train,list(subset),target)
            trials.append({"features":list(subset),"cv_median_ape":e})
            if e<=threshold:
                cand=(k,e,list(subset))
                if best is None or cand[:2] < best[:2]:
                    best=cand
        if best is not None:
            break
    if best is None:
        best=(len(features),all_cv,list(features))
    return {
        "all_feature_cv_median_ape":all_cv,
        "selection_threshold":threshold,
        "ranked_features":ranked,
        "selected_features":best[2],
        "selected_cv_median_ape":best[1],
        "trials":sorted(trials,key=lambda x:x["cv_median_ape"])[:30],
    }

def eval_holdout(train, test, features, target, seed=37):
    tr=train[features+[target]].dropna()
    te=test[features+[target]].dropna()
    if len(tr)<10 or len(te)<2:
        return {"status":"UNKNOWN_INSUFFICIENT_ROWS","n_train":len(tr),"n_test":len(te)}
    model=build_model(tr,features,seed)
    model.fit(tr[features],tr[target])
    pred=model.predict(te[features])
    return {
        "status":"MEASURED",
        "n_train":len(tr),"n_test":len(te),
        "median_ape":median_ape(te[target].to_numpy(),pred),
        "median_abs_error":float(median_absolute_error(te[target].to_numpy(),pred)),
        "predictions":[
            {"actual":float(a),"pred":float(p)}
            for a,p in zip(te[target].to_numpy(),pred)
        ]
    }

def geometry_family_column(df):
    for c in df.columns:
        nc=normalize(c)
        if any(h in nc for h in ("family","preset","pattern","topology","design_type","geometry_type")):
            n=df[c].nunique(dropna=True)
            if 3<=n<=30:
                return c
    return None

def cross_family_test(train, features, target, family_col):
    if family_col is None:
        return {"status":"UNKNOWN_NO_FAMILY_COLUMN"}
    rows=[]
    for fam, grp in train.groupby(family_col):
        if len(grp)<3: continue
        rest=train[train[family_col]!=fam]
        if len(rest)<15: continue
        ev=eval_holdout(rest,grp,features,target,seed=41)
        rows.append({"family":str(fam),**ev})
    measured=[r for r in rows if r.get("status")=="MEASURED"]
    if not measured:
        return {"status":"UNKNOWN_INSUFFICIENT_FAMILY_ROWS","family_column":family_col,"rows":rows}
    return {
        "status":"MEASURED",
        "family_column":family_col,
        "median_family_mape":float(np.median([r["median_ape"] for r in measured])),
        "families":rows
    }

def theory_partition(df):
    # Discover explicit Euler/Timoshenko variants without inventing them.
    for c in df.columns:
        if df[c].dtype != object: continue
        vals=[str(v).lower() for v in df[c].dropna().unique()]
        has_e=any("euler" in v for v in vals)
        has_t=any("timoshenko" in v for v in vals)
        if has_e and has_t:
            e_vals=[v for v in df[c].dropna().unique() if "euler" in str(v).lower()]
            t_vals=[v for v in df[c].dropna().unique() if "timoshenko" in str(v).lower()]
            return c,e_vals,t_vals
    return None,None,None

def alternate_physics_test(df, features, target):
    c,e_vals,t_vals=theory_partition(df)
    if c is None:
        return {"status":"UNKNOWN_NO_EXPLICIT_EULER_TIMOSHENKO_ROWS"}
    e=df[df[c].isin(e_vals)]
    t=df[df[c].isin(t_vals)]
    # Avoid using the theory label as a feature when testing model-world transfer.
    f=[x for x in features if x!=c]
    ev=eval_holdout(e,t,f,target,seed=43)
    return {"status":ev.get("status"),"theory_column":c,"train_world":[str(x) for x in e_vals],
            "test_world":[str(x) for x in t_vals],"result":ev}

def sample_efficiency(train, test, selected, all_features, target):
    clean=train.dropna(subset=[target])
    sizes=sorted(set([8,12,16,24,32,48,64,96,len(clean)]))
    sizes=[n for n in sizes if 8<=n<=len(clean)]
    rows=[]
    for n in sizes:
        idx=np.random.default_rng(101+n).choice(len(clean),size=n,replace=False)
        sub=clean.iloc[idx]
        a=eval_holdout(sub,test,selected,target,seed=100+n)
        b=eval_holdout(sub,test,all_features,target,seed=200+n)
        rows.append({"n":n,"selected":a,"all_features":b})
    return rows

def separator_test(train,test,features,target):
    base=eval_holdout(train,test,features,target,seed=53)
    if base.get("status")!="MEASURED":
        return {"status":"UNKNOWN_BASELINE","baseline":base}
    tr=train[features+[target]].dropna()
    te=test[features+[target]].dropna().copy()
    model=build_model(tr,features,53).fit(tr[features],tr[target])
    y=te[target].to_numpy()
    base_err=median_ape(y, model.predict(te[features]))
    effects=[]
    for f in features:
        pert=te[features].copy()
        if pd.api.types.is_numeric_dtype(tr[f]):
            pert[f]=float(tr[f].median())
        else:
            mode=tr[f].mode(dropna=True)
            pert[f]=mode.iloc[0] if len(mode) else ""
        err=median_ape(y, model.predict(pert))
        effects.append({"feature":f,"ablated_median_ape":err,"delta":err-base_err})
    return {"status":"MEASURED","baseline_median_ape":base_err,
            "effects":sorted(effects,key=lambda x:x["delta"],reverse=True)}

def main():
    result={
        "schema":"mathgraph.crystal-buehler-physical-loop-v1",
        "epistemic_status":"CANDIDATE",
        "claim_boundary":"Archive replay against Buehler public computational fracture laboratory. Simulator agreement is not physical validation.",
        "exact_graphene_source_probe":probe_exact_graphene_source(),
        "proxy_source":{"repo":HF_REPO,"revision":HF_REV,"run":"Run 3"},
    }
    got,missing=load_proxy_sources()
    result["proxy_source"]["files"]=got
    result["proxy_source"]["missing"]=missing

    runs_b=read_saved(f"{RUN3}/data/processed/runs_table.csv")
    hold_b=read_saved(f"{RUN3}/data/processed/holdout_comparison.csv")
    pred_b=read_saved(f"{RUN3}/data/holdout_predictions.json")
    if runs_b is None:
        result["experiment_status"]="EXACT_RESIDUAL"
        result["residual"]="Pinned proxy archive did not expose expected runs_table.csv; no semantic claim promoted."
        (OUT/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0

    runs=pd.read_csv(pd.io.common.BytesIO(runs_b))
    hold=pd.read_csv(pd.io.common.BytesIO(hold_b)) if hold_b is not None else None
    pred_json=json.loads(pred_b) if pred_b is not None else None

    result["schema_probe"]={
        "runs_shape":list(runs.shape),
        "runs_columns":[str(c) for c in runs.columns],
        "holdout_shape":list(hold.shape) if hold is not None else None,
        "holdout_columns":[str(c) for c in hold.columns] if hold is not None else [],
    }

    idcol,hold_ids,idinfo=map_holdout_ids(runs,hold,pred_json)
    targets=protected_targets(runs)
    feats=candidate_features(runs,list(targets.values()),idcol)
    result["mapping"]={"id_column":idcol,"holdout_ids":sorted(hold_ids),"holdout_mapping":idinfo,
                       "targets":targets,"candidate_features":feats}

    if not idcol or len(hold_ids)<2 or not targets or len(feats)<1:
        result["experiment_status"]="EXACT_RESIDUAL"
        result["residual"]="Could not derive a leakage-resistant source-holdout mapping and protected target/interface from the archived processed schema."
        (OUT/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0

    is_hold=runs[idcol].astype(str).isin(hold_ids)
    train=runs.loc[~is_hold].copy()
    test=runs.loc[is_hold].copy()
    result["rows"]={"train":len(train),"source_holdout":len(test)}

    by_target={}
    for label,target in targets.items():
        sel=select_min_interface(train,feats,target)
        selected=sel["selected_features"]
        by_target[label]={
            "target_column":target,
            "selection":sel,
            "source_holdout_selected":eval_holdout(train,test,selected,target,seed=61),
            "source_holdout_all_features":eval_holdout(train,test,feats,target,seed=62),
            "separator_ablation":separator_test(train,test,selected,target),
            "geometry_family_transfer":cross_family_test(train,selected,target,geometry_family_column(train)),
            "alternate_physics_world":alternate_physics_test(runs,selected,target),
            "sample_efficiency_replay":sample_efficiency(train,test,selected,feats,target),
        }

    result["results"]=by_target
    # Promotion is intentionally narrow.
    measured=[v for v in by_target.values() if v["source_holdout_selected"].get("status")=="MEASURED"]
    result["experiment_status"]="QUALIFIED_BOUNDED_REPLAY" if measured else "EXACT_RESIDUAL"
    result["epistemic_status"]="WARRANTED_BOUNDED_REPLAY" if measured else "UNKNOWN"
    result["nonclaims"]=[
        "No claim of experimental graphene validation.",
        "No claim that the exact X-post graphene/REBO corpus was analyzed unless exact_graphene_source_probe says FOUND_CANDIDATE and is manually reconciled.",
        "No causal claim from predictive feature sufficiency alone.",
        "No universal transfer claim beyond the pinned archive and explicit alternate-world rows, if present."
    ]
    (OUT/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
