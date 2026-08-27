#!/usr/bin/env python3
import json, pickle, re, sys, zipfile, warnings, hashlib
from pathlib import Path
from itertools import product
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
OUT=WS/'trace-ace-results/v192'; WORK=WS/'trace-ace-work/v192'; PKG=WORK/'package'; ASSET=PKG/'v192_assets.joblib'
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

def role_text(z,role_filter=None):
 parts=[]
 for r in z.itertuples(index=False):
  role=str(getattr(r,'role','')).lower(); text=str(getattr(r,'content','')).lower()
  if role_filter=='student' and 'student' not in role: continue
  if role_filter=='tutor' and 'tutor' not in role: continue
  if role_filter is None:
   if 'student' in role: pref='STUDENT'
   elif 'tutor' in role: pref='TUTOR'
   else: continue
   parts.append(pref+': '+text)
  else: parts.append(text)
 return ' '.join(parts)

def outcome_scalars(z,obj):
 ot=set(v183.toks(obj)); stu=[]; tut=[]; allrows=[]
 for i,r in z.iterrows():
  role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); tt=set(v183.toks(text)); ov=len(ot&tt)/max(1,len(ot))
  rec=(i,text,ov)
  if 'student' in role: stu.append(rec)
  elif 'tutor' in role: tut.append(rec)
  allrows.append(rec)
 n=max(len(z),1)
 def cp(t,arr): return sum(t.count(x) for x in arr)
 sjoin=' '.join(x[1] for x in stu); tjoin=' '.join(x[1] for x in tut)
 late=[x for x in stu if x[0]>=0.65*n]; late_text=' '.join(x[1] for x in late)
 correct=['correct','well done','exactly','right','good','great','excellent','perfect']
 corr=['incorrect','wrong','not quite','try again','check','mistake']
 unc=['not sure','dont know','don t know','idk','confused','maybe','guess','unsure','no idea']
 selfc=['actually','wait','i mean','sorry','redo','mistake']
 vals=[
  len(z),len(stu),len(tut),
  cp(sjoin,unc),cp(sjoin,selfc),cp(tjoin,correct),cp(tjoin,corr),
  cp(late_text,unc),cp(late_text,selfc),
  np.mean([x[2] for x in stu]) if stu else 0.,np.max([x[2] for x in stu]) if stu else 0.,
  np.mean([x[2] for x in tut]) if tut else 0.,np.max([x[2] for x in tut]) if tut else 0.,
  np.mean([len(x[1].split()) for x in stu]) if stu else 0.,
  np.mean([len(x[1].split()) for x in tut]) if tut else 0.,
  len(late), len(re.findall(r'\d',sjoin)), len(re.findall(r'[=+\-*/%]',sjoin)),
 ]
 return np.asarray(vals,float)

def meta_features(pt,ps,pstu,ptut,pp,cc,osc):
 lt,ls,lu,lv,lp=map(logit,[pt,ps,pstu,ptut,pp]); c=np.log1p(cc)
 core=np.column_stack([lt,lp,c,lt*c,lp*c,ls,lu,lv,ls*lt,lu*lt,lv*lt,ls*lp,lu*lp,np.abs(lt-ls),np.abs(lt-lu),np.abs(lt-lv)])
 return np.column_stack([core,osc])

