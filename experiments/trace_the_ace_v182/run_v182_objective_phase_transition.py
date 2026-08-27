#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
import numpy as np,pandas as pd
from scipy.sparse import hstack,csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,roc_auc_score
from sklearn.model_selection import GroupKFold
WS=Path('/workspace'); FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; TR=WS/'trace_the_ace/transcripts_extracted'; OUT=WS/'trace-ace-results/v182'
N_TEST=500;N_TRAIN=4000;EPS=1e-6
STOP=set('the a an and or of to in on for with by from is are be being been this that these those how what when where why which can could would should do does did use using find calculate work solve understand know given student students'.split())
UNC=['not sure','dont know','don t know','idk','confused','maybe','i think','guess','unsure','no idea']; POS=['got it','understand','makes sense','i see','yes','correct','right','okay','ok','done']; SELF=['actually','wait','i mean','sorry','let me redo','made a mistake','my mistake']; TCONF=['correct','well done','exactly','that is right','that s right','yes','good job','great']; TCORR=['not quite','incorrect','check','try again','mistake','not correct','wrong','rethink']; THINT=['hint','remember','think about','consider','because','let me','try to','notice']
def logit(p): p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def toks(s): return [x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>1 and x not in STOP]
def cnt(t,a): return sum(t.count(x) for x in a)
def session_sample(df,n,tag):
 s=df.groupby('session_id').size().rename('n').reset_index(); s['h']=s.session_id.astype(str).map(lambda x:int(hashlib.sha256((tag+x).encode()).hexdigest()[:16],16)); s=s.sort_values(['h','session_id']); return _cut(s,n)
def _cut(s,n):
 out=[];k=0
 for r in s.itertuples(index=False):
  out.append(r.session_id);k+=int(r.n)
  if k>=n: break
 return set(out)
def find_transcript(sid):
 p=TR/f'{sid}.csv'
 if p.exists(): return p
 xs=list(TR.glob(f'**/{sid}.csv')); return xs[0] if xs else None
def build_row(sid,obj,cache):
 if sid not in cache:
  p=find_transcript(sid)
  if p is None: cache[sid]=pd.DataFrame(columns=['role','content'])
  else:
   z=pd.read_csv(p); print('TRANSCRIPT_HEADERS',sid,list(z.columns)) if len(cache)==0 else None
   if 'timestamp' in z.columns:
    try:z=z.assign(_ts=pd.to_datetime(z.timestamp,errors='coerce')).sort_values(['_ts'],kind='stable')
    except Exception:pass
   cache[sid]=z.reset_index(drop=True)
 z=cache[sid];ot=set(toks(obj));scores=[]
 for i,r in z.iterrows():
  tt=set(toks(r.get('content','')));ov=len(ot&tt);jac=ov/max(1,len(ot|tt));scores.append((2*ov+jac,i))
 top=[i for sc,i in sorted(scores,reverse=True)[:6] if sc>0]
 if not top: top=list(range(max(0,len(z)-6),len(z)))
 keep=set()
 for i in top:
  for j in range(max(0,i-1),min(len(z),i+2)):keep.add(j)
 ordered=sorted(keep);parts=[];students=[];tutors=[]
 for i in ordered:
  r=z.iloc[i];role=str(r.get('role','')).lower();text=str(r.get('content','')).lower();pref='STUDENT' if 'student' in role else 'TUTOR';parts.append(f'{pref}: {text}');ov=len(ot&set(toks(text)))/max(1,len(ot))
  if 'student' in role:students.append((i,text,ov))
  elif 'tutor' in role:tutors.append((i,text,ov))
 joined=' '.join(x[1] for x in students);tjoined=' '.join(x[1] for x in tutors);last=students[-1][1] if students else '';first=students[0][1] if students else ''
 def ss(t):return cnt(t,POS)-cnt(t,UNC)-.5*cnt(t,SELF)
 maxsc=max([s for s,i in scores],default=0);lastpos=(max(ordered)/max(1,len(z)-1)) if ordered else 0
 vals=np.asarray([len(z),len(ordered),len(students),len(tutors),maxsc,lastpos,max([x[2] for x in students],default=0),max([x[2] for x in tutors],default=0),cnt(joined,UNC),cnt(joined,POS),cnt(joined,SELF),cnt(tjoined,TCONF),cnt(tjoined,TCORR),cnt(tjoined,THINT),len(re.findall(r'\d',joined)),len(re.findall(r'[=+\-*/%]',joined)),ss(last),ss(last)-ss(first),1. if top and max(top)>=len(z)-3 else 0.],float)
 pre=[];teach=[];post=[]
 for anchor in top[:3]:
  sb=[i for i in range(anchor,-1,-1) if 'student' in str(z.iloc[i].get('role','')).lower()]
  ti=[i for i in range(max(0,anchor-1),min(len(z),anchor+3)) if 'tutor' in str(z.iloc[i].get('role','')).lower()]
  s0=sb[0] if sb else None
  t0=next((i for i in ti if s0 is None or i>=s0),ti[0] if ti else None)
  sa=[i for i in range((t0+1 if t0 is not None else anchor+1),min(len(z),anchor+5)) if 'student' in str(z.iloc[i].get('role','')).lower()]
  s1=sa[0] if sa else None
  if s0 is not None: pre.append(str(z.iloc[s0].get('content','')).lower())
  if t0 is not None: teach.append(str(z.iloc[t0].get('content','')).lower())
  if s1 is not None: post.append(str(z.iloc[s1].get('content','')).lower())
 base='OBJECTIVE: '+str(obj)+' [KEY_MOMENTS] '+' '.join(parts)
 return base,'OBJECTIVE: '+str(obj)+' [PRE_STUDENT] '+' '.join(pre),'OBJECTIVE: '+str(obj)+' [TUTOR_INTERVENTION] '+' '.join(teach),'OBJECTIVE: '+str(obj)+' [POST_STUDENT] '+' '.join(post),vals
