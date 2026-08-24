#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
V145 = HERE.parent / "trace_the_ace_v145"
sys.path.insert(0, str(V145))
from run_v145_semantic_gate import FIELDS, build_v75, choose_subset, compile_rows, grouped_bootstrap_improvement, resolve_transcripts
from v75_canonical_trajectory import SEED, load_training


def load_scores(path: Path) -> np.ndarray:
    rows=[]
    for line in path.read_text().splitlines():
        r=json.loads(line)
        rows.append([float(r[k]) for k in FIELDS])
    a=np.asarray(rows, dtype=float)
    if not np.isfinite(a).all(): raise ValueError(f"non-finite semantic scores in {path}")
    return a


def safe_logit(p):
    return logit(np.clip(p, 1e-5, 1-1e-5))


def diagnostics(p, S):
    p=np.clip(np.asarray(p), 1e-5, 1-1e-5)
    lp=safe_logit(p)
    ent=-(p*np.log(p)+(1-p)*np.log(1-p))
    base=np.column_stack([lp, np.abs(lp), p, ent])
    return np.column_stack([S, base, S*p[:,None], S*ent[:,None]])


def fit_base(X, y):
    return LogisticRegression(C=.25, max_iter=350, solver="liblinear", random_state=SEED).fit(X,y)


def inner_oof_base(X, y, groups, n_splits=4):
    gu=pd.Series(groups).astype(str)
    n=min(n_splits, gu.nunique())
    if n < 2: raise ValueError("need >=2 groups for inner cross-fitting")
    out=np.zeros(len(y))
    for tr,va in GroupKFold(n).split(np.zeros(len(y)), y, gu):
        m=fit_base(X[tr],y[tr]); out[va]=m.predict_proba(X[va])[:,1]
    return np.clip(out,1e-5,1-1e-5)


def choose_router(p_inner, y, Z_inner):
    # Newton-style logit residual target from strictly inner-OOF base predictions.
    target=np.clip((y-p_inner)/(p_inner*(1-p_inner)+1e-3), -4, 4)
    best=None
    for alpha in (1.0,10.0,100.0):
        r=Ridge(alpha=alpha).fit(Z_inner,target)
        d=r.predict(Z_inner)
        for lam in (0.10,0.25,0.50,0.75,1.0):
            for q in (0.0,0.50,0.70,0.85):
                thr=0.0 if q==0 else float(np.quantile(np.abs(d),q))
                gate=np.abs(d)>=thr
                p=expit(safe_logit(p_inner)+lam*d*gate)
                ll=float(log_loss(y,p))
                key=(ll, alpha, lam, q, thr, float(gate.mean()))
                if best is None or key[0] < best[0]: best=key
    _,alpha,lam,q,thr,cov=best
    model=Ridge(alpha=alpha).fit(Z_inner,target)
    return model,{"alpha":alpha,"lambda":lam,"quantile":q,"threshold":thr,"inner_coverage":cov}


def evaluate(name, X, S, y, groups):
    groups=np.asarray(pd.Series(groups).astype(str))
    splits=list(GroupKFold(5).split(np.zeros(len(y)),y,groups))
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]; cover=[]; params=[]
    for k,(tr,va) in enumerate(splits,1):
        scaler=StandardScaler().fit(S[tr]); Str=scaler.transform(S[tr]); Sva=scaler.transform(S[va])
        p_inner=inner_oof_base(X[tr],y[tr],groups[tr])
        Zin=diagnostics(p_inner,Str)
        router,par=choose_router(p_inner,y[tr],Zin)
        base=fit_base(X[tr],y[tr]); pb=base.predict_proba(X[va])[:,1]
        d=router.predict(diagnostics(pb,Sva)); gate=np.abs(d)>=par["threshold"]
        pr=expit(safe_logit(pb)+par["lambda"]*d*gate)
        p0[va]=pb; p1[va]=pr; cover.append(float(gate.mean())); params.append(par)
        folds.append({"fold":k,"rows":len(va),"base":float(log_loss(y[va],pb)),"routed":float(log_loss(y[va],pr)),"coverage":float(gate.mean())})
    p0=np.clip(p0,1e-5,1-1e-5); p1=np.clip(p1,1e-5,1-1e-5)
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {"base_logloss":ll0,"routed_logloss":ll1,"improvement":ll0-ll1,
            "base_auc":float(roc_auc_score(y,p0)),"routed_auc":float(roc_auc_score(y,p1)),
            "bootstrap_improvement_95":grouped_bootstrap_improvement(y,p0,p1,groups),
            "fold_wins":int(sum(f["routed"]<f["base"] for f in folds)),"mean_coverage":float(np.mean(cover)),
            "folds":folds,"router_params":params}


