#!/usr/bin/env python3
import json,pickle,sys,warnings
from pathlib import Path
import numpy as np,pandas as pd
from scipy.sparse import hstack,csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,roc_auc_score
warnings.filterwarnings('ignore')
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'experiments'/'trace_the_ace_v192'))
import run_v192_final_independent_tournament as v
WS=Path('/workspace'); FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; CACHE=WS/'trace-ace-work/v185/feature_cache.pkl'; OUT=WS/'trace-ace-results/v193'; EPS=1e-6

def L(p):
 p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def M(y,p): return {'logloss':float(log_loss(y,p)),'auc':float(roc_auc_score(y,p))}
def fit_text(texts,scal,y,b,c,t,C,maxf):
 mu=scal[b].mean(0); sd=scal[b].std(0); sd[sd<1e-8]=1
 z=(scal-mu)/sd
 vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=maxf,strip_accents='unicode')
 xb=vec.fit_transform([texts[i] for i in b]); xc=vec.transform([texts[i] for i in c]); xt=vec.transform([texts[i] for i in t])
 xb=hstack([xb,csr_matrix(z[b])],format='csr'); xc=hstack([xc,csr_matrix(z[c])],format='csr'); xt=hstack([xt,csr_matrix(z[t])],format='csr')
 mod=LogisticRegression(C=C,max_iter=220,solver='liblinear',random_state=20260828).fit(xb,y[b])
 return mod.predict_proba(xc)[:,1],mod.predict_proba(xt)[:,1]
def fit_plain(texts,y,b,c,t,C,maxf):
 vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=maxf,strip_accents='unicode')
 xb=vec.fit_transform([texts[i] for i in b]); xc=vec.transform([texts[i] for i in c]); xt=vec.transform([texts[i] for i in t])
 mod=LogisticRegression(C=C,max_iter=220,solver='liblinear',random_state=20260828).fit(xb,y[b])
 return mod.predict_proba(xc)[:,1],mod.predict_proba(xt)[:,1]
def base(pt,ps,pp,cc):
 lt,ls,lp=L(pt),L(ps),L(pp); q=np.log1p(cc)
 return np.column_stack([lt,lp,q,lt*q,lp*q,ls,ls*lt,ls*lp,ls*q,np.abs(lt-ls)])
def full(pt,ps,pu,pv,pp,cc,osz): return v.meta_features(pt,ps,pu,pv,pp,cc,osz)
def geom(A,ps,objs,vocab):
 mp={o:j for j,o in enumerate(vocab)}; n=len(objs); k=len(vocab); oh=np.zeros((n,k),np.float32)
 for i,o in enumerate(objs):
  j=mp.get(str(o));
  if j is not None: oh[i,j]=1.
 ls=L(ps).astype(np.float32)
 return np.column_stack([A,oh,oh*ls[:,None]])

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
 df=X.merge(Y,on='response_id',validate='one_to_one').reset_index(drop=True); y=df.is_correct.to_numpy(int); groups=df.session_id.astype(str).to_numpy(); n=len(df)
 co=pickle.loads(CACHE.read_bytes()); texts=[co['texts'][str(r)] for r in df.response_id]; scal=np.vstack([co['scalars'][str(r)] for r in df.response_id]).astype(float)
 tc={}; sess=df.session_id.astype(str).drop_duplicates().tolist(); frames={s:v.transcript_frame(s,tc) for s in sess}
 alltxt=[v.role_text(frames[s]) for s in groups]; stutxt=[v.role_text(frames[s],'student') for s in groups]; tutt=[v.role_text(frames[s],'tutor') for s in groups]
 osv=np.vstack([v.outcome_scalars(frames[str(r.session_id)],str(r.learning_objective)) for r in df.itertuples(index=False)])
 uniq=np.array(sorted(set(groups))); rows=[]
 for seed in [19201,19202,19203]:
  rng=np.random.default_rng(seed); u=uniq.copy(); rng.shuffle(u); nb=int(.60*len(u)); nc=int(.20*len(u)); sb=set(u[:nb]); sc=set(u[nb:nb+nc]); st=set(u[nb+nc:])
  b=np.array([i for i,g in enumerate(groups) if g in sb]); c=np.array([i for i,g in enumerate(groups) if g in sc]); t=np.array([i for i,g in enumerate(groups) if g in st])
  ptc,ptt=fit_text(texts,scal,y,b,c,t,.35,35000); psc,pst=fit_plain(alltxt,y,b,c,t,.20,26000); puc,put=fit_plain(stutxt,y,b,c,t,.15,22000); pvc,pvt=fit_plain(tutt,y,b,c,t,.10,18000)
  ppc,ccc,_=v.objective_prior(df.iloc[b],df.iloc[c],2.0); ppt,cct,_=v.objective_prior(df.iloc[b],df.iloc[t],2.0)
  om=osv[b].mean(0); od=osv[b].std(0); od[od<1e-8]=1; osc=(osv[c]-om)/od; ost=(osv[t]-om)/od
  Bc=base(ptc,psc,ppc,ccc); Bt=base(ptt,pst,ppt,cct); Ac=full(ptc,psc,puc,pvc,ppc,ccc,osc); At=full(ptt,pst,put,pvt,ppt,cct,ost)
  q191=LogisticRegression(C=.1,solver='liblinear',max_iter=300).fit(Bc,y[c]).predict_proba(Bt)[:,1]
  q192=LogisticRegression(C=.15,solver='liblinear',max_iter=300).fit(Ac,y[c]).predict_proba(At)[:,1]
  vocab=sorted(set(df.iloc[b].learning_objective.astype(str))); Gc=geom(Ac,psc,df.iloc[c].learning_objective.astype(str).tolist(),vocab); Gt=geom(At,pst,df.iloc[t].learning_objective.astype(str).tolist(),vocab)
  best=None
  for C in [.005,.01,.02,.03,.05,.08,.1]:
   mod=LogisticRegression(C=C,solver='liblinear',max_iter=350).fit(Gc,y[c]); qc=mod.predict_proba(Gc)[:,1]; qt=mod.predict_proba(Gt)[:,1]; cm=M(y[c],qc); tm=M(y[t],qt)
   cand=(cm['logloss'],C,tm,qt)
   if best is None or cand[0]<best[0]: best=cand
  _,gc,mg,q193=best; m191=M(y[t],q191); m192=M(y[t],q192)
  rows.append({'seed':seed,'n_test':len(t),'v191':m191,'v192':m192,'v193_geom':mg,'geom_C':gc,'d192_191':m192['logloss']-m191['logloss'],'d193_192':mg['logloss']-m192['logloss']})
  print(json.dumps(rows[-1]))
 res={'protocol':'V193_STRICT_UNTOUCHED_SESSION_PROXY','rows':rows,'mean_d192_191':float(np.mean([r['d192_191'] for r in rows])),'mean_d193_192':float(np.mean([r['d193_192'] for r in rows])),'wins_v192_vs_v191':sum(r['d192_191']<0 for r in rows),'wins_v193_vs_v192':sum(r['d193_192']<0 for r in rows)}
 res['decision']='V193_GEOMETRY' if res['wins_v193_vs_v192']==3 and res['mean_d193_192']<=-.0005 else ('V192_CONFIRMED' if res['wins_v192_vs_v191']>=2 else 'V191_SAFER')
 (OUT/'strict_proxy.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
if __name__=='__main__': main()
