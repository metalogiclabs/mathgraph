#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

HERE=Path(__file__).resolve().parent
V146=HERE.parent/"trace_the_ace_v146"
sys.path.insert(0,str(V146))
from run_v146_residual_router import load_bundle, fit_base, inner_oof_base, safe_logit
V145=HERE.parent/"trace_the_ace_v145"
sys.path.insert(0,str(V145))
from run_v145_semantic_gate import FIELDS, grouped_bootstrap_improvement
from v75_canonical_trajectory import SEED


def features(p,S):
    p=np.clip(np.asarray(p),1e-5,1-1e-5)
    lp=safe_logit(p)
    ent=-(p*np.log(p)+(1-p)*np.log(1-p))
    return np.column_stack([S,lp,np.abs(lp),p,ent,S*p[:,None],S*ent[:,None]])


def prepare_cache(name,X,y,groups):
    groups=np.asarray(pd.Series(groups).astype(str))
    folds=[]; t0=time.time()
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        p_inner=inner_oof_base(X[tr],y[tr],groups[tr])
        base=fit_base(X[tr],y[tr])
        pb=np.clip(base.predict_proba(X[va])[:,1],1e-5,1-1e-5)
        folds.append((k,tr,va,p_inner,pb))
        print(f"BASE_CACHE {name} fold {k}/5",flush=True)
    print(f"BASE_CACHE_DONE {name} seconds={time.time()-t0:.1f}",flush=True)
    return groups,folds


def make_actions(y,p,deadzone):
    # Comparative target: only intervene when the realized miss is large enough.
    # 0=DOWN, 1=KEEP, 2=UP.
    r=y-p
    a=np.ones(len(y),dtype=int)
    a[r < -deadzone]=0
    a[r > deadzone]=2
    return a


def choose_policy(p_inner,y,Z):
    best=None
    for dead in (0.15,0.25,0.35):
        a=make_actions(y,p_inner,dead)
        if np.unique(a).size<2: continue
        for C in (0.05,0.2,1.0):
            clf=LogisticRegression(C=C,max_iter=300,solver="lbfgs",random_state=SEED).fit(Z,a)
            pred=clf.predict(Z)
            for delta in (0.10,0.20,0.35,0.50):
                shift=np.where(pred==0,-delta,np.where(pred==2,delta,0.0))
                pp=expit(safe_logit(p_inner)+shift)
                ll=float(log_loss(y,pp))
                key=(ll,dead,C,delta)
                if best is None or ll<best[0]: best=key
    if best is None: raise RuntimeError("no comparative policy candidate")
    _,dead,C,delta=best
    a=make_actions(y,p_inner,dead)
    clf=LogisticRegression(C=C,max_iter=300,solver="lbfgs",random_state=SEED).fit(Z,a)
    return clf,{"deadzone":dead,"C":C,"delta":delta}


def evaluate(name,S,y,cache):
    groups,foldcache=cache
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]; action_counts=np.zeros(3,dtype=int)
    for k,tr,va,p_inner,pb in foldcache:
        sc=StandardScaler().fit(S[tr]); Str=sc.transform(S[tr]); Sva=sc.transform(S[va])
        clf,par=choose_policy(p_inner,y[tr],features(p_inner,Str))
        act=clf.predict(features(pb,Sva)); action_counts += np.bincount(act,minlength=3)
        shift=np.where(act==0,-par["delta"],np.where(act==2,par["delta"],0.0))
        pr=expit(safe_logit(pb)+shift)
        p0[va]=pb; p1[va]=pr
        folds.append({"fold":k,"base":float(log_loss(y[va],pb)),"comparative":float(log_loss(y[va],pr)),"params":par,
                      "actions":{"down":int((act==0).sum()),"keep":int((act==1).sum()),"up":int((act==2).sum())}})
        print(f"COMPARATIVE {name} fold {k}/5",flush=True)
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {"base_logloss":ll0,"comparative_logloss":ll1,"improvement":ll0-ll1,
            "base_auc":float(roc_auc_score(y,p0)),"comparative_auc":float(roc_auc_score(y,p1)),
            "bootstrap_improvement_95":grouped_bootstrap_improvement(y,p0,p1,groups),
            "fold_wins":int(sum(f["comparative"]<f["base"] for f in folds)),
            "actions":{"down":int(action_counts[0]),"keep":int(action_counts[1]),"up":int(action_counts[2])},"folds":folds}


def self_test():
    rng=np.random.default_rng(7); n=100
    S=rng.normal(size=(n,7)); p=rng.uniform(.1,.9,n)
    assert features(p,S).shape==(n,25)
    a=make_actions((rng.random(n)>.5).astype(int),p,.25)
    assert set(np.unique(a)).issubset({0,1,2})
    print("V147_SELF_TEST_PASS")


def main(a):
    if a.self_test: self_test(); return
    X,S,y,sg,og,ci,Sswap,Sempty=load_bundle(a.bundle.resolve())
    rng=np.random.default_rng(SEED); shuffled=S[rng.permutation(len(S))]
    fs=prepare_cache("full_session",X,y,sg); fo=prepare_cache("full_objective",X,y,og)
    out={"protocol":"V147_COMPARATIVE_DOWN_KEEP_UP_ROUTER","rows":len(y),"fields":FIELDS,
         "session":evaluate("session",S,y,fs),"objective":evaluate("objective",S,y,fo),
         "shuffled":{"session":evaluate("session_shuffled",shuffled,y,fs),"objective":evaluate("objective_shuffled",shuffled,y,fo)}}
    Xc,yc=X[ci],y[ci]
    cs=prepare_cache("control_session",Xc,yc,sg[ci]); co=prepare_cache("control_objective",Xc,yc,og[ci])
    out["counterfactual_controls"]={}
    for name,Sc in (("objective_swap",Sswap),("evidence_empty",Sempty)):
        out["counterfactual_controls"][name]={"session":evaluate(name+"_session",Sc,yc,cs),"objective":evaluate(name+"_objective",Sc,yc,co)}
    s,o=out["session"],out["objective"]
    signal=(o["improvement"]>out["shuffled"]["objective"]["improvement"] and s["improvement"]>out["shuffled"]["session"]["improvement"])
    robust=(o["improvement"]>0 and s["improvement"]>0 and o["fold_wins"]>=4 and s["fold_wins"]>=3 and signal)
    out["decision"]="COMPARATIVE_SIGNAL" if robust else "NO_COMPARATIVE_SIGNAL"
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--bundle",type=Path); p.add_argument("--out",type=Path,default=Path("v147_results.json")); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if not a.self_test and not a.bundle: p.error("--bundle required")
    main(a)
