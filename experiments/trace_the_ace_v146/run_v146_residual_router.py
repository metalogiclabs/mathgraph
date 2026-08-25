#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time
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
from run_v145_semantic_gate import FIELDS, build_v75, grouped_bootstrap_improvement
from v75_canonical_trajectory import SEED


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


def prepare_base_cache(name, X, y, groups):
    """Compute the expensive base cross-fits once for a frozen split.

    This is a pure computational refactor of the original V146 protocol: the
    GroupKFold partitions, base estimator, inner OOF predictions and held-out
    base predictions are identical. Semantic/control views reuse these frozen
    quantities rather than refitting the same base models repeatedly.
    """
    t0=time.time()
    groups=np.asarray(pd.Series(groups).astype(str))
    splits=list(GroupKFold(5).split(np.zeros(len(y)),y,groups))
    folds=[]
    for k,(tr,va) in enumerate(splits,1):
        p_inner=inner_oof_base(X[tr],y[tr],groups[tr])
        base=fit_base(X[tr],y[tr])
        pb=np.clip(base.predict_proba(X[va])[:,1],1e-5,1-1e-5)
        folds.append({"fold":k,"tr":tr,"va":va,"p_inner":p_inner,"pb":pb})
        print(f"BASE_CACHE {name} fold {k}/5", flush=True)
    print(f"BASE_CACHE_DONE {name} seconds={time.time()-t0:.1f}", flush=True)
    return {"groups":groups,"folds":folds}


def evaluate_cached(name, S, y, cache):
    groups=cache["groups"]
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]; cover=[]; params=[]
    for item in cache["folds"]:
        k,tr,va=item["fold"],item["tr"],item["va"]
        scaler=StandardScaler().fit(S[tr]); Str=scaler.transform(S[tr]); Sva=scaler.transform(S[va])
        p_inner=item["p_inner"]
        Zin=diagnostics(p_inner,Str)
        router,par=choose_router(p_inner,y[tr],Zin)
        pb=item["pb"]
        d=router.predict(diagnostics(pb,Sva)); gate=np.abs(d)>=par["threshold"]
        pr=expit(safe_logit(pb)+par["lambda"]*d*gate)
        p0[va]=pb; p1[va]=pr; cover.append(float(gate.mean())); params.append(par)
        folds.append({"fold":k,"rows":len(va),"base":float(log_loss(y[va],pb)),"routed":float(log_loss(y[va],pr)),"coverage":float(gate.mean())})
        print(f"ROUTER {name} fold {k}/5", flush=True)
    p0=np.clip(p0,1e-5,1-1e-5); p1=np.clip(p1,1e-5,1-1e-5)
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {"base_logloss":ll0,"routed_logloss":ll1,"improvement":ll0-ll1,
            "base_auc":float(roc_auc_score(y,p0)),"routed_auc":float(roc_auc_score(y,p1)),
            "bootstrap_improvement_95":grouped_bootstrap_improvement(y,p0,p1,groups),
            "fold_wins":int(sum(f["routed"]<f["base"] for f in folds)),"mean_coverage":float(np.mean(cover)),
            "folds":folds,"router_params":params}


def load_bundle(path: Path):
    b=np.load(path,allow_pickle=True)
    frame=pd.DataFrame({"learning_objective":b["objective"].astype(str)})
    views=[]
    n=len(frame)
    for i in range(n):
        views.append({k:b[f"view_{k}"][i].item() if hasattr(b[f"view_{k}"][i],"item") else str(b[f"view_{k}"][i]) for k in ("raw","student","local","canonical","terminal")})
    X=build_v75(frame,views,b["numeric"])
    return X,b["semantic"].astype(float),b["y"].astype(int),b["session_id"].astype(str),b["objective_group"].astype(str),b["control_index"].astype(int),b["objective_swap"].astype(float),b["evidence_empty"].astype(float)


def self_test():
    rng=np.random.default_rng(3); n=120
    S=rng.normal(size=(n,7)); p=np.clip(rng.uniform(.05,.95,n),1e-5,1-1e-5)
    Z=diagnostics(p,S)
    assert Z.shape==(n,25)
    print("V146_SELF_TEST_PASS")


def main(a):
    if a.self_test: self_test(); return
    out=a.out.resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    X,S,y,session_groups,objective_groups,ci,Sswap,Sempty=load_bundle(a.bundle.resolve())
    rng=np.random.default_rng(SEED)
    shuffled=S[rng.permutation(len(S))]

    # Full-data caches are shared by main and shuffled semantic views.
    full_session=prepare_base_cache("full_session",X,y,session_groups)
    full_objective=prepare_base_cache("full_objective",X,y,objective_groups)
    results={"protocol":"V146_CROSSFITTED_SEMANTIC_RESIDUAL_ROUTER","implementation":"CACHED_BASE_CROSSFITS_EQUIVALENT",
             "rows":len(y),"fields":FIELDS,
             "session":evaluate_cached("session",S,y,full_session),
             "objective":evaluate_cached("objective",S,y,full_objective),
             "shuffled":{"session":evaluate_cached("session_shuffled",shuffled,y,full_session),
                         "objective":evaluate_cached("objective_shuffled",shuffled,y,full_objective)}}

    # Both counterfactual semantic views use the same 2,500-row base subset, so
    # cache those base cross-fits once as well.
    Xc,yc=X[ci],y[ci]
    c_session=prepare_base_cache("control_session",Xc,yc,session_groups[ci])
    c_objective=prepare_base_cache("control_objective",Xc,yc,objective_groups[ci])
    ctr={}
    for label,Sc in (("objective_swap",Sswap),("evidence_empty",Sempty)):
        ctr[label]={
          "session":evaluate_cached(label+"_session",Sc,yc,c_session),
          "objective":evaluate_cached(label+"_objective",Sc,yc,c_objective)}
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
    p=argparse.ArgumentParser(); p.add_argument("--bundle",type=Path); p.add_argument("--out",type=Path,default=Path("v146_results.json")); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if not a.self_test and not a.bundle: p.error("--bundle is required")
    main(a)
