#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

HERE=Path(__file__).resolve().parent
V150=HERE.parent/'trace_the_ace_v150'
sys.path.insert(0,str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base, safe_logit

SEED=20260826
EPS=1e-5


def fit_shrunk_obj_cal(obj, y, p, alpha, slope_alpha):
    """Empirical-Bayes-like objective intercept + slope correction.

    Correction is fit to Newton pseudo-residuals around the already-strong base,
    with independent shrinkage of objective intercept and objective x confidence slope.
    No validation labels are used.
    """
    obj=np.asarray(obj).astype(str); y=np.asarray(y,float); p=np.clip(np.asarray(p,float),EPS,1-EPS)
    z=safe_logit(p); r=(y-p)/(p*(1-p)+1e-3)
    keys=np.unique(obj); table={}
    zc=z-z.mean(); zv=float(np.mean(zc*zc))+1e-6
    for o in keys:
        m=obj==o; n=int(m.sum())
        if n==0: continue
        # intercept residual, shrunk by pseudo-count alpha
        a=float(r[m].sum()/(n+alpha))
        # local residual-vs-confidence slope, shrunk toward zero
        zz=zc[m]; rr=r[m]-a
        den=float(np.dot(zz,zz)+slope_alpha*zv)
        b=float(np.dot(zz,rr)/den) if den>0 else 0.0
        table[o]=(a,b,n)
    return table,float(z.mean())


def pred_shrunk(table,zmean,obj,p,scale):
    obj=np.asarray(obj).astype(str); p=np.clip(np.asarray(p,float),EPS,1-EPS); z=safe_logit(p)
    d=np.zeros(len(p),float)
    for i,o in enumerate(obj):
        a,b,_=table.get(o,(0.0,0.0,0)); d[i]=a+b*(z[i]-zmean)
    return np.clip(expit(z+scale*np.clip(d,-2.5,2.5)),EPS,1-EPS)


def inner_oof_base(num,obj,y,groups):
    groups=np.asarray(groups).astype(str); out=np.zeros(len(y))
    n=min(4,len(np.unique(groups)))
    for tr,va in GroupKFold(n).split(np.zeros(len(y)),y,groups):
        m=fit_base(num[tr],obj[tr],y[tr]); out[va]=predict_base(m,num[va],obj[va])
    return out


def choose_params(obj,y,p):
    best=None
    for alpha in (2.,5.,10.,20.,50.,100.,250.):
      for sa in (5.,20.,50.,100.,250.):
        t,zm=fit_shrunk_obj_cal(obj,y,p,alpha,sa)
        for scale in (.15,.25,.4,.6,.8,1.0):
          pr=pred_shrunk(t,zm,obj,p,scale)
          ll=float(log_loss(y,pr))
          if best is None or ll<best[0]: best=(ll,alpha,sa,scale)
    return best[1:]


def evaluate(y,num,obj,groups,cal_obj):
    groups=np.asarray(groups).astype(str); cal_obj=np.asarray(cal_obj).astype(str)
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        inner=inner_oof_base(num[tr],obj[tr],y[tr],groups[tr])
        alpha,sa,scale=choose_params(cal_obj[tr],y[tr],inner)
        bm=fit_base(num[tr],obj[tr],y[tr]); pb=predict_base(bm,num[va],obj[va])
        # fit calibration only from outer-train OOF predictions to avoid in-sample optimism
        tab,zm=fit_shrunk_obj_cal(cal_obj[tr],y[tr],inner,alpha,sa)
        pr=pred_shrunk(tab,zm,cal_obj[va],pb,scale)
        p0[va]=pb; p1[va]=pr
        folds.append({'fold':k,'base':float(log_loss(y[va],pb)),'conditional':float(log_loss(y[va],pr)),
                      'alpha':alpha,'slope_alpha':sa,'scale':scale,'win':bool(log_loss(y[va],pr)<log_loss(y[va],pb))})
        print(f"fold {k}/5 base={folds[-1]['base']:.6f} conditional={folds[-1]['conditional']:.6f} a={alpha} sa={sa} s={scale}",flush=True)
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {'base_logloss':ll0,'conditional_logloss':ll1,'improvement':ll0-ll1,
            'base_auc':float(roc_auc_score(y,p0)),'conditional_auc':float(roc_auc_score(y,p1)),
            'fold_wins':int(sum(f['win'] for f in folds)),'folds':folds}


def main(a):
    b=load_bundle(a.bundle.resolve()); y=b['y']; num=b['numeric']; obj=b['objective']; sess=b['session']
    rng=np.random.default_rng(SEED); sh=obj[rng.permutation(len(obj))]
    session=evaluate(y,num,obj,sess,obj)
    shuffled=evaluate(y,num,obj,sess,sh)
    objective_cold=evaluate(y,num,obj,obj,obj)
    sep=session['improvement']-shuffled['improvement']
    if session['improvement']>=.003 and session['fold_wins']>=4 and sep>=.0015:
        decision='BIG_GAIN_OBJECTIVE_CONDITIONAL_CALIBRATION'
    elif session['improvement']>=.001 and session['fold_wins']>=3 and sep>=.0005:
        decision='PROMISING_OBJECTIVE_CONDITIONAL_SIGNAL'
    else:
        decision='NO_BIG_GAIN_OBJECTIVE_CONDITIONAL_CALIBRATION'
    out={'protocol':'V162_OBJECTIVE_CONDITIONAL_CALIBRATION_SEPARATOR','rows':len(y),
         'residual':'V161 rejected generic nonlinear capacity. Test whether the missing distinction is objective-specific calibration of the strong trajectory base rather than a globally richer model.',
         'session':session,'objective_cold':objective_cold,'shuffled_objective_control':shuffled,'separator':sep,'decision':decision}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v162_results.json')); main(p.parse_args())
