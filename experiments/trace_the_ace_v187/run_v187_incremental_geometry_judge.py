#!/usr/bin/env python3
"""Frozen incremental judge: richer mastery modules versus V184 geometry itself."""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'trace_the_ace_v183'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'trace_the_ace_v186'))
import run_v183_mastery_geometry as v183
import run_v186_mastery_tournament as v186

OUT=Path('/workspace/trace-ace-results/v187'); OUT.mkdir(parents=True,exist_ok=True)
NTRAIN=9000; NJUDGE=800; TAGS=['V187_JUDGE_A','V187_JUDGE_B','V187_JUDGE_C']
# Frozen before V187 judges: the minimal V186 mechanism and its three finalists.
CANDIDATES={
 'minimal_session_ability':('directed','session_ability'),
 'minimal_session_support':('directed','session_ability','support_gate'),
 'compact_session_signed_support':('directed','session_ability','signed','support_gate'),
 'v186_finalist_second_order':('directed','factor_interact','second_order','session_ability','signed','support_gate'),
 'v186_finalist_uncertainty':('directed','factor_interact','session_ability','signed','support_gate','uncertainty'),
 'v186_finalist_lowrank':('directed','factor_interact','lowrank','session_ability','signed','support_gate'),
}

def take(frame,n,tag,forbidden):
 z=frame[~frame.session_id.isin(forbidden)]
 return set(v183.session_sample(z,n,tag))

def predict(train_x,eval_x,y,c=.1):
 m=LogisticRegression(C=c,solver='liblinear',max_iter=240).fit(train_x,y)
 return m.predict_proba(eval_x)[:,1]