def self_test():
    rng=np.random.default_rng(3); n=120
    S=rng.normal(size=(n,7)); p=np.clip(rng.uniform(.05,.95,n),1e-5,1-1e-5)
    Z=diagnostics(p,S)
    assert Z.shape==(n,25)
    print("V146_SELF_TEST_PASS")


def main(a):
    if a.self_test: self_test(); return
    work=a.v145_work.resolve(); out=a.out.resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    frame=choose_subset(load_training(a.features,a.labels),a.limit)
    transcripts=resolve_transcripts(a.transcripts.resolve(), out.parent/"compile_work")
    views,numeric,_=compile_rows(frame,transcripts)
    X=build_v75(frame,views,numeric); y=frame.target.to_numpy(int)
    S=load_scores(work/"semantic_scores.jsonl")
    if len(S)!=len(frame): raise ValueError(f"semantic row mismatch: {len(S)} vs {len(frame)}")
    objective_groups=frame.learning_objective_id if "learning_objective_id" in frame else frame.learning_objective
    rng=np.random.default_rng(SEED)
    shuffled=S[rng.permutation(len(S))]
    results={"protocol":"V146_CROSSFITTED_SEMANTIC_RESIDUAL_ROUTER","rows":len(frame),"fields":FIELDS,
             "session":evaluate("session",X,S,y,frame.session_id),
             "objective":evaluate("objective",X,S,y,objective_groups),
             "shuffled":{"session":evaluate("session_shuffled",X,shuffled,y,frame.session_id),
                         "objective":evaluate("objective_shuffled",X,shuffled,y,objective_groups)}}
    # Reproduce V145's fixed 2,500-row counterfactual subset and run the identical residual router on it.
    ci=np.sort(rng.choice(len(frame),size=min(a.control_limit,len(frame)),replace=False))
    ctr={}
    for label,fn in (("objective_swap","objective_swap_scores.jsonl"),("evidence_empty","evidence_empty_scores.jsonl")):
        Sc=load_scores(work/fn)
        if len(Sc)!=len(ci): raise ValueError(f"control row mismatch {label}: {len(Sc)} vs {len(ci)}")
        ctr[label]={
          "session":evaluate(label+"_session",X[ci],Sc,y[ci],np.asarray(frame.session_id)[ci]),
          "objective":evaluate(label+"_objective",X[ci],Sc,y[ci],np.asarray(objective_groups)[ci])}
    results["counterfactual_controls"]=ctr
    s,o=results["session"],results["objective"]
    ss,so=results["shuffled"]["session"],results["shuffled"]["objective"]
    controls_ok=True
    for split in ("session","objective"):
        main_imp=results[split]["improvement"]
        controls_ok &= all(main_imp > results["counterfactual_controls"][c][split]["improvement"] for c in ("objective_swap","evidence_empty"))
    promote=(o["improvement"]>=.001 and s["improvement"]>=.0002 and o["fold_wins"]>=4 and s["fold_wins"]>=3
             and o["bootstrap_improvement_95"][0]>0 and s["bootstrap_improvement_95"][0]>=0
             and o["improvement"]>so["improvement"]+.0005 and s["improvement"]>ss["improvement"]+.0002 and controls_ok)
    results["decision"]="PROMOTE_TO_SUBMISSION_CANDIDATE" if promote else "DO_NOT_SPEND_SUBMISSION"
    out.write_text(json.dumps(results,indent=2)); print(json.dumps(results,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--features",type=Path); p.add_argument("--labels",type=Path); p.add_argument("--transcripts",type=Path)
    p.add_argument("--v145-work",type=Path); p.add_argument("--out",type=Path,default=Path("v146_results.json")); p.add_argument("--limit",type=int,default=8000)
    p.add_argument("--control-limit",type=int,default=2500); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if not a.self_test and not all((a.features,a.labels,a.transcripts,a.v145_work)): p.error("features, labels, transcripts and v145-work are required")
    main(a)