def objective_prior(tr,q,alpha=2.):
 gm=float(tr.is_correct.mean());st=tr.groupby('learning_objective').is_correct.agg(['sum','count']);p=[];c=[]
 for o in q.learning_objective:
  if o in st.index:ss=float(st.loc[o,'sum']);n=float(st.loc[o,'count'])
  else:ss=0.;n=0.
  p.append((ss+alpha*gm)/(n+alpha));c.append(n)
 return np.asarray(p),np.asarray(c)
def metric(y,p):return {'logloss':float(log_loss(y,np.clip(p,EPS,1-EPS))),'auc':float(roc_auc_score(y,p))}
def meta(pt,pp,c):s=np.log1p(c);lt=logit(pt);lp=logit(pp);return np.column_stack([lt,lp,s,lt*s,lp*s])
def fit_oof(Xtr,Xte,y,groups,C):
 g=GroupKFold(n_splits=4);o=np.zeros(len(y))
 for f,(a,b) in enumerate(g.split(np.zeros(len(y)),y,groups)):
  m=LogisticRegression(C=C,max_iter=200,solver='liblinear',random_state=20260827);m.fit(Xtr[a],y[a]);o[b]=m.predict_proba(Xtr[b])[:,1];print('OOF',C,f,len(b))
 m=LogisticRegression(C=C,max_iter=200,solver='liblinear',random_state=20260827);m.fit(Xtr,y);return o,m.predict_proba(Xte)[:,1]
