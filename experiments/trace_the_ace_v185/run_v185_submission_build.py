#!/usr/bin/env python3
import json, os, pickle, shutil, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
import joblib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'trace_the_ace_v183'))
import run_v183_mastery_geometry as v183

WS=Path('/workspace'); WORK=WS/'trace-ace-work/v185'; OUT=WS/'trace-ace-results/v185'; PKG=WORK/'package'
CACHE=WORK/'feature_cache.pkl'; ASSET=PKG/'v185_assets.joblib'
EPS=1e-6

def save_cache(obj):
    tmp=CACHE.with_suffix('.tmp'); tmp.write_bytes(pickle.dumps(obj,protocol=pickle.HIGHEST_PROTOCOL)); tmp.replace(CACHE)

def main():
    WORK.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True); PKG.mkdir(parents=True,exist_ok=True)
    X=pd.read_csv(v183.FEAT); Y=pd.read_csv(v183.LAB)
    print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
    df=X.merge(Y,on='response_id',validate='one_to_one').reset_index(drop=True)
    print('ROWS',len(df),'SESSIONS',df.session_id.nunique(),'OBJECTIVES',df.learning_objective.nunique())

    cache_obj={'texts':{},'scalars':{}}
    if CACHE.exists():
        try: cache_obj=pickle.loads(CACHE.read_bytes()); print('RESUME_FEATURES',len(cache_obj['texts']))
        except Exception as e: print('CACHE_READ_FAILED',repr(e))
    transcript_cache={}
    for k,r in enumerate(df.itertuples(index=False)):
        rid=str(r.response_id)
        if rid not in cache_obj['texts']:
            tx,sv=v183.build_row(str(r.session_id),str(r.learning_objective),transcript_cache)
            cache_obj['texts'][rid]=tx; cache_obj['scalars'][rid]=sv.astype(np.float32)
        if (k+1)%1000==0:
            save_cache(cache_obj); print('FEATURE_ROWS',k+1,flush=True)
    save_cache(cache_obj)
    texts=[cache_obj['texts'][str(x)] for x in df.response_id]
    scal=np.vstack([cache_obj['scalars'][str(x)] for x in df.response_id]).astype(float)
    mu=scal.mean(0); sd=scal.std(0); sd[sd<1e-8]=1; scalz=(scal-mu)/sd

    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
    Xt=vec.fit_transform(texts); Xall=hstack([Xt,csr_matrix(scalz)],format='csr')
    y=df.is_correct.to_numpy(int); groups=df.session_id.astype(str).to_numpy(); gkf=GroupKFold(n_splits=4)
    n=len(df); oof=np.zeros(n); op=np.zeros(n); oc=np.zeros(n); go=np.zeros(n); gs=np.zeros(n)
    for f,(a,b) in enumerate(gkf.split(np.zeros(n),y,groups)):
        bm=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Xall[a],y[a]); oof[b]=bm.predict_proba(Xall[b])[:,1]
        pa,_,_=v183.objective_prior(df.iloc[a],df.iloc[a],2.0); pb,cb,_=v183.objective_prior(df.iloc[a],df.iloc[b],2.0); op[b]=pb; oc[b]=cb
        objs,oi,W,cnt=v183.fit_graph(df.iloc[a].reset_index(drop=True),pa)
        sig,sup=v183.propagated_signal(df.iloc[b].reset_index(drop=True),oof[b],oi,W); go[b]=sig; gs[b]=sup
        print('OOF_FOLD',f,'ROWS',len(b),'GRAPH_EDGES',int((cnt>0).sum()),'GEOM_ROWS',int((sup>0).sum()),flush=True)
    A=np.column_stack([v183.logit(oof),v183.logit(op),np.log1p(oc),v183.logit(oof)*np.log1p(oc),v183.logit(op)*np.log1p(oc)])
    AG=np.column_stack([A,go,np.tanh(go),np.log1p(gs),go*np.log1p(gs)])
    geometry_meta=LogisticRegression(C=.1,solver='liblinear',max_iter=240).fit(AG,y)
    base=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Xall,y)
    pfull,counts,gm=v183.objective_prior(df,df,2.0)
    objs,oi,W,cnt=v183.fit_graph(df,pfull)
    st=df.groupby('learning_objective').is_correct.agg(['sum','count'])
    prior_stats={str(o):(float(r['sum']),float(r['count'])) for o,r in st.iterrows()}
    assets={'version':'V185_MASTERY_GEOMETRY','vectorizer':vec,'scalar_mu':mu,'scalar_sd':sd,'base_model':base,'geometry_meta':geometry_meta,'graph_objects':objs,'graph_index':oi,'graph_W':W,'prior_stats':prior_stats,'global_mean':float(gm),'prior_alpha':2.0,'train_rows':len(df)}
    joblib.dump(assets,ASSET,compress=3)

    # Generate a small runtime that reuses the exact V183 row representation.
    runtime = r'''#!/usr/bin/env python3
import sys, re, joblib
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
BASE=Path(__file__).resolve().parent
A=joblib.load(BASE/'v185_assets.joblib'); EPS=1e-6
STOP=set('the a an and or of to in on for with by from is are be being been this that these those how what when where why which can could would should do does did use using find calculate work solve understand know given student students'.split())
UNC=['not sure','dont know','don t know','idk','confused','maybe','i think','guess','unsure','no idea']; POS=['got it','understand','makes sense','i see','yes','correct','right','okay','ok','done']; SELF=['actually','wait','i mean','sorry','let me redo','made a mistake','my mistake']; TCONF=['correct','well done','exactly','that is right','that s right','yes','good job','great']; TCORR=['not quite','incorrect','check','try again','mistake','not correct','wrong','rethink']; THINT=['hint','remember','think about','consider','because','let me','try to','notice']
def toks(s): return [x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>1 and x not in STOP]
def cp(t,arr): return sum(t.count(x) for x in arr)
def row(sid,obj,trdir,cache):
    if sid not in cache:
        p=trdir/f'{sid}.csv'; xs=[] if p.exists() else list(trdir.glob(f'**/{sid}.csv')); p=p if p.exists() else (xs[0] if xs else None)
        z=pd.read_csv(p) if p else pd.DataFrame(columns=['role','content'])
        if 'timestamp' in z.columns:
            try: z=z.assign(_ts=pd.to_datetime(z.timestamp,errors='coerce')).sort_values(['_ts'],kind='stable')
            except Exception: pass
        cache[sid]=z.reset_index(drop=True)
    z=cache[sid]; ot=set(toks(obj)); scores=[]
    for i,r in z.iterrows():
        tt=set(toks(r.get('content',''))); ov=len(ot&tt); jac=ov/max(1,len(ot|tt)); scores.append((2*ov+jac,i))
    top=[i for sc,i in sorted(scores,reverse=True)[:6] if sc>0] or list(range(max(0,len(z)-6),len(z))); keep=set()
    for i in top:
        for j in range(max(0,i-1),min(len(z),i+2)): keep.add(j)
    ordered=sorted(keep); parts=[]; rs=[]; rt=[]
    for i in ordered:
        r=z.iloc[i]; role=str(r.get('role','')).lower(); text=str(r.get('content','')).lower(); parts.append(('STUDENT' if 'student' in role else 'TUTOR')+': '+text); ov=len(ot&set(toks(text)))/max(1,len(ot)); (rs if 'student' in role else rt).append((i,text,ov))
    joined=' '.join(x[1] for x in rs); tj=' '.join(x[1] for x in rt); last=rs[-1][1] if rs else ''; first=rs[0][1] if rs else ''
    ss=lambda t: cp(t,POS)-cp(t,UNC)-.5*cp(t,SELF); maxsc=max([s for s,i in scores],default=0); lastpos=max(ordered)/max(1,len(z)-1) if ordered else 0
    v=[len(z),len(ordered),len(rs),len(rt),maxsc,lastpos,max([x[2] for x in rs],default=0),max([x[2] for x in rt],default=0),cp(joined,UNC),cp(joined,POS),cp(joined,SELF),cp(tj,TCONF),cp(tj,TCORR),cp(tj,THINT),len(re.findall(r'\d',joined)),len(re.findall(r'[=+\-*/%]',joined)),ss(last),ss(last)-ss(first),1.0 if top and max(top)>=len(z)-3 else 0.0]
    return 'OBJECTIVE: '+str(obj)+' [KEY_MOMENTS] '+' '.join(parts),np.asarray(v,float)
def logit(p): p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))
def main():
    data=Path('/code_execution/data'); X=pd.read_csv(data/'test_features.csv'); tr=data/'test_transcripts'; cache={}; texts=[]; scal=[]
    for r in X.itertuples(index=False): tx,v=row(str(r.session_id),str(r.learning_objective),tr,cache); texts.append(tx); scal.append(v)
    scal=(np.vstack(scal)-A['scalar_mu'])/A['scalar_sd']; M=hstack([A['vectorizer'].transform(texts),csr_matrix(scal)],format='csr'); ptext=A['base_model'].predict_proba(M)[:,1]
    gm=A['global_mean']; alpha=A['prior_alpha']; pp=[]; cc=[]
    for o in X.learning_objective.astype(str):
        ss,n=A['prior_stats'].get(o,(0.,0.)); pp.append((ss+alpha*gm)/(n+alpha)); cc.append(n)
    pp=np.asarray(pp); cc=np.asarray(cc); oi=A['graph_index']; W=A['graph_W']; sig=np.zeros(len(X)); sup=np.zeros(len(X)); by={}
    for i,s in enumerate(X.session_id.astype(str)): by.setdefault(s,[]).append(i)
    for inds in by.values():
        for i in inds:
            ti=oi.get(str(X.iloc[i].learning_objective)); vals=[]; ws=[]
            if ti is None: continue
            for j in inds:
                if j==i: continue
                sj=oi.get(str(X.iloc[j].learning_objective));
                if sj is None: continue
                w=W[sj,ti]
                if abs(w)<1e-12: continue
                vals.append(w*(ptext[j]-.5)); ws.append(abs(w))
            if ws: sig[i]=sum(vals)/(sum(ws)+1e-9); sup[i]=sum(ws)
    B=np.column_stack([logit(ptext),logit(pp),np.log1p(cc),logit(ptext)*np.log1p(cc),logit(pp)*np.log1p(cc)]); BG=np.column_stack([B,sig,np.tanh(sig),np.log1p(sup),sig*np.log1p(sup)])
    pred=A['geometry_meta'].predict_proba(BG)[:,1]; out=pd.DataFrame({'response_id':X.response_id,'is_correct':np.clip(pred,1e-6,1-1e-6)}); Path('/code_execution').mkdir(parents=True,exist_ok=True); out.to_csv('/code_execution/submission.csv',index=False)
if __name__=='__main__': main()
'''
    (PKG/'main.py').write_text(runtime)
    zip_path=OUT/'trace_ace_v185_mastery_geometry_submission.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(PKG/'main.py','main.py'); z.write(ASSET,'v185_assets.joblib')
    result={'protocol':'V185_FULL_DATA_SUBMISSION_BUILD','train_rows':len(df),'feature_cache_rows':len(cache_obj['texts']),'asset_bytes':ASSET.stat().st_size,'zip_bytes':zip_path.stat().st_size,'graph_objectives':len(objs),'graph_edges':int((cnt>0).sum()),'decision':'ASSETS_BUILT__NEXT_EXACT_HARNESS_PARITY'}
    (OUT/'v185_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
