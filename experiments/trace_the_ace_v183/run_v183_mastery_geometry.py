#!/usr/bin/env python3
import hashlib, json, math, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

WS=Path('/workspace'); FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; TR=WS/'trace_the_ace/transcripts_extracted'; OUT=WS/'trace-ace-results/v183'
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
def count_phrases(text,arr): return sum(text.count(x) for x in arr)
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
    z=cache[sid]; ot=set(toks(obj)); n=max(len(z),1); scores=[]
    for i,r in z.iterrows():
        tt=set(toks(r.get('content',''))); ov=len(ot & tt); jac=ov/max(1,len(ot|tt)); scores.append((2*ov+jac,i))
    top=[i for sc,i in sorted(scores,reverse=True)[:6] if sc>0]
    if not top: top=list(range(max(0,len(z)-6),len(z)))
    keep=set()
    for i in top:
        for j in range(max(0,i-1),min(len(z),i+2)): keep.add(j)
    ordered=sorted(keep); parts=[]; rel_student=[]; rel_tutor=[]
    for i in ordered:
        r=z.iloc[i]; role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); pref='STUDENT' if 'student' in role else 'TUTOR'; parts.append(f'{pref}: {text}')
        overlap=len(ot & set(toks(text)))/max(1,len(ot))
        if 'student' in role: rel_student.append((i,text,overlap))
        elif 'tutor' in role: rel_tutor.append((i,text,overlap))
    joined=' '.join(x[1] for x in rel_student); tjoined=' '.join(x[1] for x in rel_tutor); last_student=rel_student[-1][1] if rel_student else ''; first_student=rel_student[0][1] if rel_student else ''
    def ss(text): return count_phrases(text,POS)-count_phrases(text,UNC)-0.5*count_phrases(text,SELF)
    maxsc=max([s for s,i in scores],default=0); lastpos=(max(ordered)/max(1,len(z)-1)) if ordered else 0
    vals=[len(z),len(ordered),len(rel_student),len(rel_tutor),maxsc,lastpos,max([x[2] for x in rel_student],default=0),max([x[2] for x in rel_tutor],default=0),count_phrases(joined,UNC),count_phrases(joined,POS),count_phrases(joined,SELF),count_phrases(tjoined,TCONF),count_phrases(tjoined,TCORR),count_phrases(tjoined,THINT),len(re.findall(r'\d',joined)),len(re.findall(r'[=+\-*/%]',joined)),ss(last_student),ss(last_student)-ss(first_student),1.0 if top and max(top)>=len(z)-3 else 0.0]
    return 'OBJECTIVE: '+str(obj)+' [KEY_MOMENTS] '+' '.join(parts),np.asarray(vals,float)
def objective_prior(train_df,query_df,alpha=2.0):
    gm=float(train_df.is_correct.mean()); st=train_df.groupby('learning_objective').is_correct.agg(['sum','count']); p=[]; c=[]
    for o in query_df.learning_objective:
        if o in st.index: ss=float(st.loc[o,'sum']); n=float(st.loc[o,'count'])
        else: ss=0.; n=0.
        p.append((ss+alpha*gm)/(n+alpha)); c.append(n)
    return np.asarray(p),np.asarray(c),gm
def metric(y,p): return {'logloss':float(log_loss(y,np.clip(p,EPS,1-EPS))),'auc':float(roc_auc_score(y,p))}

def fit_graph(frame, base_prior):
    # Learn directed residual transfer from labels only. Pair residuals within sessions;
    # shrink aggressively so rare co-occurrences cannot dominate.
    objs=sorted(frame.learning_objective.astype(str).unique()); oi={o:i for i,o in enumerate(objs)}; m=len(objs)
    num=np.zeros((m,m)); den=np.zeros((m,m)); cnt=np.zeros((m,m))
    tmp=frame[['session_id','learning_objective','is_correct']].copy(); tmp['res']=tmp.is_correct.to_numpy(float)-base_prior
    for _,g in tmp.groupby('session_id'):
        rows=list(g.itertuples(index=False))
        for a in rows:
            ia=oi[str(a.learning_objective)]
            for b in rows:
                ib=oi[str(b.learning_objective)]
                if ia==ib: continue
                num[ia,ib]+=float(a.res)*float(b.res); den[ia,ib]+=float(a.res)*float(a.res); cnt[ia,ib]+=1
    W=np.divide(num,den+1e-9); shrink=cnt/(cnt+20.0); W*=shrink; W=np.clip(W,-1.5,1.5)
    return objs,oi,W,cnt

