#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

WS=Path('/workspace'); FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; TR=WS/'trace_the_ace/transcripts_extracted'; OUT=WS/'trace-ace-results/v181'
N_TEST=500; N_TRAIN=4000; EPS=1e-6
STOP=set('the a an and or of to in on for with by from is are be being been this that these those how what when where why which can could would should do does did use using find calculate work solve understand know given student students'.split())
UNC=['not sure','dont know','don t know','idk','confused','maybe','i think','guess','unsure','no idea']
POS=['got it','understand','makes sense','i see','yes','correct','right','okay','ok','done']
SELF=['actually','wait','i mean','sorry','let me redo','made a mistake','my mistake']
TCONF=['correct','well done','exactly','that is right','that s right','yes','good job','great']
TCORR=['not quite','incorrect','check','try again','mistake','not correct','wrong','rethink']
THINT=['hint','remember','think about','consider','because','let me','try to','notice']

def logit(p):
    p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def toks(s): return [x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>1 and x not in STOP]
def count_phrases(text, arr): return sum(text.count(x) for x in arr)
def session_sample(df,n,seedtag):
    s=df.groupby('session_id').size().rename('n').reset_index(); s['h']=s.session_id.astype(str).map(lambda x:int(hashlib.sha256((seedtag+x).encode()).hexdigest()[:16],16)); s=s.sort_values(['h','session_id']); chosen=[]; rows=0
    for r in s.itertuples(index=False):
        chosen.append(r.session_id); rows+=int(r.n)
        if rows>=n: break
    return set(chosen)
def find_transcript(sid):
    p=TR/f'{sid}.csv'
    if p.exists(): return p
    xs=list(TR.glob(f'**/{sid}.csv')); return xs[0] if xs else None

def build_row(sid,obj,cache):
    if sid not in cache:
        p=find_transcript(sid)
        if p is None: cache[sid]=pd.DataFrame(columns=['role','content'])
        else:
            z=pd.read_csv(p)
            print('TRANSCRIPT_HEADERS',sid,list(z.columns)) if len(cache)==0 else None
            if 'timestamp' in z.columns:
                try: z=z.assign(_ts=pd.to_datetime(z.timestamp,errors='coerce')).sort_values(['_ts'],kind='stable')
                except Exception: pass
            cache[sid]=z.reset_index(drop=True)
    z=cache[sid]; ot=set(toks(obj)); scores=[]
    for i,r in z.iterrows():
        tt=set(toks(r.get('content',''))); ov=len(ot & tt); jac=ov/max(1,len(ot|tt)); scores.append((2*ov+jac,i))
    top=[i for sc,i in sorted(scores,reverse=True)[:6] if sc>0]
    if not top: top=list(range(max(0,len(z)-6),len(z)))
    keep=set()
    for i in top:
        for j in range(max(0,i-1),min(len(z),i+2)): keep.add(j)
    ordered=sorted(keep); parts=[]; rel_student=[]; rel_tutor=[]
    for i in ordered:
        r=z.iloc[i]; role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); pref='STUDENT' if 'student' in role else 'TUTOR'
        parts.append(f'{pref}: {text}')
        overlap=len(ot & set(toks(text)))/max(1,len(ot))
        if 'student' in role: rel_student.append((i,text,overlap))
        elif 'tutor' in role: rel_tutor.append((i,text,overlap))
    joined=' '.join(x[1] for x in rel_student); tjoined=' '.join(x[1] for x in rel_tutor)
    last_student=rel_student[-1][1] if rel_student else ''; first_student=rel_student[0][1] if rel_student else ''
    def ssig(text): return count_phrases(text,POS)-count_phrases(text,UNC)-0.5*count_phrases(text,SELF)
    maxsc=max([s for s,i in scores],default=0); lastpos=(max(ordered)/max(1,len(z)-1)) if ordered else 0
    vals=np.asarray([
      len(z),len(ordered),len(rel_student),len(rel_tutor),maxsc,lastpos,
      max([x[2] for x in rel_student],default=0),max([x[2] for x in rel_tutor],default=0),
      count_phrases(joined,UNC),count_phrases(joined,POS),count_phrases(joined,SELF),
      count_phrases(tjoined,TCONF),count_phrases(tjoined,TCORR),count_phrases(tjoined,THINT),
      len(re.findall(r'\d',joined)),len(re.findall(r'[=+\-*/%]',joined)),
      ssig(last_student),ssig(last_student)-ssig(first_student),1.0 if top and max(top)>=len(z)-3 else 0.0
    ],float)
    text='OBJECTIVE: '+str(obj)+' [KEY_MOMENTS] '+' '.join(parts)
    return text,vals

def objective_prior(train_df, query_df, alpha=2.0):
    gm=float(train_df.is_correct.mean()); st=train_df.groupby('learning_objective').is_correct.agg(['sum','count'])
    p=[]; c=[]
    for o in query_df.learning_objective:
        if o in st.index: ss=float(st.loc[o,'sum']); n=float(st.loc[o,'count'])
        else: ss=0.; n=0.
        p.append((ss+alpha*gm)/(n+alpha)); c.append(n)
    return np.asarray(p),np.asarray(c)
