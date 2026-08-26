#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

SEED=20260827

def load_data(features, labels):
    fcols=list(pd.read_csv(features,nrows=0).columns)
    lcols=list(pd.read_csv(labels,nrows=0).columns)
    print('FEATURE_HEADERS',fcols,flush=True)
    print('LABEL_HEADERS',lcols,flush=True)
    need={'response_id','session_id','learning_objective_id'}
    if not need.issubset(fcols): raise ValueError(f'missing feature cols {sorted(need-set(fcols))}')
    target='is_correct' if 'is_correct' in lcols else 'correct' if 'correct' in lcols else None
    if target is None: raise ValueError('labels missing target')
    f=pd.read_csv(features)
    y=pd.read_csv(labels)
    return f.merge(y[['response_id',target]],on='response_id',validate='one_to_one').rename(columns={target:'target'})

def prior_predict(train, valid, alpha):
    gm=float(train.target.mean())
    stats=train.groupby('learning_objective_id').target.agg(['sum','count'])
    pri=(stats['sum']+alpha*gm)/(stats['count']+alpha)
    p=valid.learning_objective_id.map(pri).fillna(gm).to_numpy(float)
    return np.clip(p,1e-6,1-1e-6)

def fullfit_predict(df, alpha):
    gm=float(df.target.mean())
    stats=df.groupby('learning_objective_id').target.agg(['sum','count'])
    pri=(stats['sum']+alpha*gm)/(stats['count']+alpha)
    return np.clip(df.learning_objective_id.map(pri).fillna(gm).to_numpy(float),1e-6,1-1e-6)

def eval_alpha(df, alpha, folds):
    oof=np.zeros(len(df),dtype=float); rows=[]
    y=df.target.to_numpy(int)
    for k,(tr,va) in enumerate(folds,1):
        p=prior_predict(df.iloc[tr],df.iloc[va],alpha)
        oof[va]=p
        row={'fold':k,'rows':int(len(va)),'logloss':float(log_loss(y[va],p)),'auc':float(roc_auc_score(y[va],p))}
        print(f'alpha={alpha}',row,flush=True); rows.append(row)
    return {'alpha':alpha,'oof_logloss':float(log_loss(y,oof)),'oof_auc':float(roc_auc_score(y,oof)),'per_fold':rows,'pred_mean':float(oof.mean()),'pred_std':float(oof.std())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--features',required=True); ap.add_argument('--labels',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    df=load_data(a.features,a.labels); y=df.target.to_numpy(int)
    groups=df.session_id.astype(str).to_numpy()
    folds=list(GroupKFold(n_splits=5).split(np.zeros(len(df)),y,groups))
    alphas=[0.5,1,2,5,10,20,50,100]
    cross=[eval_alpha(df,x,folds) for x in alphas]
    full=[]
    for x in alphas:
        p=fullfit_predict(df,x)
        full.append({'alpha':x,'fullfit_logloss':float(log_loss(y,p)),'fullfit_auc':float(roc_auc_score(y,p))})
    best_oof=min(cross,key=lambda r:r['oof_logloss']); best_full=min(full,key=lambda r:r['fullfit_logloss'])
    public=0.6037
    result={
      'protocol':'V171_STRICT_CROSSFIT_OBJECTIVE_PRIOR_PARITY',
      'rows':int(len(df)),'sessions':int(df.session_id.nunique()),'objectives':int(df.learning_objective_id.nunique()),
      'global_mean':float(df.target.mean()),'global_logloss':float(log_loss(y,np.full(len(df),df.target.mean()))),
      'crossfit':cross,'fullfit':full,'best_crossfit':best_oof,'best_fullfit':best_full,
      'known_public_v154_v157_logloss':public,
      'optimism_gap_best_fullfit_to_crossfit':float(best_oof['oof_logloss']-best_full['fullfit_logloss']),
      'crossfit_to_public_gap':float(public-best_oof['oof_logloss'])
    }
    if best_oof['oof_logloss']>=0.59:
        decision='FULLFIT_OPTIMISM_EXPLAINS_MOST_OFFLINE_GAP'
        residual='Objective-prior performance collapses under strict session-grouped cross-fitting; stop treating full-fit ~0.54 as deployable evidence.'
    elif best_oof['oof_logloss']>=0.575:
        decision='FULLFIT_OPTIMISM_MATERIAL_BUT_INCOMPLETE'
        residual='Cross-fitting removes a large fraction of the apparent gain, but a remaining CV-to-public gap still needs production/distribution analysis.'
    else:
        decision='CROSSFIT_PRIOR_REMAINS_STRONG'
        residual='Strict grouped OOF prior remains far better than public; investigate test distribution shift or production equation next.'
    result['decision']=decision; result['residual']=residual
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__': main()
