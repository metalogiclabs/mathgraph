#!/usr/bin/env python3
import json, pickle, re, sys, zipfile, warnings, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
import joblib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'trace_the_ace_v183'))
import run_v183_mastery_geometry as v183

WS=Path('/workspace')
FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; TR=WS/'trace_the_ace/transcripts_extracted'
CACHE=WS/'trace-ace-work/v185/feature_cache.pkl'
OUT=WS/'trace-ace-results/v191'; WORK=WS/'trace-ace-work/v191'; PKG=WORK/'package'; ASSET=PKG/'v191_assets.joblib'
EPS=1e-6

def logit(p):
 p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def metric(y,p):
 p=np.clip(np.asarray(p,float),EPS,1-EPS); return {'logloss':float(log_loss(y,p)),'auc':float(roc_auc_score(y,p))}
def objective_prior(train,query,alpha=2.0):
 gm=float(train.is_correct.mean()); st=train.groupby('learning_objective').is_correct.agg(['sum','count']); p=[]; c=[]
 for o in query.learning_objective.astype(str):
  if o in st.index: s=float(st.loc[o,'sum']); n=float(st.loc[o,'count'])
  else: s=0.; n=0.
  p.append((s+alpha*gm)/(n+alpha)); c.append(n)
 return np.asarray(p),np.asarray(c),gm

def transcript_frame(sid,cache):
 if sid in cache: return cache[sid]
 p=TR/f'{sid}.csv'; xs=[] if p.exists() else list(TR.glob(f'**/{sid}.csv')); p=p if p.exists() else (xs[0] if xs else None)
 z=pd.read_csv(p) if p else pd.DataFrame(columns=['role','content','timestamp'])
 if 'timestamp' in z.columns:
  try: z=z.assign(_ts=pd.to_timedelta(z.timestamp,errors='coerce')).sort_values('_ts',kind='stable')
  except Exception: pass
 cache[sid]=z.reset_index(drop=True); return cache[sid]

def session_text(sid,cache):
 z=transcript_frame(sid,cache); parts=[]
 for r in z.itertuples(index=False):
  role=str(getattr(r,'role','')).lower(); text=str(getattr(r,'content','')).lower()
  if 'student' in role: pref='STUDENT'
  elif 'tutor' in role: pref='TUTOR'
  else: continue
  parts.append(pref+': '+text)
 return ' '.join(parts)

def meta_features(pt,ps,pp,cc):
 lt,ls,lp=logit(pt),logit(ps),logit(pp); s=np.log1p(cc)
 return np.column_stack([lt,lp,s,lt*s,lp*s,ls,ls*lt,ls*lp,ls*s,np.abs(lt-ls)])

