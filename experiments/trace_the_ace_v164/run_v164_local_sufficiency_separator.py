#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

HERE=Path(__file__).resolve().parent
V150=HERE.parent/'trace_the_ace_v150'
sys.path.insert(0,str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base, safe_logit
from scipy.special import expit

SEED=20260826
EPS=1e-5


def local_residual_predict(num_tr,obj_tr,y_tr,p_tr,num_va,obj_va,p_va,k,shrink):
    sc=StandardScaler().fit(num_tr)
    Xtr=sc.transform(num_tr); Xva=sc.transform(num_va)
    out=np.zeros(len(num_va),float); support=np.zeros(len(num_va),int)
    # Newton-like residual around the base probability; local averaging asks whether
    # current numeric trajectory state contains exploitable structure the global model misses.
    r=(y_tr-p_tr)/(p_tr*(1-p_tr)+1e-3)
    global_r=float(np.mean(r))
    for o in np.unique(obj_va):
        iva=np.where(obj_va==o)[0]; itr=np.where(obj_tr==o)[0]
        if len(itr)<3:
            out[iva]=global_r; continue
        kk=min(k,len(itr))
        nn=NearestNeighbors(n_neighbors=kk,metric='euclidean').fit(Xtr[itr])
        d,ix=nn.kneighbors(Xva[iva])
        # distance-weighted local residual, shrunk by effective support
        w=1.0/(d+0.15); rr=r[itr][ix]
        loc=(w*rr).sum(1)/(w.sum(1)+1e-12)
        eff=np.minimum(len(itr),kk)
        alpha=eff/(eff+shrink)
        out[iva]=alpha*loc+(1-alpha)*global_r
        support[iva]=len(itr)
    return out,support


def inner_oof_base(num,obj,y,groups):
    out=np.zeros(len(y)); groups=np.asarray(groups).astype(str)
    n=min(4,len(np.unique(groups)))
    for tr,va in GroupKFold(n).split(np.zeros(len(y)),y,groups):
        m=fit_base(num[tr],obj[tr],y[tr]); out[va]=predict_base(m,num[va],obj[va])
    return out


def choose_params(num,obj,y,groups,p):
    # Select locality strength only on training OOF predictions. This is deliberately
    # small/bounded: separator, not hyperparameter mining.
    best=None
    groups=np.asarray(groups).astype(str)
    splits=list(GroupKFold(4).split(np.zeros(len(y)),y,groups))
    for k in (5,10,20,40):
      for shrink in (10.,30.,100.):
       for lam in (.10,.25,.50):
        pred=np.zeros(len(y))
        for tr,va in splits:
            d,_=local_residual_predict(num[tr],obj[tr],y[tr],p[tr],num[va],obj[va],p[va],k,shrink)
            pred[va]=np.clip(expit(safe_logit(p[va])+lam*np.clip(d,-3,3)),EPS,1-EPS)
        ll=float(log_loss(y,pred))
        if best is None or ll<best[0]: best=(ll,k,shrink,lam)
    return best[1:]


def evaluate(num,obj,y,groups):
    groups=np.asarray(groups).astype(str); splits=list(GroupKFold(5).split(np.zeros(len(y)),y,groups))
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]; supports=[]
    for j,(tr,va) in enumerate(splits,1):
        inner=inner_oof_base(num[tr],obj[tr],y[tr],groups[tr])
        k,shrink,lam=choose_params(num[tr],obj[tr],y[tr],groups[tr],inner)
        bm=fit_base(num[tr],obj[tr],y[tr]); ptr=predict_base(bm,num[tr],obj[tr]); pb=predict_base(bm,num[va],obj[va])
        d,sup=local_residual_predict(num[tr],obj[tr],y[tr],ptr,num[va],obj[va],pb,k,shrink)
        pr=np.clip(expit(safe_logit(pb)+lam*np.clip(d,-3,3)),EPS,1-EPS)
        p0[va]=pb; p1[va]=pr; supports.extend(sup.tolist())
        a=float(log_loss(y[va],pb)); b=float(log_loss(y[va],pr))
        folds.append({'fold':j,'base':a,'local':b,'gain':a-b,'k':k,'shrink':shrink,'lambda':lam,'win':b<a})
        print(f'fold {j}/5 base={a:.6f} local={b:.6f} gain={a-b:.6f} k={k} sh={shrink} lam={lam}',flush=True)
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {'base_logloss':ll0,'local_logloss':ll1,'improvement':ll0-ll1,
            'base_auc':float(roc_auc_score(y,p0)),'local_auc':float(roc_auc_score(y,p1)),
            'fold_wins':int(sum(f['win'] for f in folds)),
            'support_median':float(np.median(supports)),'support_p10':float(np.quantile(supports,.1)),
            'folds':folds}


def main(a):
    b=load_bundle(a.bundle.resolve()); y=b['y']; num=b['numeric']; obj=b['objective']; sess=b['session']
    main=evaluate(num,obj,y,sess)
    # shuffled numeric control: same objective/support but destroy trajectory geometry
    rng=np.random.default_rng(SEED); sh=num[rng.permutation(len(num))]
    ctrl=evaluate(sh,obj,y,sess)
    sep=main['improvement']-ctrl['improvement']
    if main['improvement']>=.003 and main['fold_wins']>=4 and sep>=.001:
        decision='CURRENT_OBSERVABLE_HAS_UNEXPLOITED_LOCAL_SIGNAL'
    elif main['improvement']>=.001 and main['fold_wins']>=3 and sep>=.0005:
        decision='SMALL_LOCAL_SIGNAL_REMAINS'
    else:
        decision='CURRENT_NUMERIC_OBJECTIVE_OBSERVABLE_NEAR_EXHAUSTED'
    out={'protocol':'V164_LOCAL_REPRESENTATION_SUFFICIENCY_SEPARATOR','rows':len(y),
         'residual':'After nonlinear models and calibration failed, ask whether the existing objective + trajectory-numeric observable still contains locally recoverable label structure. If not, model tweaking is the wrong level; a new observable/feature family is required.',
         'session':main,'shuffled_numeric_control':ctrl,'separator':sep,'decision':decision}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v164_results.json')); main(p.parse_args())
