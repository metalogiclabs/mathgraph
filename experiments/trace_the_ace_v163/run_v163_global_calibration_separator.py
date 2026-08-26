#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE=Path(__file__).resolve().parent
V150=HERE.parent/'trace_the_ace_v150'
sys.path.insert(0,str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base, safe_logit

EPS=1e-5
SEED=20260826

def clip(p): return np.clip(np.asarray(p,float),EPS,1-EPS)

def fit_temp(y,p):
    z=safe_logit(clip(p)); best=(1e9,1.0)
    for t in np.concatenate([np.linspace(.5,1.5,41),np.linspace(1.6,3.0,15)]):
        q=expit(z/t); ll=float(log_loss(y,q))
        if ll<best[0]: best=(ll,float(t))
    return best[1]

def apply_temp(p,t): return clip(expit(safe_logit(clip(p))/t))

def fit_platt(y,p):
    z=safe_logit(clip(p)).reshape(-1,1)
    m=LogisticRegression(C=1e6,solver='lbfgs',max_iter=500,random_state=SEED)
    m.fit(z,y); return m

def apply_platt(p,m): return clip(m.predict_proba(safe_logit(clip(p)).reshape(-1,1))[:,1])

def fit_iso(y,p):
    m=IsotonicRegression(out_of_bounds='clip',y_min=EPS,y_max=1-EPS)
    m.fit(clip(p),y); return m

def inner_oof(y,num,obj,groups):
    groups=np.asarray(groups).astype(str); out=np.zeros(len(y))
    n=min(4,len(np.unique(groups)))
    for tr,va in GroupKFold(n).split(np.zeros(len(y)),y,groups):
        m=fit_base(num[tr],obj[tr],y[tr]); out[va]=predict_base(m,num[va],obj[va])
    return clip(out)

def evaluate(y,num,obj,groups):
    groups=np.asarray(groups).astype(str)
    p0=np.zeros(len(y)); pt=np.zeros(len(y)); pp=np.zeros(len(y)); pi=np.zeros(len(y)); psel=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        inn=inner_oof(y[tr],num[tr],obj[tr],groups[tr])
        t=fit_temp(y[tr],inn); pm=fit_platt(y[tr],inn); im=fit_iso(y[tr],inn)
        inner_candidates={
            'identity':clip(inn),
            'temperature':apply_temp(inn,t),
            'platt':apply_platt(inn,pm),
            'isotonic':clip(im.predict(clip(inn))),
        }
        inner_ll={n:float(log_loss(y[tr],q)) for n,q in inner_candidates.items()}
        chosen=min(inner_ll,key=inner_ll.get)
        bm=fit_base(num[tr],obj[tr],y[tr]); b=clip(predict_base(bm,num[va],obj[va]))
        cand={
            'identity':b,
            'temperature':apply_temp(b,t),
            'platt':apply_platt(b,pm),
            'isotonic':clip(im.predict(b)),
        }
        p0[va]=b; pt[va]=cand['temperature']; pp[va]=cand['platt']; pi[va]=cand['isotonic']; psel[va]=cand[chosen]
        row={'fold':k,'chosen':chosen,'temperature':t,'inner_logloss':inner_ll,
             'base':float(log_loss(y[va],b)),
             'temp':float(log_loss(y[va],cand['temperature'])),
             'platt':float(log_loss(y[va],cand['platt'])),
             'isotonic':float(log_loss(y[va],cand['isotonic'])),
             'selected':float(log_loss(y[va],cand[chosen]))}
        row['win']=row['selected']<row['base']; folds.append(row)
        print(f"fold {k}/5 base={row['base']:.6f} temp={row['temp']:.6f} platt={row['platt']:.6f} iso={row['isotonic']:.6f} selected={chosen}:{row['selected']:.6f}",flush=True)
    def m(p): return {'logloss':float(log_loss(y,clip(p))),'auc':float(roc_auc_score(y,p))}
    mb,mt,mp,mi,ms=map(m,(p0,pt,pp,pi,psel))
    return {'base':mb,'temperature':mt,'platt':mp,'isotonic':mi,'selected':ms,
            'selected_improvement':mb['logloss']-ms['logloss'],
            'best_fixed_improvement':mb['logloss']-min(mt['logloss'],mp['logloss'],mi['logloss']),
            'fold_wins':int(sum(f['win'] for f in folds)),'folds':folds}

def main(a):
    b=load_bundle(a.bundle.resolve()); y=b['y']; num=b['numeric']; obj=b['objective']; sess=b['session']
    session=evaluate(y,num,obj,sess); objective=evaluate(y,num,obj,obj)
    gain=session['selected_improvement']
    if gain>=.003 and session['fold_wins']>=4: decision='BIG_GLOBAL_CALIBRATION_GAIN'
    elif gain>=.001 and session['fold_wins']>=3: decision='SMALL_GLOBAL_CALIBRATION_GAIN'
    else: decision='GLOBAL_CALIBRATION_EXHAUSTED'
    out={'protocol':'V163_NESTED_GLOBAL_CALIBRATION_SEPARATOR','rows':len(y),
         'residual':'V162 objective-conditional correction overfit. Test standard global temperature, Platt, and isotonic calibration with strict nested OOF selection.',
         'session':session,'objective_cold':objective,'decision':decision}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,required=True); main(p.parse_args())
