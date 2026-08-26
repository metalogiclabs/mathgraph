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
from v71_mastery_events import inspect_headers, load_transcript
from v75_canonical_trajectory import trajectory_views

SEED=20260826

def norm(x):
    s=str(x).strip()
    return s[:-2] if s.endswith('.0') else s

def digits(x):
    m=re.findall(r'\d+',norm(x)); return m[-1] if m else ''

def load_frame(fp,lp):
    fc=inspect_headers(fp); lc=inspect_headers(lp)
    print('FEATURE_HEADERS',fc,flush=True); print('LABEL_HEADERS',lc,flush=True)
    target='is_correct' if 'is_correct' in lc else 'correct' if 'correct' in lc else None
    if target is None: raise ValueError('no label target')
    need={'response_id','session_id','learning_objective'}
    if not need.issubset(fc): raise ValueError(f'missing {need-set(fc)}')
    f=pd.read_csv(fp); l=pd.read_csv(lp)
    return f.merge(l[['response_id',target]],on='response_id',validate='one_to_one').rename(columns={target:'target'})

def candidate_maps(frame,tdir):
    cache={}; stats={k:{'matched':0,'ambiguous':0} for k in ['exact','digit_exact','ordinal_student','ordinal_all']}
    maps={k:{} for k in stats}
    total=0
    for sid,g in frame.groupby(frame.session_id.astype(str),sort=False):
        p=tdir/f'{sid}.csv'
        if not p.exists(): continue
        d=load_transcript(p).reset_index(drop=True); cache[sid]=d
        uid=[norm(x) for x in d.utterance_id]
        uid_digit=[digits(x) for x in d.utterance_id]
        students=[i for i,r in enumerate(d.role.astype(str).str.lower()) if r=='student']
        rows=list(g.index)
        # exact and numeric-suffix exact
        for idx in rows:
            rid=norm(frame.at[idx,'response_id']); total+=1
            hits=[i for i,u in enumerate(uid) if u==rid]
            if len(hits)==1: maps['exact'][idx]=hits[0]; stats['exact']['matched']+=1
            elif len(hits)>1: stats['exact']['ambiguous']+=1
            rd=digits(rid); hits=[i for i,u in enumerate(uid_digit) if rd and u==rd]
            if len(hits)==1: maps['digit_exact'][idx]=hits[0]; stats['digit_exact']['matched']+=1
            elif len(hits)>1: stats['digit_exact']['ambiguous']+=1
        # deterministic ordinal hypotheses; only when cardinalities make them defensible
        sr=sorted(rows,key=lambda i:norm(frame.at[i,'response_id']))
        if len(sr)==len(students):
            for idx,pos in zip(sr,students): maps['ordinal_student'][idx]=pos
            stats['ordinal_student']['matched']+=len(sr)
        if len(sr)==len(d):
            for idx,pos in zip(sr,range(len(d))): maps['ordinal_all'][idx]=pos
            stats['ordinal_all']['matched']+=len(sr)
    return cache,maps,stats,total

def features_for(frame,cache,mapping):
    X=[]; keep=[]
    for idx in frame.index:
        sid=str(frame.at[idx,'session_id'])
        if idx not in mapping or sid not in cache: continue
        pos=int(mapping[idx]); d=cache[sid]
        # Include evidence available through tutor feedback immediately following the response.
        end=pos
        if end+1<len(d) and str(d.iloc[end+1].role).lower()=='tutor': end+=1
        pref=d.iloc[:end+1].copy()
        _,f,_=trajectory_views(pref,str(frame.at[idx,'learning_objective']))
        X.append(f); keep.append(idx)
    return np.vstack(X) if X else np.empty((0,0)),np.asarray(keep,int)

def fit_base(num,obj,y):
    enc=OneHotEncoder(handle_unknown='ignore',min_frequency=2)
    O=enc.fit_transform(np.asarray(obj).reshape(-1,1)); sc=StandardScaler().fit(num)
    X=hstack([O,csr_matrix(sc.transform(num))],format='csr')
    m=LogisticRegression(C=.25,max_iter=300,solver='liblinear',random_state=SEED).fit(X,y)
    return enc,sc,m

def pred_base(m,num,obj):
    enc,sc,lr=m; X=hstack([enc.transform(np.asarray(obj).reshape(-1,1)),csr_matrix(sc.transform(num))],format='csr')
    return np.clip(lr.predict_proba(X)[:,1],1e-5,1-1e-5)

