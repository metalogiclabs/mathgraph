#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
V150 = HERE.parent / 'trace_the_ace_v150'
sys.path.insert(0, str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base

SEED=1729
EPS=1e-5

def slogit(p): return logit(np.clip(np.asarray(p),EPS,1-EPS))

def bentropy(p):
    p=np.clip(np.asarray(p),EPS,1-EPS)
    return -(p*np.log(p)+(1-p)*np.log(1-p))

def base_cache(num,obj,y,groups):
    groups=np.asarray(groups).astype(str); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        inner=np.zeros(len(tr)); g=groups[tr]; n=min(4,len(np.unique(g)))
        for itr,iva in GroupKFold(n).split(np.zeros(len(tr)),y[tr],g):
            m=fit_base(num[tr][itr],obj[tr][itr],y[tr][itr]); inner[iva]=predict_base(m,num[tr][iva],obj[tr][iva])
        m=fit_base(num[tr],obj[tr],y[tr]); pb=predict_base(m,num[va],obj[va])
        folds.append((k,tr,va,inner,pb))
    return folds

def feats(p,e,kind):
    p=np.clip(p,EPS,1-EPS); l=slogit(p); h=bentropy(p); e=np.asarray(e,float)
    if kind=='additive': return np.c_[l,e]
    if kind=='confidence': return np.c_[l,l*e]
    if kind=='uncertainty': return np.c_[l,e,h*e]
    if kind=='symmetric': return np.c_[l,e,l*e,np.abs(l)*e,h*e]
    raise ValueError(kind)

def fit_cal(p,e,y,kind,C):
    X=feats(p,e,kind); sc=StandardScaler().fit(X); Xs=sc.transform(X)
    m=LogisticRegression(C=C,max_iter=400,solver='liblinear',random_state=SEED).fit(Xs,y)
    return sc,m

def pred_cal(model,p,e,kind):
    sc,m=model; return np.clip(m.predict_proba(sc.transform(feats(p,e,kind)))[:,1],EPS,1-EPS)

def choose_on_inner(p,e,y):
    best=None
    for direction in ('raw','invert'):
        ee=e if direction=='raw' else 1-e
        for kind in ('additive','confidence','uncertainty','symmetric'):
            for C in (.01,.03,.1,.3,1.0):
                m=fit_cal(p,ee,y,kind,C); pr=pred_cal(m,p,ee,kind); ll=float(log_loss(y,pr))
                key=(ll,kind,C,direction,m)
                if best is None or ll<best[0]: best=key
    return best[1],best[2],best[3],best[4]

def eval_shape(e,y,folds):
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); rows=[]; choices=[]
    for k,tr,va,inner,pb in folds:
        kind,C,direction,m=choose_on_inner(inner,e[tr],y[tr]); ev=e[va] if direction=='raw' else 1-e[va]
        pr=pred_cal(m,pb,ev,kind); p0[va]=pb; p1[va]=pr
        rows.append({'fold':k,'base':float(log_loss(y[va],pb)),'shaped':float(log_loss(y[va],pr)),'win':bool(log_loss(y[va],pr)<log_loss(y[va],pb))})
        choices.append({'fold':k,'kind':kind,'C':C,'direction':direction})
    l0=float(log_loss(y,p0)); l1=float(log_loss(y,p1))
    return {'base_logloss':l0,'shaped_logloss':l1,'improvement':l0-l1,'base_auc':float(roc_auc_score(y,p0)),'shaped_auc':float(roc_auc_score(y,p1)),'fold_wins':int(sum(r['win'] for r in rows)),'choices':choices,'folds':rows}