def main():
 OUT.mkdir(parents=True,exist_ok=True); WORK.mkdir(parents=True,exist_ok=True); PKG.mkdir(parents=True,exist_ok=True)
 X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
 target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
 df=X.merge(Y,on='response_id',validate='one_to_one').reset_index(drop=True)
 print('ROWS',len(df),'SESSIONS',df.session_id.nunique(),'OBJECTIVES',df.learning_objective.nunique())
 y=df.is_correct.to_numpy(int); groups=df.session_id.astype(str).to_numpy(); n=len(df)

 # Reuse the exact V179/V185 target-conditioned representation.
 co=pickle.loads(CACHE.read_bytes())
 texts=[co['texts'][str(r)] for r in df.response_id]; scal=np.vstack([co['scalars'][str(r)] for r in df.response_id]).astype(float)
 mu=scal.mean(0); sd=scal.std(0); sd[sd<1e-8]=1; sz=(scal-mu)/sd
 tv=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
 TX=tv.fit_transform(texts); TF=hstack([TX,csr_matrix(sz)],format='csr')

 # Legal latent-ability channel: only the current sample's own transcript, independent of other test rows.
 tc={}; sess_ids=df.session_id.astype(str).drop_duplicates().tolist(); smap={s:session_text(s,tc) for s in sess_ids}
 stxt=[smap[s] for s in df.session_id.astype(str)]
 sv=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=25000,strip_accents='unicode')
 SX=sv.fit_transform(stxt)

 gkf=GroupKFold(n_splits=4); pt=np.zeros(n); ps=np.zeros(n); pp=np.zeros(n); cc=np.zeros(n); fold_id=np.full(n,-1)
 for f,(a,b) in enumerate(gkf.split(np.zeros(n),y,groups)):
  tm=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260828).fit(TF[a],y[a]); pt[b]=tm.predict_proba(TF[b])[:,1]
  sm=LogisticRegression(C=.20,max_iter=180,solver='liblinear',random_state=20260828).fit(SX[a],y[a]); ps[b]=sm.predict_proba(SX[b])[:,1]
  pb,cb,_=objective_prior(df.iloc[a],df.iloc[b],2.0); pp[b]=pb; cc[b]=cb; fold_id[b]=f
  print('BASE_FOLD',f,'ROWS',len(b),flush=True)

 # Cross-fitted second level; no meta row is scored by a meta model trained on that row.
 candidates={}
 baseA=np.column_stack([logit(pt),logit(pp),np.log1p(cc),logit(pt)*np.log1p(cc),logit(pp)*np.log1p(cc)])
 fullA=meta_features(pt,ps,pp,cc)
 for name,A,C in [('v179_control',baseA,.25),('session_mastery_C003',fullA,.03),('session_mastery_C01',fullA,.1),('session_mastery_C025',fullA,.25),('session_mastery_C1',fullA,1.0)]:
  pred=np.zeros(n)
  for f in range(4):
   a=np.where(fold_id!=f)[0]; b=np.where(fold_id==f)[0]
   m=LogisticRegression(C=C,solver='liblinear',max_iter=240).fit(A[a],y[a]); pred[b]=m.predict_proba(A[b])[:,1]
  candidates[name]={'metric':metric(y,pred),'pred':pred,'C':C}
 # conservative direct blends as independent checks
 for w in [.10,.20,.30,.40]:
  q=np.clip((1-w)*candidates['v179_control']['pred']+w*ps,EPS,1-EPS); candidates[f'blend_session_{w}']={'metric':metric(y,q),'pred':q,'C':None}
 ref=candidates['v179_control']['metric']['logloss']; ranked=sorted(candidates.items(),key=lambda kv:kv[1]['metric']['logloss']); winner_name,winner=ranked[0]
 result={'protocol':'V191_INDEPENDENT_TRANSCRIPT_MASTERY','rows':n,'sessions':int(df.session_id.nunique()),'reference':candidates['v179_control']['metric'],'ranking':[{'name':k,**v['metric'],'delta_vs_v179':v['metric']['logloss']-ref} for k,v in ranked],'winner':winner_name,'winner_delta_vs_v179':winner['metric']['logloss']-ref}
 print(json.dumps(result,indent=2))

 # Fit full production models and selected meta.
 tmodel=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260828).fit(TF,y)
 smodel=LogisticRegression(C=.20,max_iter=180,solver='liblinear',random_state=20260828).fit(SX,y)
 pfull,cfull,gm=objective_prior(df,df,2.0); stats=df.groupby('learning_objective').is_correct.agg(['sum','count']); prior_stats={str(o):(float(r['sum']),float(r['count'])) for o,r in stats.iterrows()}
 if winner_name.startswith('session_mastery_'):
  C=winner['C']; final_meta=LogisticRegression(C=C,solver='liblinear',max_iter=240).fit(fullA,y); mode='meta'
 elif winner_name.startswith('blend_session_'):
  final_meta=None; mode='blend'; C=float(winner_name.rsplit('_',1)[1])
 else:
  final_meta=LogisticRegression(C=.25,solver='liblinear',max_iter=240).fit(baseA,y); mode='control'; C=.25
 assets={'version':'V191_INDEPENDENT_TRANSCRIPT_MASTERY','target_vectorizer':tv,'target_mu':mu,'target_sd':sd,'target_model':tmodel,'session_vectorizer':sv,'session_model':smodel,'meta_model':final_meta,'mode':mode,'winner':winner_name,'winner_param':C,'prior_stats':prior_stats,'global_mean':float(gm),'prior_alpha':2.0,'train_rows':n}
 joblib.dump(assets,ASSET,compress=3)

 runtime=r'''#!/usr/bin/env python3
import warnings; warnings.filterwarnings('ignore')
import re, joblib
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
BASE=Path(__file__).resolve().parent; A=joblib.load(BASE/'v191_assets.joblib'); EPS=1e-6
STOP=set('the a an and or of to in on for with by from is are be being been this that these those how what when where why which can could would should do does did use using find calculate work solve understand know given student students'.split())
UNC=['not sure','dont know','don t know','idk','confused','maybe','i think','guess','unsure','no idea']; POS=['got it','understand','makes sense','i see','yes','correct','right','okay','ok','done']; SELF=['actually','wait','i mean','sorry','let me redo','made a mistake','my mistake']; TCONF=['correct','well done','exactly','that is right','that s right','yes','good job','great']; TCORR=['not quite','incorrect','check','try again','mistake','not correct','wrong','rethink']; THINT=['hint','remember','think about','consider','because','let me','try to','notice']
def toks(s): return [x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>1 and x not in STOP]
def cp(t,arr): return sum(t.count(x) for x in arr)
def loadz(sid,trdir):
 p=trdir/f'{sid}.csv'; xs=[] if p.exists() else list(trdir.glob(f'**/{sid}.csv')); p=p if p.exists() else (xs[0] if xs else None); z=pd.read_csv(p) if p else pd.DataFrame(columns=['role','content','timestamp'])
 if 'timestamp' in z.columns:
  try: z=z.assign(_ts=pd.to_timedelta(z.timestamp,errors='coerce')).sort_values('_ts',kind='stable')
  except Exception: pass
 return z.reset_index(drop=True)
def target_row(z,obj):
 ot=set(toks(obj)); scores=[]
 for i,r in z.iterrows():
  tt=set(toks(r.get('content',''))); ov=len(ot&tt); jac=ov/max(1,len(ot|tt)); scores.append((2*ov+jac,i))
 top=[i for sc,i in sorted(scores,reverse=True)[:6] if sc>0] or list(range(max(0,len(z)-6),len(z))); keep=set()
 for i in top:
  for j in range(max(0,i-1),min(len(z),i+2)): keep.add(j)
 ordered=sorted(keep); parts=[]; rs=[]; rt=[]
 for i in ordered:
  r=z.iloc[i]; role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); parts.append(('STUDENT' if 'student' in role else 'TUTOR')+': '+text); ov=len(ot&set(toks(text)))/max(1,len(ot)); (rs if 'student' in role else rt).append((i,text,ov))
 joined=' '.join(x[1] for x in rs); tj=' '.join(x[1] for x in rt); last=rs[-1][1] if rs else ''; first=rs[0][1] if rs else ''; ss=lambda t: cp(t,POS)-cp(t,UNC)-.5*cp(t,SELF); maxsc=max([s for s,i in scores],default=0); lastpos=max(ordered)/max(1,len(z)-1) if ordered else 0
 v=[len(z),len(ordered),len(rs),len(rt),maxsc,lastpos,max([x[2] for x in rs],default=0),max([x[2] for x in rt],default=0),cp(joined,UNC),cp(joined,POS),cp(joined,SELF),cp(tj,TCONF),cp(tj,TCORR),cp(tj,THINT),len(re.findall(r'\d',joined)),len(re.findall(r'[=+\-*/%]',joined)),ss(last),ss(last)-ss(first),1.0 if top and max(top)>=len(z)-3 else 0.0]
 return 'OBJECTIVE: '+str(obj)+' [KEY_MOMENTS] '+' '.join(parts),np.asarray(v,float)
def session_text(z):
 p=[]
 for _,r in z.iterrows():
  role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower()
  if 'student' in role: p.append('STUDENT: '+text)
  elif 'tutor' in role: p.append('TUTOR: '+text)
 return ' '.join(p)
def lg(p): p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def mf(pt,ps,pp,cc):
 lt,ls,lp=lg(pt),lg(ps),lg(pp); s=np.log1p(cc); return np.column_stack([lt,lp,s,lt*s,lp*s,ls,ls*lt,ls*lp,ls*s,np.abs(lt-ls)])
def main():
 data=Path('/code_execution/data'); X=pd.read_csv(data/'test_features.csv'); fmt=pd.read_csv(data/'submission_format.csv'); tr=data/'test_transcripts'
 if list(fmt.columns)!=['response_id','probability']: raise RuntimeError('submission_format contract changed')
 texts=[]; sc=[]; sess=[]
 # Each row is computed only from that row plus its own session transcript. No other test row enters its features.
 for r in X.itertuples(index=False):
  z=loadz(str(r.session_id),tr); t,v=target_row(z,str(r.learning_objective)); texts.append(t); sc.append(v); sess.append(session_text(z))
 sc=(np.vstack(sc)-A['target_mu'])/A['target_sd']; M=hstack([A['target_vectorizer'].transform(texts),csr_matrix(sc)],format='csr'); pt=A['target_model'].predict_proba(M)[:,1]; ps=A['session_model'].predict_proba(A['session_vectorizer'].transform(sess))[:,1]
 pp=[]; cc=[]; gm=A['global_mean']; al=A['prior_alpha']
 for o in X.learning_objective.astype(str):
  s,n=A['prior_stats'].get(o,(0.,0.)); pp.append((s+al*gm)/(n+al)); cc.append(n)
 pp=np.asarray(pp); cc=np.asarray(cc)
 if A['mode']=='meta': pred=A['meta_model'].predict_proba(mf(pt,ps,pp,cc))[:,1]
 elif A['mode']=='blend': pred=(1-A['winner_param'])*pt+A['winner_param']*ps
 else:
  B=np.column_stack([lg(pt),lg(pp),np.log1p(cc),lg(pt)*np.log1p(cc),lg(pp)*np.log1p(cc)]); pred=A['meta_model'].predict_proba(B)[:,1]
 by={str(r):float(p) for r,p in zip(X.response_id,pred)}
 if len(by)!=len(X): raise RuntimeError('duplicate response_id in test_features')
 ids=fmt.response_id.astype(str).tolist(); miss=[r for r in ids if r not in by]
 if miss: raise RuntimeError(f'missing response ids: {miss[:5]}')
 out=fmt.copy(); out['probability']=[np.clip(by[r],1e-6,1-1e-6) for r in ids]
 if not np.isfinite(out.probability.to_numpy(float)).all(): raise RuntimeError('nonfinite probabilities')
 out.to_csv('/code_execution/submission.csv',index=False)
if __name__=='__main__': main()
'''
 (PKG/'main.py').write_text(runtime)
 zip_path=OUT/'trace_ace_v191_independent_transcript_mastery_submission.zip'
 with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z: z.write(PKG/'main.py','main.py'); z.write(ASSET,'v191_assets.joblib')
 result.update({'asset_bytes':ASSET.stat().st_size,'zip_bytes':zip_path.stat().st_size,'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'decision':'BUILD_OFFICIAL_RUNTIME_TEST'})
 (OUT/'v191_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