def evaluate(frame,Xlocal,keep,group_col):
    sub=frame.loc[keep].copy(); y=sub.target.to_numpy(int); obj=(sub.learning_objective_id if 'learning_objective_id' in sub else sub.learning_objective).astype(str).to_numpy(); groups=sub[group_col].astype(str).to_numpy()
    n=min(5,len(np.unique(groups))); p0=np.zeros(len(y)); p1=np.zeros(len(y)); folds=[]
    for k,(tr,va) in enumerate(GroupKFold(n).split(np.zeros(len(y)),y,groups),1):
        # baseline is whole-session V75 numeric trajectory + objective id
        whole=[]
        for idx in sub.index[tr]:
            sid=str(frame.at[idx,'session_id']); _,f,_=trajectory_views(CACHE[sid],str(frame.at[idx,'learning_objective'])); whole.append(f)
        whole=np.vstack(whole)
        wholev=[]
        for idx in sub.index[va]:
            sid=str(frame.at[idx,'session_id']); _,f,_=trajectory_views(CACHE[sid],str(frame.at[idx,'learning_objective'])); wholev.append(f)
        wholev=np.vstack(wholev)
        bm=fit_base(whole,obj[tr],y[tr]); pb=pred_base(bm,wholev,obj[va])
        # local-state candidate: same base family, but preserves endpoint state instead of whole-session quotient
        lm=fit_base(Xlocal[tr],obj[tr],y[tr]); pl=pred_base(lm,Xlocal[va],obj[va])
        p0[va]=pb; p1[va]=pl
        folds.append({'fold':k,'rows':len(va),'base':float(log_loss(y[va],pb)),'local':float(log_loss(y[va],pl)),'gain':float(log_loss(y[va],pb)-log_loss(y[va],pl))})
    return {'rows':len(y),'base_logloss':float(log_loss(y,p0)),'local_logloss':float(log_loss(y,p1)),'improvement':float(log_loss(y,p0)-log_loss(y,p1)),'base_auc':float(roc_auc_score(y,p0)),'local_auc':float(roc_auc_score(y,p1)),'fold_wins':sum(x['local']<x['base'] for x in folds),'folds':folds}

CACHE={}
def main(a):
    global CACHE
    frame=load_frame(a.features,a.labels)
    CACHE,maps,stats,total=candidate_maps(frame,a.transcripts)
    for k in stats: stats[k]['coverage']=stats[k]['matched']/max(1,total)
    print('MAPPING_STATS',json.dumps(stats,indent=2),flush=True)
    ranked=sorted(stats,key=lambda k:(stats[k]['coverage'],-stats[k]['ambiguous']),reverse=True)
    chosen=None
    # Exact identifiers are preferred. Ordinal mapping is only accepted at very high structural coverage.
    for k in ranked:
        cov=stats[k]['coverage']
        if k in ('exact','digit_exact') and cov>=.50: chosen=k; break
        if k.startswith('ordinal') and cov>=.90: chosen=k; break
    out={'protocol':'V163_RESPONSE_LOCAL_STATE_SEPARATOR','rows':len(frame),'mapping_stats':stats,'chosen_mapping':chosen}
    if chosen is None:
        out['decision']='ENDPOINT_MAPPING_NOT_RECOVERED'; out['residual']='Need a new observable linking response_id to transcript position; do not guess alignment.'
    else:
        X,keep=features_for(frame,CACHE,maps[chosen])
        out['mapped_rows']=len(keep); out['session_cold']=evaluate(frame,X,keep,'session_id')
        objcol='learning_objective_id' if 'learning_objective_id' in frame else 'learning_objective'
        out['objective_cold']=evaluate(frame,X,keep,objcol)
        s=out['session_cold']; o=out['objective_cold']
        if s['improvement']>=.005 and s['fold_wins']>=4 and o['improvement']>=-.001:
            out['decision']='PHASE_CHANGE_FOUND'
        elif s['improvement']>=.002 and s['fold_wins']>=3:
            out['decision']='LOCAL_STATE_PROMISING'
        else:
            out['decision']='LOCAL_STATE_NOT_ENOUGH'
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--features',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--transcripts',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v163_results.json')); main(p.parse_args())