def eval_threshold_family(e,y,folds):
    # Explicitly test the hypothesis that sufficiency should control *magnitude* of confidence.
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); rows=[]; choices=[]
    for k,tr,va,inner,pb in folds:
        best=None; li=slogit(inner)
        for direction in ('high','low'):
          for q in (.2,.35,.5,.65,.8):
            thr=float(np.quantile(e[tr],q)); gate=(e[tr]>=thr) if direction=='high' else (e[tr]<=thr)
            for beta in (-.30,-.20,-.10,-.05,.05,.10,.20,.30):
                pr=expit(li*(1+beta*gate.astype(float))); ll=float(log_loss(y[tr],pr))
                if best is None or ll<best[0]: best=(ll,direction,q,thr,beta)
        _,direction,q,thr,beta=best; gate=(e[va]>=thr) if direction=='high' else (e[va]<=thr)
        pr=np.clip(expit(slogit(pb)*(1+beta*gate.astype(float))),EPS,1-EPS); p0[va]=pb; p1[va]=pr
        rows.append({'fold':k,'base':float(log_loss(y[va],pb)),'shaped':float(log_loss(y[va],pr)),'coverage':float(gate.mean()),'win':bool(log_loss(y[va],pr)<log_loss(y[va],pb))})
        choices.append({'fold':k,'direction':direction,'quantile':q,'threshold':thr,'beta':beta})
    l0=float(log_loss(y,p0)); l1=float(log_loss(y,p1))
    return {'base_logloss':l0,'shaped_logloss':l1,'improvement':l0-l1,'base_auc':float(roc_auc_score(y,p0)),'shaped_auc':float(roc_auc_score(y,p1)),'fold_wins':int(sum(r['win'] for r in rows)),'choices':choices,'folds':rows}

def main(a):
    b=load_bundle(a.bundle.resolve()); ci=b['ci']; y=b['y'][ci]; num=b['numeric'][ci]; obj=b['objective'][ci]
    real=b['S'][ci]; empty=b['Sempty']; e=real[:,6]; de=real[:,6]-empty[:,6]
    rng=np.random.default_rng(SEED); shuffled=e[rng.permutation(len(e))]
    caches={'session':base_cache(num,obj,y,b['session'][ci]),'objective':base_cache(num,obj,y,b['objective'][ci])}
    variants={'evidence_sufficiency':e,'evidence_delta':de,'shuffled_sufficiency':shuffled}
    out={'protocol':'V152_EVIDENCE_SUFFICIENCY_SHAPE_AUDIT','warning':'FOLLOWUP_ON_V151_DISCOVERY; NOT INDEPENDENT SUBMISSION EVIDENCE','rows':len(y),'residual':'V151 isolated evidence_sufficiency. Test whether its useful role is additive calibration or confidence-magnitude control.'}
    out['flexible']={}; out['threshold_confidence']={}
    for name,x in variants.items():
        out['flexible'][name]={s:eval_shape(x,y,caches[s]) for s in ('session','objective')}
        out['threshold_confidence'][name]={s:eval_threshold_family(x,y,caches[s]) for s in ('session','objective')}
    candidates=[]
    for family in ('flexible','threshold_confidence'):
      for name in ('evidence_sufficiency','evidence_delta'):
        r=out[family][name]; candidates.append((r['objective']['improvement']+0.5*r['session']['improvement'],family,name,r))
    candidates.sort(reverse=True,key=lambda z:z[0]); _,fam,name,best=candidates[0]
    ctrl=out[fam]['shuffled_sufficiency']
    robust=(best['objective']['improvement']>=.0025 and best['session']['improvement']>=.0008 and best['objective']['fold_wins']>=4 and best['session']['fold_wins']>=3 and best['objective']['improvement']>ctrl['objective']['improvement']+.001 and best['session']['improvement']>ctrl['session']['improvement']+.0005)
    out['best_family']=fam; out['best_signal']=name; out['best']=best; out['decision']='SHAPE_SEPARATOR_CONFIRMED' if robust else 'SHAPE_NOT_CONFIRMED'
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps({'decision':out['decision'],'best_family':fam,'best_signal':name,'best':best,'shuffle_control':ctrl},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v152_results.json')); main(p.parse_args())