def main():
 OUT.mkdir(parents=True,exist_ok=True); WORK.mkdir(parents=True,exist_ok=True); PKG.mkdir(parents=True,exist_ok=True)
 X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
 df=X.merge(Y,on='response_id',validate='one_to_one').reset_index(drop=True); y=df.is_correct.to_numpy(int); groups=df.session_id.astype(str).to_numpy(); n=len(df)
 co=pickle.loads(CACHE.read_bytes()); texts=[co['texts'][str(r)] for r in df.response_id]; scal=np.vstack([co['scalars'][str(r)] for r in df.response_id]).astype(float)
 mu=scal.mean(0); sd=scal.std(0); sd[sd<1e-8]=1; sz=(scal-mu)/sd
 tv=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode'); TX=tv.fit_transform(texts); TF=hstack([TX,csr_matrix(sz)],format='csr')
 tc={}; sess_ids=df.session_id.astype(str).drop_duplicates().tolist(); frames={s:transcript_frame(s,tc) for s in sess_ids}
 alltxt=[role_text(frames[s]) for s in df.session_id.astype(str)]; stutxt=[role_text(frames[s],'student') for s in df.session_id.astype(str)]; tutt=[role_text(frames[s],'tutor') for s in df.session_id.astype(str)]
 osv=np.vstack([outcome_scalars(frames[str(r.session_id)],str(r.learning_objective)) for r in df.itertuples(index=False)]); om=osv.mean(0); od=osv.std(0); od[od<1e-8]=1; osz=(osv-om)/od
 av=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=26000,strip_accents='unicode'); AX=av.fit_transform(alltxt)
 uv=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=22000,strip_accents='unicode'); UX=uv.fit_transform(stutxt)
 vv=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=18000,strip_accents='unicode'); VX=vv.fit_transform(tutt)
 gkf=GroupKFold(n_splits=5); pt=np.zeros(n); ps=np.zeros(n); pu=np.zeros(n); pv=np.zeros(n); pp=np.zeros(n); cc=np.zeros(n); fold=np.full(n,-1)
 for f,(a,b) in enumerate(gkf.split(np.zeros(n),y,groups)):
  pt[b]=LogisticRegression(C=.35,max_iter=220,solver='liblinear',random_state=20260828).fit(TF[a],y[a]).predict_proba(TF[b])[:,1]
  ps[b]=LogisticRegression(C=.20,max_iter=220,solver='liblinear',random_state=20260828).fit(AX[a],y[a]).predict_proba(AX[b])[:,1]
  pu[b]=LogisticRegression(C=.15,max_iter=220,solver='liblinear',random_state=20260828).fit(UX[a],y[a]).predict_proba(UX[b])[:,1]
  pv[b]=LogisticRegression(C=.10,max_iter=220,solver='liblinear',random_state=20260828).fit(VX[a],y[a]).predict_proba(VX[b])[:,1]
  pb,cb,_=objective_prior(df.iloc[a],df.iloc[b],2.0); pp[b]=pb; cc[b]=cb; fold[b]=f
 A=meta_features(pt,ps,pu,pv,pp,cc,osz)
 base=np.column_stack([logit(pt),logit(pp),np.log1p(cc),logit(pt)*np.log1p(cc),logit(pp)*np.log1p(cc),logit(ps),logit(ps)*logit(pt),logit(ps)*logit(pp),logit(ps)*np.log1p(cc),np.abs(logit(pt)-logit(ps))])
 def crossfit(M,C):
  q=np.zeros(n)
  for f in range(5):
   a=np.where(fold!=f)[0]; b=np.where(fold==f)[0]; q[b]=LogisticRegression(C=C,solver='liblinear',max_iter=300).fit(M[a],y[a]).predict_proba(M[b])[:,1]
  return q
 refp=crossfit(base,.1); ref=metric(y,refp)
 candidates=[]
 for C in [.01,.03,.05,.08,.1,.15,.25]:
  q=crossfit(A,C); m=metric(y,q); candidates.append({'name':f'full_C{C}','C':C,'metric':m,'delta':m['logloss']-ref['logloss'],'pred':q})
 for wt,ws,wu,wv in [(0.60,0.20,0.15,0.05),(0.55,0.20,0.20,0.05),(0.50,0.25,0.20,0.05),(0.55,0.25,0.10,0.10)]:
  q=np.clip(wt*pt+ws*ps+wu*pu+wv*pv,EPS,1-EPS); m=metric(y,q); candidates.append({'name':f'blend_{wt}_{ws}_{wu}_{wv}','C':None,'metric':m,'delta':m['logloss']-ref['logloss'],'pred':q,'weights':[wt,ws,wu,wv]})
 candidates.sort(key=lambda r:r['metric']['logloss']); winner=candidates[0]
 # Stability gate: winner must improve ref on >=4/5 held-out folds and pooled by at least 0.001.
 splits=[]
 for f in range(5):
  b=np.where(fold==f)[0]; splits.append(float(log_loss(y[b],winner['pred'][b])-log_loss(y[b],refp[b])))
 promote=(winner['delta']<=-0.001 and sum(d<0 for d in splits)>=4)
 if not promote:
  winner={'name':'v191_control','C':.1,'metric':ref,'delta':0.0,'pred':refp}; mode='control'; splits=[0.0]*5
 else: mode='meta' if winner['name'].startswith('full_') else 'blend'
 result={'protocol':'V192_FINAL_INDEPENDENT_TOURNAMENT','rows':n,'reference_v191':ref,'ranking':[{'name':r['name'],**r['metric'],'delta_vs_v191':r['delta']} for r in candidates],'winner':winner['name'],'winner_metric':winner['metric'],'winner_delta_vs_v191':winner['delta'],'split_deltas':splits,'promote':promote}
 (OUT/'v192_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
 # Fit full models.
 tmodel=LogisticRegression(C=.35,max_iter=220,solver='liblinear',random_state=20260828).fit(TF,y); smodel=LogisticRegression(C=.20,max_iter=220,solver='liblinear',random_state=20260828).fit(AX,y); umodel=LogisticRegression(C=.15,max_iter=220,solver='liblinear',random_state=20260828).fit(UX,y); vmodel=LogisticRegression(C=.10,max_iter=220,solver='liblinear',random_state=20260828).fit(VX,y)
 stats=df.groupby('learning_objective').is_correct.agg(['sum','count']); prior_stats={str(o):(float(r['sum']),float(r['count'])) for o,r in stats.iterrows()}; gm=float(y.mean())
 if mode=='meta': final_meta=LogisticRegression(C=winner['C'],solver='liblinear',max_iter=300).fit(A,y); winparam=winner['C']
 elif mode=='blend': final_meta=None; winparam=winner['weights']
 else: final_meta=LogisticRegression(C=.1,solver='liblinear',max_iter=300).fit(base,y); winparam=.1
 assets={'version':'V192_FINAL_INDEPENDENT','target_vectorizer':tv,'target_mu':mu,'target_sd':sd,'target_model':tmodel,'all_vectorizer':av,'all_model':smodel,'student_vectorizer':uv,'student_model':umodel,'tutor_vectorizer':vv,'tutor_model':vmodel,'outcome_mu':om,'outcome_sd':od,'meta_model':final_meta,'mode':mode,'winner':winner['name'],'winner_param':winparam,'prior_stats':prior_stats,'global_mean':gm,'prior_alpha':2.0,'train_rows':n}
 joblib.dump(assets,ASSET,compress=3)
 runtime=r'''#!/usr/bin/env python3
import warnings; warnings.filterwarnings('ignore')
import re, joblib
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
BASE=Path(__file__).resolve().parent; A=joblib.load(BASE/'v192_assets.joblib'); EPS=1e-6
STOP=set('the a an and or of to in on for with by from is are be being been this that these those how what when where why which can could would should do does did use using find calculate work solve understand know given student students'.split())
def toks(s): return [x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>1 and x not in STOP]
def loadz(sid,tr):
 p=tr/f'{sid}.csv'; z=pd.read_csv(p) if p.exists() else pd.DataFrame(columns=['role','content','timestamp']);
 if 'timestamp' in z.columns:
  try: z=z.assign(_ts=pd.to_timedelta(z.timestamp,errors='coerce')).sort_values('_ts',kind='stable')
  except Exception: pass
 return z.reset_index(drop=True)
def role_text(z,rf=None):
 q=[]
 for _,r in z.iterrows():
  role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower()
  if rf=='student' and 'student' not in role: continue
  if rf=='tutor' and 'tutor' not in role: continue
  if rf is None:
   if 'student' in role: q.append('STUDENT: '+text)
   elif 'tutor' in role: q.append('TUTOR: '+text)
  else: q.append(text)
 return ' '.join(q)
def target_row(z,obj):
 ot=set(toks(obj)); scores=[]
 for i,r in z.iterrows():
  tt=set(toks(r.get('content',''))); ov=len(ot&tt); jac=ov/max(1,len(ot|tt)); scores.append((2*ov+jac,i))
 top=[i for sc,i in sorted(scores,reverse=True)[:6] if sc>0] or list(range(max(0,len(z)-6),len(z))); keep=set()
 for i in top:
  for j in range(max(0,i-1),min(len(z),i+2)): keep.add(j)
 ordered=sorted(keep); parts=[]; rs=[]; rt=[]
 UNC=['not sure','dont know','don t know','idk','confused','maybe','i think','guess','unsure','no idea']; POS=['got it','understand','makes sense','i see','yes','correct','right','okay','ok','done']; SELF=['actually','wait','i mean','sorry','let me redo','made a mistake','my mistake']; TCONF=['correct','well done','exactly','that is right','that s right','yes','good job','great']; TCORR=['not quite','incorrect','check','try again','mistake','not correct','wrong','rethink']; THINT=['hint','remember','think about','consider','because','let me','try to','notice']; cp=lambda t,a:sum(t.count(x) for x in a)
 for i in ordered:
  r=z.iloc[i]; role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); parts.append(('STUDENT' if 'student' in role else 'TUTOR')+': '+text); ov=len(ot&set(toks(text)))/max(1,len(ot)); (rs if 'student' in role else rt).append((i,text,ov))
 joined=' '.join(x[1] for x in rs); tj=' '.join(x[1] for x in rt); last=rs[-1][1] if rs else ''; first=rs[0][1] if rs else ''; ss=lambda t:cp(t,POS)-cp(t,UNC)-.5*cp(t,SELF); maxsc=max([s for s,i in scores],default=0); lastpos=max(ordered)/max(1,len(z)-1) if ordered else 0
 v=[len(z),len(ordered),len(rs),len(rt),maxsc,lastpos,max([x[2] for x in rs],default=0),max([x[2] for x in rt],default=0),cp(joined,UNC),cp(joined,POS),cp(joined,SELF),cp(tj,TCONF),cp(tj,TCORR),cp(tj,THINT),len(re.findall(r'\d',joined)),len(re.findall(r'[=+\-*/%]',joined)),ss(last),ss(last)-ss(first),1.0 if top and max(top)>=len(z)-3 else 0.0]
 return 'OBJECTIVE: '+str(obj)+' [KEY_MOMENTS] '+' '.join(parts),np.asarray(v,float)
def oscal(z,obj):
 ot=set(toks(obj)); stu=[]; tut=[]; n=max(len(z),1)
 for i,r in z.iterrows():
  role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); ov=len(ot&set(toks(text)))/max(1,len(ot)); rec=(i,text,ov)
  if 'student' in role: stu.append(rec)
  elif 'tutor' in role: tut.append(rec)
 cp=lambda t,a:sum(t.count(x) for x in a); sj=' '.join(x[1] for x in stu); tj=' '.join(x[1] for x in tut); late=' '.join(x[1] for x in stu if x[0]>=.65*n); cor=['correct','well done','exactly','right','good','great','excellent','perfect']; bad=['incorrect','wrong','not quite','try again','check','mistake']; unc=['not sure','dont know','don t know','idk','confused','maybe','guess','unsure','no idea']; selfc=['actually','wait','i mean','sorry','redo','mistake']
 return np.asarray([len(z),len(stu),len(tut),cp(sj,unc),cp(sj,selfc),cp(tj,cor),cp(tj,bad),cp(late,unc),cp(late,selfc),np.mean([x[2] for x in stu]) if stu else 0.,np.max([x[2] for x in stu]) if stu else 0.,np.mean([x[2] for x in tut]) if tut else 0.,np.max([x[2] for x in tut]) if tut else 0.,np.mean([len(x[1].split()) for x in stu]) if stu else 0.,np.mean([len(x[1].split()) for x in tut]) if tut else 0.,sum(x[0]>=.65*n for x in stu),len(re.findall(r'\d',sj)),len(re.findall(r'[=+\-*/%]',sj))],float)
def lg(p): p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def main():
 data=Path('/code_execution/data'); X=pd.read_csv(data/'test_features.csv'); fmt=pd.read_csv(data/'submission_format.csv'); tr=data/'test_transcripts'; assert list(fmt.columns)==['response_id','probability']
 T=[]; S=[]; U=[]; V=[]; O=[]
 for r in X.itertuples(index=False):
  z=loadz(str(r.session_id),tr); t,s=target_row(z,str(r.learning_objective)); T.append(t); S.append(s); U.append(role_text(z)); V.append(role_text(z,'student')); O.append((role_text(z,'tutor'),oscal(z,str(r.learning_objective))))
 sz=(np.vstack(S)-A['target_mu'])/A['target_sd']; pt=A['target_model'].predict_proba(hstack([A['target_vectorizer'].transform(T),csr_matrix(sz)],format='csr'))[:,1]; ps=A['all_model'].predict_proba(A['all_vectorizer'].transform(U))[:,1]; pu=A['student_model'].predict_proba(A['student_vectorizer'].transform(V))[:,1]; pv=A['tutor_model'].predict_proba(A['tutor_vectorizer'].transform([x[0] for x in O]))[:,1]; oz=(np.vstack([x[1] for x in O])-A['outcome_mu'])/A['outcome_sd']
 pp=[]; cc=[]; gm=A['global_mean']; al=A['prior_alpha']
 for o in X.learning_objective.astype(str): s,n=A['prior_stats'].get(o,(0.,0.)); pp.append((s+al*gm)/(n+al)); cc.append(n)
 pp=np.asarray(pp); cc=np.asarray(cc); lt,ls,lu,lv,lp=map(lg,[pt,ps,pu,pv,pp]); c=np.log1p(cc)
 full=np.column_stack([lt,lp,c,lt*c,lp*c,ls,lu,lv,ls*lt,lu*lt,lv*lt,ls*lp,lu*lp,np.abs(lt-ls),np.abs(lt-lu),np.abs(lt-lv),oz])
 if A['mode']=='meta': pred=A['meta_model'].predict_proba(full)[:,1]
 elif A['mode']=='blend': w=A['winner_param']; pred=w[0]*pt+w[1]*ps+w[2]*pu+w[3]*pv
 else:
  base=np.column_stack([lt,lp,c,lt*c,lp*c,ls,ls*lt,ls*lp,ls*c,np.abs(lt-ls)]); pred=A['meta_model'].predict_proba(base)[:,1]
 by={str(r):float(p) for r,p in zip(X.response_id,pred)}; ids=fmt.response_id.astype(str).tolist(); miss=[r for r in ids if r not in by];
 if miss: raise RuntimeError(f'missing ids {miss[:5]}')
 out=fmt.copy(); out['probability']=[float(np.clip(by[r],1e-6,1-1e-6)) for r in ids]; out.to_csv('/code_execution/submission.csv',index=False)
if __name__=='__main__': main()
'''
 (PKG/'main.py').write_text(runtime); zip_path=OUT/'trace_ace_v192_final_independent_submission.zip'
 with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z: z.write(PKG/'main.py','main.py'); z.write(ASSET,'v192_assets.joblib')
 result.update({'package_sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'package_bytes':zip_path.stat().st_size}); (OUT/'v192_results.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__': main()
