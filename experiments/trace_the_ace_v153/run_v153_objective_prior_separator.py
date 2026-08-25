#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
import numpy as np
from scipy.special import expit, logit
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

SEED = 20260826

def slogit(p):
    return logit(np.clip(np.asarray(p), 1e-5, 1-1e-5))

def load_bundle(path: Path):
    b=np.load(path,allow_pickle=True)
    return dict(
        y=b['y'].astype(int), session=b['session_id'].astype(str),
        objective=b['objective_group'].astype(str), numeric=b['numeric'].astype(float)
    )

def fit_numeric(X,y):
    sc=StandardScaler().fit(X)
    m=LogisticRegression(C=.25,max_iter=300,solver='liblinear',random_state=SEED).fit(sc.transform(X),y)
    return sc,m

def pred_numeric(model,X):
    sc,m=model
    return np.clip(m.predict_proba(sc.transform(X))[:,1],1e-5,1-1e-5)

def objective_prior(train_obj, train_y, val_obj, alpha):
    mu=(train_y.sum()+1.0)/(len(train_y)+2.0)
    sums={}; counts={}
    for o,y in zip(train_obj,train_y):
        sums[o]=sums.get(o,0.0)+float(y); counts[o]=counts.get(o,0)+1
    out=np.empty(len(val_obj),float)
    for i,o in enumerate(val_obj):
        n=counts.get(o,0); s=sums.get(o,0.0)
        out[i]=(s+alpha*mu)/(n+alpha) if n else mu
    return np.clip(out,1e-5,1-1e-5)

def eval_split(y,num,obj,groups):
    folds=[]; pnum=np.zeros(len(y)); pbest=np.zeros(len(y)); pprior=np.zeros(len(y))
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        nm=fit_numeric(num[tr],y[tr]); pn=pred_numeric(nm,num[va]); pnum[va]=pn
        # Choose shrinkage and blend strictly on inner grouped OOF.
        inner=np.zeros(len(tr)); pobj=np.zeros(len(tr)); gtr=np.asarray(groups)[tr]
        inner_splits=list(GroupKFold(min(4,len(np.unique(gtr)))).split(np.zeros(len(tr)),y[tr],gtr))
        for itr,iva in inner_splits:
            nmi=fit_numeric(num[tr][itr],y[tr][itr]); inner[iva]=pred_numeric(nmi,num[tr][iva])
        best=None
        for a in (2.,5.,10.,20.,50.,100.):
            pp=np.zeros(len(tr))
            for itr,iva in inner_splits:
                pp[iva]=objective_prior(obj[tr][itr],y[tr][itr],obj[tr][iva],a)
            for w in (0.,.1,.2,.35,.5,.65,.8,1.0):
                pb=expit((1-w)*slogit(inner)+w*slogit(pp))
                ll=log_loss(y[tr],pb)
                if best is None or ll<best[0]: best=(ll,a,w)
        _,a,w=best
        pp=objective_prior(obj[tr],y[tr],obj[va],a); pprior[va]=pp
        pb=expit((1-w)*slogit(pn)+w*slogit(pp)); pbest[va]=pb
        folds.append(dict(fold=k,alpha=a,weight=w,base=float(log_loss(y[va],pn)),blend=float(log_loss(y[va],pb)),prior=float(log_loss(y[va],pp)),win=bool(log_loss(y[va],pb)<log_loss(y[va],pn))))
    def metrics(p): return dict(logloss=float(log_loss(y,p)),auc=float(roc_auc_score(y,p)))
    mb,mm,mp=metrics(pnum),metrics(pbest),metrics(pprior)
    return dict(base=mb,blend=mm,prior=mp,improvement=mb['logloss']-mm['logloss'],fold_wins=sum(f['win'] for f in folds),folds=folds)

def main(a):
    b=load_bundle(a.bundle); y=b['y']; obj=b['objective']; num=b['numeric']; sess=b['session']
    rng=np.random.default_rng(SEED); sh=obj[rng.permutation(len(obj))]
    session=eval_split(y,num,obj,sess)
    objective=eval_split(y,num,obj,obj)
    shuffled=eval_split(y,num,sh,sess)
    # For competition-like deployment, new sessions but recurring objectives is the useful regime.
    gain=session['improvement']; sep=gain-shuffled['improvement']
    if gain>=.003 and session['fold_wins']>=4 and sep>=.0015:
        decision='BIG_OBJECTIVE_PRIOR_GAIN'
    elif gain>=.0015 and session['fold_wins']>=3 and sep>=.00075:
        decision='OBJECTIVE_PRIOR_SEPARATOR_FOUND'
    else:
        decision='NO_BIG_OBJECTIVE_PRIOR_GAIN'
    out=dict(protocol='V153_OBJECTIVE_PRIOR_SEPARATOR',warning='TRIAGE_ONLY_NOT_SUBMISSION_EVIDENCE',rows=len(y),
             residual='Semantic branch revoked. Test whether recurring learning-objective base rates are the missing low-dimensional competition-specific calibration signal.',
             session=session,objective_cold=objective,shuffled_objective_control=shuffled,decision=decision)
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v153_results.json')); main(p.parse_args())
