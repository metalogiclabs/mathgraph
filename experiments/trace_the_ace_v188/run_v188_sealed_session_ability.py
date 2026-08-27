#!/usr/bin/env python3
"""Large fresh sealed judge for the one frozen incremental winner: session ability."""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'trace_the_ace_v183'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'trace_the_ace_v186'))
import run_v183_mastery_geometry as v183
import run_v186_mastery_tournament as v186

OUT=Path('/workspace/trace-ace-results/v188'); OUT.mkdir(parents=True,exist_ok=True)
NTRAIN=11000; NJUDGE=2000; EPS=1e-6

def take(frame,n,tag,forbidden):
 return set(v183.session_sample(frame[~frame.session_id.isin(forbidden)],n,tag))

def predict(Xt,Xe,y):
 return LogisticRegression(C=.1,solver='liblinear',max_iter=240).fit(Xt,y).predict_proba(Xe)[:,1]

def reserve_prior_judges(df):
 # Exactly reconstruct and exclude every V186/V187 evaluation session.
 used186=set()
 for tag in ['V186_DEV_A','V186_DEV_B','V186_DEV_C']:
  s=take(df,600,tag,used186); used186|=s
 s=take(df,1000,'V186_CHAMP',used186); used186|=s
 used187=set()
 for tag in ['V187_JUDGE_A','V187_JUDGE_B','V187_JUDGE_C']:
  s=take(df,800,tag,used187); used187|=s
 return used186|used187

def clustered_bootstrap(frame,y,pbase,pcand,reps=2000):
 groups={}
 for i,s in enumerate(frame.session_id.astype(str)): groups.setdefault(s,[]).append(i)
 keys=list(groups); rng=np.random.default_rng(20260827); ds=[]
 for _ in range(reps):
  chosen=rng.choice(keys,size=len(keys),replace=True)
  idx=np.concatenate([groups[s] for s in chosen])
  ds.append(log_loss(y[idx],np.clip(pcand[idx],EPS,1-EPS))-log_loss(y[idx],np.clip(pbase[idx],EPS,1-EPS)))
 ds=np.asarray(ds)
 return {'repetitions':reps,'clusters':len(keys),'mean':float(ds.mean()),'lower_95':float(np.quantile(ds,.025)),
  'upper_95':float(np.quantile(ds,.975)),'probability_better':float(np.mean(ds<0))}

def main():
 X=pd.read_csv(v183.FEAT); Y=pd.read_csv(v183.LAB)
 print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
 target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
 df=X.merge(Y,on='response_id',validate='one_to_one')
 forbidden=reserve_prior_judges(df)
 judge_sessions=take(df,NJUDGE,'V188_LARGE_SEALED',forbidden); forbidden|=judge_sessions
 judge=df[df.session_id.isin(judge_sessions)].copy().reset_index(drop=True)
 pool=df[~df.session_id.isin(forbidden)].copy(); train_sessions=take(pool,NTRAIN,'V188_TRAIN',set())
 train=pool[pool.session_id.isin(train_sessions)].copy().reset_index(drop=True)
 work=pd.concat([train,judge],ignore_index=True); ntr=len(train)
 print('TRAIN_ROWS',ntr,'SEALED_ROWS',len(judge),'EXCLUDED_PRIOR_JUDGE_SESSIONS',len(forbidden))
 cache={}; texts=[]; scal=[]
 for k,r in enumerate(work.itertuples(index=False)):
  t,s=v183.build_row(str(r.session_id),str(r.learning_objective),cache); texts.append(t); scal.append(s)
  if (k+1)%1000==0: print('FEATURE_ROWS',k+1)
 scal=np.vstack(scal); mu=scal[:ntr].mean(0); sd=scal[:ntr].std(0); sd[sd<1e-8]=1; scal=(scal-mu)/sd
 vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
 A=vec.fit_transform(texts[:ntr]); B=vec.transform(texts[ntr:])
 Ft=hstack([A,csr_matrix(scal[:ntr])],format='csr'); Fe=hstack([B,csr_matrix(scal[ntr:])],format='csr')
 y=train.is_correct.to_numpy(int); ye=judge.is_correct.to_numpy(int); groups=train.session_id.astype(str).to_numpy()
 oof=np.zeros(ntr); op=np.zeros(ntr); oc=np.zeros(ntr); directed=np.zeros((ntr,4)); ability=np.zeros((ntr,3))
 for f,(a,b) in enumerate(GroupKFold(n_splits=4).split(np.zeros(ntr),y,groups)):
  m=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Ft[a],y[a]); oof[b]=m.predict_proba(Ft[b])[:,1]
  pa,_,_=v183.objective_prior(train.iloc[a],train.iloc[a],2.0)
  pb,cb,_=v183.objective_prior(train.iloc[a],train.iloc[b],2.0); op[b]=pb; oc[b]=cb
  _,oi,W,cnt=v183.fit_graph(train.iloc[a].reset_index(drop=True),pa)
  mods=v186.make_modules(train.iloc[b].reset_index(drop=True),oof[b],pb,cb,oi,W)
  directed[b]=mods['directed']; ability[b]=mods['session_ability']
  print('OOF_FOLD',f,'ROWS',len(b),'EDGES',int((cnt>0).sum()))
 fm=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Ft,y); pe=fm.predict_proba(Fe)[:,1]
 pp,cc,_=v183.objective_prior(train,judge,2.0); ptrain,_,_=v183.objective_prior(train,train,2.0)
 _,oi,W,_=v183.fit_graph(train,ptrain); mods=v186.make_modules(judge,pe,pp,cc,oi,W)
 core_train=v186.base_features(oof,op,oc); core_eval=v186.base_features(pe,pp,cc)
 v184_train=np.column_stack([core_train,directed]); v184_eval=np.column_stack([core_eval,mods['directed']])
 pbase=predict(v184_train,v184_eval,y)
 pcand=predict(np.column_stack([v184_train,ability]),np.column_stack([v184_eval,mods['session_ability']]),y)
 bm=v186.metric(ye,pbase); cm=v186.metric(ye,pcand); delta=cm['logloss']-bm['logloss']; adelta=cm['auc']-bm['auc']
 boot=clustered_bootstrap(judge,ye,pbase,pcand)
 promote=delta<=-.0005 and boot['upper_95']<0 and adelta>=-.001
 result={'protocol':'V188_LARGE_FRESH_SEALED_SESSION_ABILITY_JUDGE','train_rows':ntr,'sealed_rows':len(judge),
  'excluded_prior_judge_sessions':len(forbidden),'frozen_baseline':'V184_DIRECTED_GEOMETRY_C0.1',
  'frozen_candidate':'V184_PLUS_SESSION_ABILITY_C0.1','baseline':bm,'candidate':cm,
  'delta_logloss':delta,'delta_auc':adelta,'clustered_bootstrap':boot,
  'decision':'SESSION_ABILITY_CONFIRMED__INTEGRATE' if promote else 'SESSION_ABILITY_NOT_CONFIRMED__KEEP_V184'}
 (OUT/'v188_results.json').write_text(json.dumps(result,indent=2))
 pd.DataFrame({'response_id':judge.response_id.astype(str),'session_id':judge.session_id.astype(str),'y':ye,
  'p_v184':pbase,'p_v184_session_ability':pcand}).to_csv(OUT/'v188_predictions.csv',index=False)
 print(json.dumps(result,indent=2))

if __name__=='__main__': main()