def main():
 X=pd.read_csv(v183.FEAT); Y=pd.read_csv(v183.LAB)
 print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
 target='is_correct' if 'is_correct' in Y.columns else 'correct'
 Y=Y.rename(columns={target:'is_correct'})
 df=X.merge(Y,on='response_id',validate='one_to_one')
 used=set(); judges=[]
 for tag in TAGS:
  ss=take(df,NJUDGE,tag,used); used|=ss
  judges.append(df[df.session_id.isin(ss)].copy().reset_index(drop=True))
 pool=df[~df.session_id.isin(used)].copy(); ts=take(pool,NTRAIN,'V187_TRAIN',set())
 train=pool[pool.session_id.isin(ts)].copy().reset_index(drop=True)
 eval_all=pd.concat(judges,ignore_index=True); work=pd.concat([train,eval_all],ignore_index=True); ntr=len(train)
 print('TRAIN_ROWS',ntr,'JUDGE_ROWS',[len(z) for z in judges])
 cache={}; texts=[]; scalars=[]
 for k,r in enumerate(work.itertuples(index=False)):
  t,s=v183.build_row(str(r.session_id),str(r.learning_objective),cache); texts.append(t); scalars.append(s)
  if (k+1)%1000==0: print('FEATURE_ROWS',k+1)
 scalars=np.vstack(scalars); mu=scalars[:ntr].mean(0); sd=scalars[:ntr].std(0); sd[sd<1e-8]=1; scalars=(scalars-mu)/sd
 vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
 Xt=vec.fit_transform(texts[:ntr]); Xe=vec.transform(texts[ntr:])
 Ft=hstack([Xt,csr_matrix(scalars[:ntr])],format='csr'); Fe=hstack([Xe,csr_matrix(scalars[ntr:])],format='csr')
 y=train.is_correct.to_numpy(int); groups=train.session_id.astype(str).to_numpy(); gkf=GroupKFold(n_splits=4)
 oof=np.zeros(ntr); op=np.zeros(ntr); oc=np.zeros(ntr); chunks=None
 for f,(a,b) in enumerate(gkf.split(np.zeros(ntr),y,groups)):
  m=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Ft[a],y[a])
  oof[b]=m.predict_proba(Ft[b])[:,1]
  pa,_,_=v183.objective_prior(train.iloc[a],train.iloc[a],2.0)
  pb,cb,_=v183.objective_prior(train.iloc[a],train.iloc[b],2.0); op[b]=pb; oc[b]=cb
  _,oi,W,cnt=v183.fit_graph(train.iloc[a].reset_index(drop=True),pa)
  mods=v186.make_modules(train.iloc[b].reset_index(drop=True),oof[b],pb,cb,oi,W)
  if chunks is None: chunks={name:[] for name in mods}
  for name,values in mods.items(): chunks[name].append((b,values))
  print('OOF_FOLD',f,'ROWS',len(b),'EDGES',int((cnt>0).sum()))
 mod_oof={}
 for name,parts in chunks.items():
  M=np.zeros((ntr,parts[0][1].shape[1]))
  for idx,values in parts: M[idx]=values
  mod_oof[name]=M
 fm=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Ft,y)
 pe=fm.predict_proba(Fe)[:,1]
 pp,cc,_=v183.objective_prior(train,eval_all,2.0); ptrain,_,_=v183.objective_prior(train,train,2.0)
 _,oi,W,_=v183.fit_graph(train,ptrain); mod_eval=v186.make_modules(eval_all,pe,pp,cc,oi,W)
 A=v186.base_features(oof,op,oc); B=v186.base_features(pe,pp,cc)
 # Frozen V184 comparator: C=.1 meta model over core + directed geometry.
 At=np.column_stack([A,mod_oof['directed']]); Bt=np.column_stack([B,mod_eval['directed']])
 pbase=predict(At,Bt,y,.1); predictions={'v184_directed':pbase}
 for name,combo in CANDIDATES.items():
  extra=[m for m in combo if m!='directed']
  tr=np.column_stack([At]+[mod_oof[m] for m in extra]); ev=np.column_stack([Bt]+[mod_eval[m] for m in extra])
  predictions[name]=predict(tr,ev,y,.1)
 offsets=[]; pos=0
 for judge in judges: offsets.append((pos,pos+len(judge))); pos+=len(judge)
 ye=eval_all.is_correct.to_numpy(int); bm=v186.metric(ye,pbase); rows=[]
 for name,p in predictions.items():
  mm=v186.metric(ye,p); ds=[]; sms=[]
  for (lo,hi),judge in zip(offsets,judges):
   yy=judge.is_correct.to_numpy(int); sm=v186.metric(yy,p[lo:hi]); sb=v186.metric(yy,pbase[lo:hi])
   sms.append(sm); ds.append(sm['logloss']-sb['logloss'])
  rows.append({'name':name,'combo':['directed'] if name=='v184_directed' else list(CANDIDATES[name]),
   'metric':mm,'delta_vs_v184':mm['logloss']-bm['logloss'],'split_metrics':sms,
   'split_deltas_vs_v184':ds,'wins_vs_v184':int(sum(d<0 for d in ds)),'worst_split_delta':float(max(ds))})
 rows.sort(key=lambda r:r['metric']['logloss']); challengers=[r for r in rows if r['name']!='v184_directed']
 stable=[r for r in challengers if r['wins_vs_v184']==len(judges) and r['worst_split_delta']<0]
 winner=min(stable,key=lambda r:r['metric']['logloss']) if stable else min(challengers,key=lambda r:r['metric']['logloss'])
 promote=winner['wins_vs_v184']==len(judges) and winner['delta_vs_v184']<=-.001
 result={'protocol':'V187_FROZEN_INCREMENTAL_MASTERY_GEOMETRY_JUDGE','train_rows':ntr,'judge_rows':[len(z) for z in judges],
  'frozen_baseline':'V184_DIRECTED_GEOMETRY_C0.1','baseline_metric':bm,'candidates':rows,'winner':winner,
  'decision':'INCREMENTAL_WINNER__INTEGRATE' if promote else 'NO_MATERIAL_INCREMENT__KEEP_V184'}
 (OUT/'v187_results.json').write_text(json.dumps(result,indent=2))
 pd.DataFrame({'response_id':eval_all.response_id.astype(str),'y':ye,**predictions}).to_csv(OUT/'v187_predictions.csv',index=False)
 print(json.dumps(result,indent=2))

if __name__=='__main__': main()
