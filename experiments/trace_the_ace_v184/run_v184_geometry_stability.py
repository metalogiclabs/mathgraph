#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

# Reuse the exact V183 representation/graph machinery; V184 changes only the
# sampling/evaluation protocol so the positive separator is tested out of sample.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'trace_the_ace_v183'))
import run_v183_mastery_geometry as v183

OUT=Path('/workspace/trace-ace-results/v184')
N_TRAIN=8000
N_TEST_EACH=1000
TEST_TAGS=['V184_TEST_A','V184_TEST_B','V184_TEST_C']
EPS=1e-6

def metric(y,p):
    return {'logloss':float(log_loss(y,np.clip(p,EPS,1-EPS))), 'auc':float(roc_auc_score(y,p))}

def take_sessions(df,n,tag,forbidden=None):
    forbidden=set() if forbidden is None else set(forbidden)
    avail=df[~df.session_id.isin(forbidden)].copy()
    chosen=v183.session_sample(avail,n,tag)
    return set(chosen)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    X=pd.read_csv(v183.FEAT); Y=pd.read_csv(v183.LAB)
    print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    target='is_correct' if 'is_correct' in Y.columns else 'correct'
    Y=Y.rename(columns={target:'is_correct'})
    df=X.merge(Y,on='response_id',validate='one_to_one')

    # Three mutually disjoint session holdouts, frozen before training.
    used=set(); tests=[]
    for tag in TEST_TAGS:
        ss=take_sessions(df,N_TEST_EACH,tag,used); used |= ss
        t=df[df.session_id.isin(ss)].copy().reset_index(drop=True); tests.append(t)
        print(tag,'SESSIONS',len(ss),'ROWS',len(t))
    pool=df[~df.session_id.isin(used)].copy()
    train_sessions=v183.session_sample(pool,N_TRAIN,'V184_TRAIN')
    train=pool[pool.session_id.isin(train_sessions)].copy().reset_index(drop=True)
    print('TRAIN_SESSIONS',len(train_sessions),'TRAIN_ROWS',len(train))

    work=pd.concat([train]+tests,ignore_index=True); ntr=len(train)
    offsets=[]; pos=ntr
    for t in tests: offsets.append((pos,pos+len(t))); pos+=len(t)

    cache={}; texts=[]; scal=[]
    for k,r in enumerate(work.itertuples(index=False)):
        tx,val=v183.build_row(str(r.session_id),str(r.learning_objective),cache)
        texts.append(tx); scal.append(val)
        if (k+1)%1000==0: print('FEATURE_ROWS',k+1)
    scal=np.vstack(scal); mu=scal[:ntr].mean(0); sd=scal[:ntr].std(0); sd[sd<1e-8]=1; scal=(scal-mu)/sd

    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
    Xt=vec.fit_transform(texts[:ntr]); Xa=vec.transform(texts[ntr:])
    Xtr=hstack([Xt,csr_matrix(scal[:ntr])],format='csr'); Xall=hstack([Xa,csr_matrix(scal[ntr:])],format='csr')
    y=train.is_correct.to_numpy(int); groups=train.session_id.astype(str).to_numpy(); gkf=GroupKFold(n_splits=4)

    # Exact V179 control OOF and exact V183 graph OOF features.
    oof=np.zeros(ntr); op=np.zeros(ntr); oc=np.zeros(ntr); graph_oof=np.zeros(ntr); graph_sup_oof=np.zeros(ntr)
    for f,(a,b) in enumerate(gkf.split(np.zeros(ntr),y,groups)):
        m=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827)
        m.fit(Xtr[a],y[a]); oof[b]=m.predict_proba(Xtr[b])[:,1]
        p_a,_,_=v183.objective_prior(train.iloc[a],train.iloc[a],2.0)
        p_b,c_b,_=v183.objective_prior(train.iloc[a],train.iloc[b],2.0); op[b]=p_b; oc[b]=c_b
        objs,oi,W,cnt=v183.fit_graph(train.iloc[a].reset_index(drop=True),p_a)
        sig,sup=v183.propagated_signal(train.iloc[b].reset_index(drop=True),oof[b],oi,W)
        graph_oof[b]=sig; graph_sup_oof[b]=sup
        print('FOLD',f,'ROWS',len(b),'GRAPH_EDGES',int((cnt>0).sum()),'NONZERO_PROP',int((sup>0).sum()))

    A=np.column_stack([v183.logit(oof),v183.logit(op),np.log1p(oc),v183.logit(oof)*np.log1p(oc),v183.logit(op)*np.log1p(oc)])
    AG=np.column_stack([A,graph_oof,np.tanh(graph_oof),np.log1p(graph_sup_oof),graph_oof*np.log1p(graph_sup_oof)])
    control_meta=LogisticRegression(C=.25,solver='liblinear',max_iter=200).fit(A,y)
    # Frozen from V183 winner. No C selection on V184 holdouts.
    geometry_meta=LogisticRegression(C=.1,solver='liblinear',max_iter=240).fit(AG,y)

    final=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Xtr,y)
    pall=final.predict_proba(Xall)[:,1]
    p_train_prior,_,_=v183.objective_prior(train,train,2.0)
    objs,oi,W,cnt=v183.fit_graph(train,p_train_prior)

    per_split=[]; pooled_y=[]; pooled_control=[]; pooled_geometry=[]
    rel=0
    for tag,t in zip(TEST_TAGS,tests):
        n=len(t); Xslice=Xall[rel:rel+n]; ptext=pall[rel:rel+n]; rel+=n
        tp,tc,_=v183.objective_prior(train,t,2.0)
        psig,psup=v183.propagated_signal(t,ptext,oi,W)
        B=np.column_stack([v183.logit(ptext),v183.logit(tp),np.log1p(tc),v183.logit(ptext)*np.log1p(tc),v183.logit(tp)*np.log1p(tc)])
        BG=np.column_stack([B,psig,np.tanh(psig),np.log1p(psup),psig*np.log1p(psup)])
        pc=control_meta.predict_proba(B)[:,1]; pg=geometry_meta.predict_proba(BG)[:,1]; yt=t.is_correct.to_numpy(int)
        mc=metric(yt,pc); mg=metric(yt,pg); d=mg['logloss']-mc['logloss']
        row={'split':tag,'rows':n,'control':mc,'geometry_C0.1':mg,'delta_logloss':float(d),'delta_auc':float(mg['auc']-mc['auc']),'rows_with_geometry':int((psup>0).sum())}
        per_split.append(row); print('SPLIT_RESULT',json.dumps(row))
        pooled_y.extend(yt.tolist()); pooled_control.extend(pc.tolist()); pooled_geometry.extend(pg.tolist())
        pd.DataFrame({'response_id':t.response_id.astype(str),'y':yt,'p_control':pc,'p_geometry':pg,'geometry_signal':psig,'geometry_support':psup}).to_csv(OUT/f'{tag.lower()}_predictions.csv',index=False)

    py=np.asarray(pooled_y); pc=np.asarray(pooled_control); pg=np.asarray(pooled_geometry)
    pmc=metric(py,pc); pmg=metric(py,pg); pooled_delta=pmg['logloss']-pmc['logloss']
    wins=sum(r['delta_logloss']<0 for r in per_split)
    # Strong gate: improvement on every disjoint split and meaningful pooled gain.
    if wins==3 and pooled_delta<=-0.002:
        decision='MASTERY_GEOMETRY_STABLE__PROMOTE_TO_SUBMISSION_BUILD'
    elif wins>=2 and pooled_delta<0:
        decision='MASTERY_GEOMETRY_REAL_BUT_UNSTABLE__REFINE_GATE'
    else:
        decision='MASTERY_GEOMETRY_FAILED_STABILITY__DO_NOT_PROMOTE'
    result={'protocol':'V184_GEOMETRY_STABILITY','train_rows':len(train),'test_rows_total':len(py),'test_rows_each':[len(t) for t in tests],'frozen_geometry_C':0.1,'per_split':per_split,'pooled':{'control':pmc,'geometry_C0.1':pmg,'delta_logloss':float(pooled_delta),'delta_auc':float(pmg['auc']-pmc['auc'])},'wins':wins,'graph_objectives':len(objs),'graph_observed_edges':int((cnt>0).sum()),'decision':decision}
    (OUT/'v184_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
