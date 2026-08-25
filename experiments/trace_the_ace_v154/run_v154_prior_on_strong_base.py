#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE=Path(__file__).resolve().parent
V150=HERE.parent/'trace_the_ace_v150'
sys.path.insert(0,str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base, safe_logit

SEED=20260826

def objective_prior(train_obj, train_y, val_obj, alpha):
    mu=(float(train_y.sum())+1.0)/(len(train_y)+2.0)
    sums={}; counts={}
    for o,y in zip(train_obj,train_y):
        sums[o]=sums.get(o,0.0)+float(y); counts[o]=counts.get(o,0)+1
    out=np.empty(len(val_obj),float)
    for i,o in enumerate(val_obj):
        n=counts.get(o,0); s=sums.get(o,0.0)
        out[i]=(s+alpha*mu)/(n+alpha) if n else mu
    return np.clip(out,1e-5,1-1e-5)

def eval_split(y,num,obj,groups,prior_obj):
    groups=np.asarray(groups).astype(str)
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); ppall=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        gtr=groups[tr]
        inner_splits=list(GroupKFold(min(4,len(np.unique(gtr)))).split(np.zeros(len(tr)),y[tr],gtr))
        inner=np.zeros(len(tr))
        for itr,iva in inner_splits:
            bm=fit_base(num[tr][itr],obj[tr][itr],y[tr][itr])
            inner[iva]=predict_base(bm,num[tr][iva],obj[tr][iva])
        best=None
        for alpha in (2.,5.,10.,20.,50.,100.,250.):
            ipp=np.zeros(len(tr))
            for itr,iva in inner_splits:
                ipp[iva]=objective_prior(prior_obj[tr][itr],y[tr][itr],prior_obj[tr][iva],alpha)
            for w in (0.,.025,.05,.1,.15,.2,.3,.4,.5):
                pb=expit((1-w)*safe_logit(inner)+w*safe_logit(ipp))
                ll=float(log_loss(y[tr],pb))
                if best is None or ll<best[0]: best=(ll,alpha,w)
        _,alpha,w=best
        bm=fit_base(num[tr],obj[tr],y[tr]); pb=predict_base(bm,num[va],obj[va])
        pp=objective_prior(prior_obj[tr],y[tr],prior_obj[va],alpha)
        pr=expit((1-w)*safe_logit(pb)+w*safe_logit(pp))
        p0[va]=pb; p1[va]=pr; ppall[va]=pp
        folds.append({'fold':k,'alpha':alpha,'weight':w,'base':float(log_loss(y[va],pb)),'blend':float(log_loss(y[va],pr)),'win':bool(log_loss(y[va],pr)<log_loss(y[va],pb))})
    def m(p): return {'logloss':float(log_loss(y,p)),'auc':float(roc_auc_score(y,p))}
    a,b,c=m(p0),m(p1),m(ppall)
    return {'base':a,'blend':b,'prior':c,'improvement':a['logloss']-b['logloss'],'fold_wins':int(sum(f['win'] for f in folds)),'folds':folds}

def main(a):
    b=load_bundle(a.bundle.resolve()); y=b['y']; num=b['numeric']; obj=b['objective']; sess=b['session']
    rng=np.random.default_rng(SEED); sh=obj[rng.permutation(len(obj))]
    session=eval_split(y,num,obj,sess,obj)
    shuffled=eval_split(y,num,obj,sess,sh)
    objective=eval_split(y,num,obj,obj,obj)
    sep=session['improvement']-shuffled['improvement']
    if session['improvement']>=.003 and session['fold_wins']>=4 and sep>=.0015:
        decision='BIG_GAIN_SURVIVES_STRONG_BASE'
    elif session['improvement']>=.001 and session['fold_wins']>=3 and sep>=.0005:
        decision='INCREMENTAL_PRIOR_GAIN_CONFIRMED'
    else:
        decision='V153_GAIN_ABSORBED_BY_STRONG_BASE'
    out={'protocol':'V154_OBJECTIVE_PRIOR_ON_STRONG_LOW_DIMENSIONAL_BASE','warning':'TRIAGE_ONLY_NOT_SUBMISSION_EVIDENCE','rows':len(y),
         'residual':'V153 showed +0.0403 versus numeric-only base. Test whether objective prior adds value beyond the stronger objective-onehot + numeric base already used in V150.',
         'session':session,'objective_cold':objective,'shuffled_objective_control':shuffled,'separator':sep,'decision':decision}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v154_results.json')); main(p.parse_args())