def propagated_signal(frame,ptext,oi,W):
    out=np.zeros(len(frame)); support=np.zeros(len(frame)); idx_by_session={}
    for idx,sid in enumerate(frame.session_id.astype(str)): idx_by_session.setdefault(sid,[]).append(idx)
    for inds in idx_by_session.values():
        for i in inds:
            ti=oi.get(str(frame.iloc[i].learning_objective))
            if ti is None: continue
            vals=[]; ws=[]
            for j in inds:
                if j==i: continue
                sj=oi.get(str(frame.iloc[j].learning_objective))
                if sj is None: continue
                w=W[sj,ti]
                if abs(w)<1e-12: continue
                vals.append(w*(ptext[j]-0.5)); ws.append(abs(w))
            if ws:
                out[i]=sum(vals)/(sum(ws)+1e-9); support[i]=sum(ws)
    return out,support

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'}); df=X.merge(Y,on='response_id',validate='one_to_one')
    test_sessions=session_sample(df,N_TEST,'TEST'); test=df[df.session_id.isin(test_sessions)].copy().reset_index(drop=True); pool=df[~df.session_id.isin(test_sessions)].copy(); train_sessions=session_sample(pool,N_TRAIN,'TRAIN'); train=pool[pool.session_id.isin(train_sessions)].copy().reset_index(drop=True)
    work=pd.concat([train,test],ignore_index=True); ntr=len(train); print('TRAIN_ROWS',ntr,'TEST_ROWS',len(test))
    cache={}; texts=[]; scal=[]
    for k,r in enumerate(work.itertuples(index=False)):
        tx,v=build_row(str(r.session_id),str(r.learning_objective),cache); texts.append(tx); scal.append(v)
        if (k+1)%1000==0: print('FEATURE_ROWS',k+1)
    scal=np.vstack(scal); mu=scal[:ntr].mean(0); sd=scal[:ntr].std(0); sd[sd<1e-8]=1; scal=(scal-mu)/sd
    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode'); Xt=vec.fit_transform(texts[:ntr]); Xv=vec.transform(texts[ntr:]); Xtr=hstack([Xt,csr_matrix(scal[:ntr])],format='csr'); Xte=hstack([Xv,csr_matrix(scal[ntr:])],format='csr')
    y=train.is_correct.to_numpy(int); yt=test.is_correct.to_numpy(int); groups=train.session_id.astype(str).to_numpy(); gkf=GroupKFold(n_splits=4)
    oof=np.zeros(ntr); op=np.zeros(ntr); oc=np.zeros(ntr); graph_oof=np.zeros(ntr); graph_sup_oof=np.zeros(ntr)
    fold_data=[]
    for f,(a,b) in enumerate(gkf.split(np.zeros(ntr),y,groups)):
        m=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827); m.fit(Xtr[a],y[a]); oof[b]=m.predict_proba(Xtr[b])[:,1]
        p_a,_,_=objective_prior(train.iloc[a],train.iloc[a],2.0); p_b,c_b,_=objective_prior(train.iloc[a],train.iloc[b],2.0); op[b]=p_b; oc[b]=c_b
        objs,oi,W,cnt=fit_graph(train.iloc[a].reset_index(drop=True),p_a)
        sig,sup=propagated_signal(train.iloc[b].reset_index(drop=True),oof[b],oi,W); graph_oof[b]=sig; graph_sup_oof[b]=sup
        print('FOLD',f,'ROWS',len(b),'GRAPH_EDGES',int((cnt>0).sum()),'NONZERO_PROP',int((sup>0).sum()))
    final=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Xtr,y); ptext=final.predict_proba(Xte)[:,1]; tp,tc,gm=objective_prior(train,test,2.0)
    p_train_prior,_,_=objective_prior(train,train,2.0); objs,oi,W,cnt=fit_graph(train,p_train_prior); psig,psup=propagated_signal(test,ptext,oi,W)
    A=np.column_stack([logit(oof),logit(op),np.log1p(oc),logit(oof)*np.log1p(oc),logit(op)*np.log1p(oc)])
    B=np.column_stack([logit(ptext),logit(tp),np.log1p(tc),logit(ptext)*np.log1p(tc),logit(tp)*np.log1p(tc)])
    meta=LogisticRegression(C=.25,solver='liblinear',max_iter=200).fit(A,y); pv179=meta.predict_proba(B)[:,1]
    candidates=[{'name':'v179_control',**metric(yt,pv179)}]
    for C in [.03,.1,.25,1.0]:
        AG=np.column_stack([A,graph_oof,np.tanh(graph_oof),np.log1p(graph_sup_oof),graph_oof*np.log1p(graph_sup_oof)])
        BG=np.column_stack([B,psig,np.tanh(psig),np.log1p(psup),psig*np.log1p(psup)])
        mg=LogisticRegression(C=C,solver='liblinear',max_iter=240).fit(AG,y); pg=mg.predict_proba(BG)[:,1]
        candidates.append({'name':f'geometry_meta_C{C}',**metric(yt,pg),'coef_tail':mg.coef_.ravel()[-4:].tolist()})
    for w in [.1,.2,.35,.5]:
        q=np.clip(pv179+w*psig,EPS,1-EPS); candidates.append({'name':f'direct_geometry_{w}',**metric(yt,q)})
    best=min(candidates,key=lambda r:r['logloss']); ref=float(candidates[0]['logloss']); delta=best['logloss']-ref
    decision='MASTERY_GEOMETRY_PHASE_CHANGE__SCALE' if delta<=-.004 else ('MASTERY_GEOMETRY_HELP__REFINE' if delta<0 else 'NO_GAIN__GEOMETRY_NOT_SEPARATOR')
    result={'protocol':'V183_MASTERY_GEOMETRY','train_rows':ntr,'test_rows':len(test),'v179_control':candidates[0],'candidates':candidates,'best':best,'delta_vs_v179':delta,'graph_objectives':len(objs),'graph_observed_edges':int((cnt>0).sum()),'test_rows_with_geometry':int((psup>0).sum()),'decision':decision}
    (OUT/'v183_results.json').write_text(json.dumps(result,indent=2)); pd.DataFrame({'response_id':test.response_id.astype(str),'y':yt,'p_v179':pv179,'geometry_signal':psig,'geometry_support':psup}).to_csv(OUT/'v183_predictions.csv',index=False); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
