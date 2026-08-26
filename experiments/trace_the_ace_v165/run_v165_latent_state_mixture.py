#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE=Path(__file__).resolve().parent
V145=HERE.parent/'trace_the_ace_v145'
sys.path.insert(0,str(V145))
from v71_mastery_events import inspect_headers, load_transcript, extract_episodes
from v75_canonical_trajectory import trajectory_views

SEED=20260826


def episode_vec(e):
    return np.array([
        e.relevance,e.feedback_pos,e.feedback_neg,e.hinted,e.answer_substantive,
        e.answer_agreement,e.recency,
        e.feedback_pos*e.answer_substantive*(1.0-e.hinted),
        e.feedback_neg*e.answer_substantive,
    ],float)


def latent_features(df, objective):
    eps=extract_episodes(df,objective)
    if not eps:
        return np.zeros(60,float)
    V=np.vstack([episode_vec(e) for e in eps])
    rel=V[:,0]
    score=rel*(0.25+0.75*V[:,6])
    order=np.argsort(score)[::-1]
    V=V[order]
    score=score[order]
    # Keep several candidate local states alive instead of collapsing to one session summary.
    top=np.zeros((3,V.shape[1]),float)
    m=min(3,len(V)); top[:m]=V[:m]
    # Soft mixture summaries at several temperatures.
    pooled=[]
    for temp in (0.15,0.35,0.75,1.5):
        z=(score-score.max())/temp
        w=np.exp(np.clip(z,-50,50)); w=w/(w.sum()+1e-12)
        mu=(w[:,None]*V).sum(0)
        var=(w[:,None]*(V-mu)**2).sum(0)
        pooled.extend(mu.tolist())
        pooled.extend(var[:3].tolist())
    # Mixture uncertainty / disagreement features.
    p=score-score.min()+1e-6; p=p/p.sum()
    ent=float(-(p*np.log(p+1e-12)).sum()/np.log(max(2,len(p))))
    extras=np.array([
        len(eps),float(score.max()),float(score.mean()),float(score.std()),ent,
        float((rel>0.05).sum()),float((rel>0.10).sum()),float((rel>0.20).sum()),
        float(np.max(V[:,6])),float(np.min(V[:,6])),float(V[0,6]),
        float(V[:min(3,len(V)),1].mean()),float(V[:min(3,len(V)),2].mean()),
        float(V[:min(3,len(V)),7].mean()),float(V[:min(3,len(V)),8].mean()),
    ])
    out=np.concatenate([top.ravel(),np.asarray(pooled),extras])
    # fixed 60 dims
    if len(out)<60: out=np.pad(out,(0,60-len(out)))
    return out[:60]


def compile_features(frame,tdir):
    cache={}; whole=[]; latent=[]
    for i,row in enumerate(frame.itertuples(index=False),1):
        sid=str(row.session_id)
        if sid not in cache: cache[sid]=load_transcript(tdir/f'{sid}.csv')
        df=cache[sid]
        _,wf,_=trajectory_views(df,str(row.learning_objective))
        whole.append(wf)
        latent.append(latent_features(df,str(row.learning_objective)))
        if i%2000==0: print(f'compiled {i}/{len(frame)}',flush=True)
    return np.vstack(whole),np.vstack(latent)


def fit_predict(Xnum,obj,y,tr,va):
    enc=OneHotEncoder(handle_unknown='ignore',min_frequency=2)
    Otr=enc.fit_transform(obj[tr].reshape(-1,1)); Ova=enc.transform(obj[va].reshape(-1,1))
    sc=StandardScaler().fit(Xnum[tr]); Xtr=hstack([Otr,csr_matrix(sc.transform(Xnum[tr]))],format='csr'); Xva=hstack([Ova,csr_matrix(sc.transform(Xnum[va]))],format='csr')
    m=LogisticRegression(C=.25,max_iter=300,solver='liblinear',random_state=SEED).fit(Xtr,y[tr])
    return np.clip(m.predict_proba(Xva)[:,1],1e-5,1-1e-5)


def eval_regime(name,y,obj,groups,whole,latent):
    p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(5).split(np.zeros(len(y)),y,groups),1):
        pb=fit_predict(whole,obj,y,tr,va)
        pc=fit_predict(np.hstack([whole,latent]),obj,y,tr,va)
        p0[va]=pb; p1[va]=pc
        a=float(log_loss(y[va],pb)); b=float(log_loss(y[va],pc))
        folds.append({'fold':k,'base':a,'mixture':b,'improvement':a-b,'win':b<a})
        print(name,'fold',k,'gain',a-b,flush=True)
    return {
        'base_logloss':float(log_loss(y,p0)),'mixture_logloss':float(log_loss(y,p1)),
        'improvement':float(log_loss(y,p0)-log_loss(y,p1)),
        'base_auc':float(roc_auc_score(y,p0)),'mixture_auc':float(roc_auc_score(y,p1)),
        'fold_wins':int(sum(f['win'] for f in folds)),'folds':folds
    }


def main(a):
    print('FEATURE_HEADERS',inspect_headers(a.features)); print('LABEL_HEADERS',inspect_headers(a.labels))
    f=pd.read_csv(a.features); l=pd.read_csv(a.labels)
    frame=f.merge(l[['response_id','is_correct']],on='response_id',validate='one_to_one')
    y=frame.is_correct.to_numpy(int); obj=frame.learning_objective_id.astype(str).to_numpy(); sess=frame.session_id.astype(str).to_numpy()
    whole,latent=compile_features(frame,a.transcripts)
    session=eval_regime('session',y,obj,sess,whole,latent)
    objective=eval_regime('objective',y,obj,obj,whole,latent)
    rng=np.random.default_rng(SEED); sh=latent[rng.permutation(len(latent))]
    shuffled=eval_regime('shuffled_session',y,obj,sess,whole,sh)
    sep=session['improvement']-shuffled['improvement']
    if session['improvement']>=.005 and session['fold_wins']>=4 and sep>=.002:
        decision='LATENT_STATE_PHASE_CHANGE'
    elif session['improvement']>=.002 and session['fold_wins']>=3 and sep>=.00075:
        decision='PROMISING_LATENT_STATE_SIGNAL'
    else:
        decision='NO_BIG_GAIN_FROM_LATENT_STATE_MIXTURE'
    out={'protocol':'V165_LATENT_STATE_MIXTURE','rows':len(frame),'session':session,'objective_cold':objective,'shuffled_latent_control':shuffled,'separator':sep,'decision':decision,
         'residual':'Preserve several plausible objective-relevant episode states and marginalize over them instead of forcing unavailable endpoint alignment or collapsing to one session summary.'}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--features',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--transcripts',type=Path,required=True); p.add_argument('--out',type=Path,required=True); main(p.parse_args())
