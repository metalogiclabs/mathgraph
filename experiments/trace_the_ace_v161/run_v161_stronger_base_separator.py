#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE=Path(__file__).resolve().parent
V150=HERE.parent/'trace_the_ace_v150'
sys.path.insert(0,str(V150))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base

SEED=20260826

def cat_frame(num,obj):
    import pandas as pd
    X=pd.DataFrame(num,columns=[f'n{i}' for i in range(num.shape[1])])
    X['objective']=np.asarray(obj).astype(str)
    return X

def fit_cat(num,obj,y):
    from catboost import CatBoostClassifier
    X=cat_frame(num,obj)
    m=CatBoostClassifier(
        iterations=500, depth=7, learning_rate=.035, loss_function='Logloss',
        eval_metric='Logloss', l2_leaf_reg=6.0, random_seed=SEED,
        verbose=False, allow_writing_files=False, thread_count=-1,
    )
    m.fit(X,y,cat_features=['objective'],verbose=False)
    return m

def predict_cat(m,num,obj):
    p=m.predict_proba(cat_frame(num,obj))[:,1]
    return np.clip(p,1e-5,1-1e-5)

def evaluate(y,num,obj,groups):
    groups=np.asarray(groups).astype(str)
    pb=np.zeros(len(y)); pc=np.zeros(len(y)); pe=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        bm=fit_base(num[tr],obj[tr],y[tr]); cb=fit_cat(num[tr],obj[tr],y[tr])
        b=predict_base(bm,num[va],obj[va]); c=predict_cat(cb,num[va],obj[va])
        best=None
        # blend only on a grouped inner OOF set; no validation tuning
        gtr=groups[tr]; inner_b=np.zeros(len(tr)); inner_c=np.zeros(len(tr))
        for itr,iva in GroupKFold(min(4,len(np.unique(gtr)))).split(np.zeros(len(tr)),y[tr],gtr):
            ib=fit_base(num[tr][itr],obj[tr][itr],y[tr][itr]); ic=fit_cat(num[tr][itr],obj[tr][itr],y[tr][itr])
            inner_b[iva]=predict_base(ib,num[tr][iva],obj[tr][iva]); inner_c[iva]=predict_cat(ic,num[tr][iva],obj[tr][iva])
        for w in (0,.15,.3,.45,.6,.75,.9,1.0):
            p=(1-w)*inner_b+w*inner_c; ll=float(log_loss(y[tr],p))
            if best is None or ll<best[0]: best=(ll,w)
        w=best[1]; e=(1-w)*b+w*c
        pb[va]=b; pc[va]=c; pe[va]=e
        folds.append({'fold':k,'base':float(log_loss(y[va],b)),'cat':float(log_loss(y[va],c)),'blend':float(log_loss(y[va],e)),'weight_cat':w})
        print(f'fold {k}/5 base={folds[-1]["base"]:.6f} cat={folds[-1]["cat"]:.6f} blend={folds[-1]["blend"]:.6f} w={w}',flush=True)
    def met(p): return {'logloss':float(log_loss(y,p)),'auc':float(roc_auc_score(y,p))}
    mb,mc,me=met(pb),met(pc),met(pe)
    return {'base':mb,'catboost':mc,'blend':me,'cat_improvement':mb['logloss']-mc['logloss'],'blend_improvement':mb['logloss']-me['logloss'],'folds':folds,'blend_fold_wins':sum(f['blend']<f['base'] for f in folds)}

def main(a):
    b=load_bundle(a.bundle.resolve()); y=b['y'];
    session=evaluate(y,b['numeric'],b['objective'],b['session'])
    objective=evaluate(y,b['numeric'],b['objective'],b['objective'])
    imp=session['blend_improvement']
    if imp>=.005 and session['blend_fold_wins']>=4:
        decision='BIG_GAIN_BASE_FAMILY_FOUND'
    elif imp>=.002 and session['blend_fold_wins']>=3:
        decision='PROMISING_STRONGER_BASE'
    else:
        decision='NO_BIG_GAIN_FROM_NONLINEAR_BASE'
    out={'protocol':'V161_STRONGER_BASE_SEPARATOR','rows':len(y),'session':session,'objective_cold':objective,'decision':decision,
         'residual':'V160 revoked long-context residual. Test whether the live gap is model-family/interaction capacity rather than missing transcript observables.'}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v161_results.json')); main(p.parse_args())