def main():
 OUT.mkdir(parents=True,exist_ok=True);X=pd.read_csv(FEAT);Y=pd.read_csv(LAB);print('FEATURE_HEADERS',list(X.columns));print('LABEL_HEADERS',list(Y.columns));target='is_correct' if 'is_correct' in Y.columns else 'correct';Y=Y.rename(columns={target:'is_correct'});df=X.merge(Y,on='response_id',validate='one_to_one')
 ts=session_sample(df,N_TEST,'TEST');test=df[df.session_id.isin(ts)].copy();pool=df[~df.session_id.isin(ts)].copy();trs=session_sample(pool,N_TRAIN,'TRAIN');train=pool[pool.session_id.isin(trs)].copy();work=pd.concat([train,test],ignore_index=True);ntr=len(train);print('TRAIN_ROWS',ntr,'TEST_ROWS',len(test))
 cache={};base=[];pre=[];teach=[];post=[];sc=[]
 for k,r in enumerate(work.itertuples(index=False)):
  a,b,c,d,v=build_row(str(r.session_id),str(r.learning_objective),cache);base.append(a);pre.append(b);teach.append(c);post.append(d);sc.append(v)
  if (k+1)%1000==0:print('FEATURE_ROWS',k+1)
 sc=np.vstack(sc);mu=sc[:ntr].mean(0);sd=sc[:ntr].std(0);sd[sd<1e-8]=1;z=(sc-mu)/sd
 vb=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode');B=vb.fit_transform(base[:ntr]);Bv=vb.transform(base[ntr:]);Xb=hstack([B,csr_matrix(z[:ntr])],format='csr');Xbv=hstack([Bv,csr_matrix(z[ntr:])],format='csr')
 vecs=[];mats=[];vmats=[]
 for name,texts,mf in [('pre',pre,14000),('tutor',teach,14000),('post',post,14000)]:
  v=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=mf,strip_accents='unicode');a=v.fit_transform(texts[:ntr]);b=v.transform(texts[ntr:]);vecs.append((name,len(v.vocabulary_)));mats.append(a);vmats.append(b)
 Xt=hstack(mats+[csr_matrix(z[:ntr])],format='csr');Xtv=hstack(vmats+[csr_matrix(z[ntr:])],format='csr')
 y=train.is_correct.to_numpy(int);yt=test.is_correct.to_numpy(int);groups=train.session_id.astype(str).to_numpy();gkf=GroupKFold(n_splits=4);op=np.zeros(ntr);oc=np.zeros(ntr)
 for a,b in gkf.split(np.zeros(ntr),y,groups):op[b],oc[b]=objective_prior(train.iloc[a],train.iloc[b])
 tp,tc=objective_prior(train,test);rows=[{'name':'prior_alpha2',**metric(yt,tp)}];pred={}
 ob,pb=fit_oof(Xb,Xbv,y,groups,.35);mb=LogisticRegression(C=.25,solver='liblinear',max_iter=220).fit(meta(ob,op,oc),y);pv=mb.predict_proba(meta(pb,tp,tc))[:,1];rows.append({'name':'v179_support_stack_reproduction',**metric(yt,pv)});pred['p_v179_repro']=pv
 for C in [.15,.25,.35]:
  oo,pp=fit_oof(Xt,Xtv,y,groups,C);mm=LogisticRegression(C=.25,solver='liblinear',max_iter=220).fit(meta(oo,op,oc),y);pm=mm.predict_proba(meta(pp,tp,tc))[:,1];rows.append({'name':f'phase_transition_stack_C{C}',**metric(yt,pm)});pred[f'p_phase_C{C}']=pm
 best=min(rows,key=lambda r:r['logloss']);ref=.5765775587897433;res={'protocol':'V182_OBJECTIVE_PHASE_TRANSITION','train_rows':ntr,'test_rows':len(test),'v179_best_reference':ref,'base_vocab':len(vb.vocabulary_),'phase_vocabs':dict(vecs),'candidates':rows,'best':best,'delta_vs_v179':best['logloss']-ref}
 res['decision']='PHASE_TRANSITION_CLEAR_GAIN__SCALE_NEXT' if best['logloss']<ref-.002 else ('PHASE_TRANSITION_SMALL_GAIN__RETAIN' if best['logloss']<ref else 'NO_GAIN__CHANGE_REPRESENTATION_AGAIN')
 (OUT/'v182_results.json').write_text(json.dumps(res,indent=2));out={'response_id':test.response_id.astype(str),'y':yt,'p_prior':tp,'objective_support':tc};out.update(pred);pd.DataFrame(out).to_csv(OUT/'v182_predictions.csv',index=False);print(json.dumps(res,indent=2))
if __name__=='__main__':main()