def metric(y,p): return {'logloss':float(log_loss(y,np.clip(p,EPS,1-EPS))),'auc':float(roc_auc_score(y,p))}

def base_meta(pt,pp,c):
    s=np.log1p(c); lt=logit(pt); lp=logit(pp)
    return np.column_stack([lt,lp,s,lt*s,lp*s])
def trust_meta(pt,pp,c,q):
    b=base_meta(pt,pp,c); lt=logit(pt); s=np.log1p(c)
    # Frozen V181 separator: only label-free retrieval-quality signals already present in V179.
    # q columns: retrieved span, lexical score, position, student overlap, tutor overlap,
    # last-student signal, signal change, terminal-hit flag.
    return np.column_stack([b,q,lt[:,None]*q,(lt*s)[:,None]*q[:,3:5]])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
    df=X.merge(Y,on='response_id',validate='one_to_one')
    test_sessions=session_sample(df,N_TEST,'TEST'); test=df[df.session_id.isin(test_sessions)].copy(); pool=df[~df.session_id.isin(test_sessions)].copy(); train_sessions=session_sample(pool,N_TRAIN,'TRAIN'); train=pool[pool.session_id.isin(train_sessions)].copy()
    work=pd.concat([train,test],ignore_index=True); ntr=len(train); print('TRAIN_ROWS',ntr,'TEST_ROWS',len(test))
    cache={}; texts=[]; scal=[]
    for k,r in enumerate(work.itertuples(index=False)):
        tx,v=build_row(str(r.session_id),str(r.learning_objective),cache); texts.append(tx); scal.append(v)
        if (k+1)%1000==0: print('FEATURE_ROWS',k+1)
    scal=np.vstack(scal); mu=scal[:ntr].mean(0); sd=scal[:ntr].std(0); sd[sd<1e-8]=1; zscal=(scal-mu)/sd
    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
    Xt=vec.fit_transform(texts[:ntr]); Xv=vec.transform(texts[ntr:]); Xtr=hstack([Xt,csr_matrix(zscal[:ntr])],format='csr'); Xte=hstack([Xv,csr_matrix(zscal[ntr:])],format='csr')
    y=train.is_correct.to_numpy(int); yt=test.is_correct.to_numpy(int); groups=train.session_id.astype(str).to_numpy(); gkf=GroupKFold(n_splits=4)
    oof=np.zeros(ntr)
    for f,(a,b) in enumerate(gkf.split(np.zeros(ntr),y,groups)):
        m=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827); m.fit(Xtr[a],y[a]); oof[b]=m.predict_proba(Xtr[b])[:,1]; print('TEXT_OOF_FOLD',f,len(b))
    final=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827); final.fit(Xtr,y); ptext=final.predict_proba(Xte)[:,1]
    op=np.zeros(ntr); oc=np.zeros(ntr)
    for a,b in gkf.split(np.zeros(ntr),y,groups): op[b],oc[b]=objective_prior(train.iloc[a],train.iloc[b],2.0)
    tp,tc=objective_prior(train,test,2.0)
    qi=[1,4,5,6,7,16,17,18]; qtr=zscal[:ntr,qi]; qte=zscal[ntr:,qi]
    rows=[{'name':'prior_alpha2',**metric(yt,tp)},{'name':'v179_text_raw_reproduction',**metric(yt,ptext)}]
    A0=base_meta(oof,op,oc); B0=base_meta(ptext,tp,tc)
    m0=LogisticRegression(C=.25,solver='liblinear',max_iter=220).fit(A0,y); p0=m0.predict_proba(B0)[:,1]; rows.append({'name':'v179_support_stack_reproduction',**metric(yt,p0)})
    A=trust_meta(oof,op,oc,qtr); B=trust_meta(ptext,tp,tc,qte)
    preds={}
    for C in [.03,.06,.10,.15]:
        m=LogisticRegression(C=C,solver='liblinear',max_iter=240).fit(A,y); p=m.predict_proba(B)[:,1]; preds[f'C{C}']=p; rows.append({'name':f'retrieval_trust_stack_C{C}',**metric(yt,p)})
    best=min(rows,key=lambda r:r['logloss']); ref=.5765775587897433
    result={'protocol':'V181_RETRIEVAL_TRUST_GATE','train_rows':ntr,'test_rows':len(test),'v179_best_reference':ref,'vocab':len(vec.vocabulary_),'quality_indices':qi,'candidates':rows,'best':best,'delta_vs_v179':best['logloss']-ref}
    if best['logloss']<ref-.002: result['decision']='TRUST_SEPARATOR_CLEAR_GAIN__SCALE_NEXT'
    elif best['logloss']<ref: result['decision']='TRUST_SEPARATOR_SMALL_GAIN__RETAIN'
    else: result['decision']='NO_GAIN__V179_REMAINS_FRONTIER'
    (OUT/'v181_results.json').write_text(json.dumps(result,indent=2))
    out={'response_id':test.response_id.astype(str),'y':yt,'p_text':ptext,'p_prior':tp,'p_v179_repro':p0,'objective_support':tc}
    out.update({f'p_trust_{k}':v for k,v in preds.items()}); pd.DataFrame(out).to_csv(OUT/'v181_predictions.csv',index=False)
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
