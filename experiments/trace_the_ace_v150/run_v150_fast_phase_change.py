#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from scipy.sparse import hstack, csr_matrix

SEED=1729

def safe_logit(p):
    return logit(np.clip(np.asarray(p),1e-5,1-1e-5))

def load_bundle(path:Path):
    b=np.load(path,allow_pickle=True)
    return {
      'y':b['y'].astype(int),
      'session':b['session_id'].astype(str),
      'objective':b['objective_group'].astype(str),
      'numeric':b['numeric'].astype(float),
      'S':b['semantic'].astype(float),
      'ci':b['control_index'].astype(int),
      'Sswap':b['objective_swap'].astype(float),
      'Sempty':b['evidence_empty'].astype(float),
    }

def fit_base(num, obj, y):
    enc=OneHotEncoder(handle_unknown='ignore', min_frequency=2)
    O=enc.fit_transform(obj.reshape(-1,1))
    sc=StandardScaler().fit(num)
    X=hstack([O,csr_matrix(sc.transform(num))],format='csr')
    m=LogisticRegression(C=.25,max_iter=250,solver='liblinear',random_state=SEED).fit(X,y)
    return enc,sc,m

def predict_base(model,num,obj):
    enc,sc,m=model
    X=hstack([enc.transform(obj.reshape(-1,1)),csr_matrix(sc.transform(num))],format='csr')
    return np.clip(m.predict_proba(X)[:,1],1e-5,1-1e-5)

def sem_features(p,S):
    p=np.clip(p,1e-5,1-1e-5); lp=safe_logit(p)
    ent=-(p*np.log(p)+(1-p)*np.log(1-p))
    return np.column_stack([S,lp,np.abs(lp),p,ent,S*p[:,None],S*ent[:,None]])

def choose_delta(p,y,Z):
    target=np.clip((y-p)/(p*(1-p)+1e-3),-4,4)
    best=None
    for alpha in (1.,10.,100.):
      r=Ridge(alpha=alpha).fit(Z,target); d=r.predict(Z)
      for lam in (.10,.25,.50,.75,1.0):
        for q in (0.,.5,.7,.85):
          thr=0 if q==0 else float(np.quantile(np.abs(d),q))
          gate=np.abs(d)>=thr
          pp=expit(safe_logit(p)+lam*d*gate)
          ll=float(log_loss(y,pp))
          if best is None or ll<best[0]: best=(ll,r,lam,thr,q)
    return best[1],{'lambda':best[2],'threshold':best[3],'quantile':best[4]}

def eval_split(name,num,obj,S,y,groups):
    groups=np.asarray(groups).astype(str)
    splits=list(GroupKFold(5).split(np.zeros(len(y)),y,groups))
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(splits,1):
      # Cheap low-dimensional base. Inner residual target uses a second grouped split.
      inner=np.zeros(len(tr))
      gtr=groups[tr]; n=min(4,len(np.unique(gtr)))
      for itr,iva in GroupKFold(n).split(np.zeros(len(tr)),y[tr],gtr):
        bm=fit_base(num[tr][itr],obj[tr][itr],y[tr][itr])
        inner[iva]=predict_base(bm,num[tr][iva],obj[tr][iva])
      ss=StandardScaler().fit(S[tr]); Str=ss.transform(S[tr]); Sva=ss.transform(S[va])
      router,par=choose_delta(inner,y[tr],sem_features(inner,Str))
      bm=fit_base(num[tr],obj[tr],y[tr]); pb=predict_base(bm,num[va],obj[va])
      d=router.predict(sem_features(pb,Sva)); gate=np.abs(d)>=par['threshold']
      pr=expit(safe_logit(pb)+par['lambda']*d*gate)
      p0[va]=pb; p1[va]=pr
      folds.append({'fold':k,'base':float(log_loss(y[va],pb)),'routed':float(log_loss(y[va],pr)),'coverage':float(gate.mean()),'params':par})
      print(f'{name} fold {k}/5',flush=True)
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {'base_logloss':ll0,'routed_logloss':ll1,'improvement':ll0-ll1,
            'base_auc':float(roc_auc_score(y,p0)),'routed_auc':float(roc_auc_score(y,p1)),
            'fold_wins':int(sum(f['routed']<f['base'] for f in folds)),'folds':folds}

def main(a):
    b=load_bundle(a.bundle.resolve()); y=b['y']; rng=np.random.default_rng(SEED); sh=b['S'][rng.permutation(len(y))]
    out={'protocol':'V150_FAST_SEMANTIC_PHASE_CHANGE_TRIAGE','warning':'TRIAGE_ONLY_NOT_SUBMISSION_EVIDENCE','rows':len(y)}
    out['session']=eval_split('session',b['numeric'],b['objective'],b['S'],y,b['session'])
    out['objective']=eval_split('objective',b['numeric'],b['objective'],b['S'],y,b['objective'])
    out['shuffled']={
      'session':eval_split('session_shuffled',b['numeric'],b['objective'],sh,y,b['session']),
      'objective':eval_split('objective_shuffled',b['numeric'],b['objective'],sh,y,b['objective'])}
    ci=b['ci']; yc=y[ci]; numc=b['numeric'][ci]; objc=b['objective'][ci]
    out['controls']={}
    for nm,Sc in [('objective_swap',b['Sswap']),('evidence_empty',b['Sempty'])]:
      out['controls'][nm]={
        'session':eval_split(nm+'_session',numc,objc,Sc,yc,b['session'][ci]),
        'objective':eval_split(nm+'_objective',numc,objc,Sc,yc,b['objective'][ci])}
    s,o=out['session'],out['objective']; ss=out['shuffled']['session']; so=out['shuffled']['objective']
    # Strong triage threshold: sizeable cold gains and clear advantage over shuffle.
    phase=(o['improvement']>=.003 and s['improvement']>=.001 and o['fold_wins']>=4 and s['fold_wins']>=3 and
           o['improvement']>so['improvement']+.001 and s['improvement']>ss['improvement']+.0005)
    out['decision']='PHASE_CHANGE_CANDIDATE' if phase else 'NO_MASSIVE_GAIN_IN_FAST_TRIAGE'
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v150_results.json')); a=p.parse_args(); main(a)
