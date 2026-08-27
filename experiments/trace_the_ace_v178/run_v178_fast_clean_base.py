#!/usr/bin/env python3
import ast, hashlib, json, os, shutil, sys, zipfile
from pathlib import Path
import numpy as np, pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

WS=Path('/workspace'); ZIP=WS/'V157_RECOVERED_SUBMISSION.zip'; OUT=WS/'trace-ace-results/v178'; EX=WS/'trace-ace-work/v178_v157'
FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; TR=WS/'trace_the_ace/transcripts_extracted'
N_TEST=500; N_TRAIN=4000; EPS=1e-6

def import_main(path):
    tree=ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name=='build_base_predictions':
            for st in node.body:
                if isinstance(st,ast.Return):
                    st.value=ast.Tuple(elts=[ast.Name(id='X75',ctx=ast.Load()),ast.Name(id='Xr',ctx=ast.Load()),ast.Name(id='Z',ctx=ast.Load()),ast.Name(id='R',ctx=ast.Load())],ctx=ast.Load())
    ast.fix_missing_locations(tree); ns={'__name__':'v178_prod','__file__':str(path)}
    sys.path.insert(0,str(path.parent))
    try: exec(compile(tree,str(path),'exec'),ns)
    finally: sys.path.pop(0)
    return ns

def session_sample(df,n,seedtag):
    s=df.groupby('session_id').size().rename('n').reset_index()
    s['h']=s.session_id.astype(str).map(lambda x:int(hashlib.sha256((seedtag+x).encode()).hexdigest()[:16],16))
    s=s.sort_values(['h','session_id']); chosen=[]; rows=0
    for r in s.itertuples(index=False):
        chosen.append(r.session_id); rows+=int(r.n)
        if rows>=n: break
    return set(chosen)

def patch(X,nnum,raw,mean,std):
    std=np.where(std<1e-8,1.0,std); return hstack([X[:,:X.shape[1]-nnum],csr_matrix((raw-mean)/std)],format='csr')

def fit(X,y,C=.25):
    m=LogisticRegression(C=C,max_iter=200,solver='liblinear',random_state=20260827); m.fit(X,y); return m

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if EX.exists(): shutil.rmtree(EX)
    EX.mkdir(parents=True); zipfile.ZipFile(ZIP).extractall(EX)
    X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    df=X.merge(Y,on='response_id',validate='one_to_one')
    test_sessions=session_sample(df,N_TEST,'TEST'); test=df[df.session_id.isin(test_sessions)].copy()
    pool=df[~df.session_id.isin(test_sessions)].copy(); train_sessions=session_sample(pool,N_TRAIN,'TRAIN'); train=pool[pool.session_id.isin(train_sessions)].copy()
    work=pd.concat([train,test],ignore_index=True); ntr=len(train); print('TRAIN_ROWS',ntr,'TEST_ROWS',len(test),'TOTAL_FEATURE_ROWS',len(work))
    data=Path('/code_execution/data'); data.mkdir(parents=True,exist_ok=True); work[X.columns].to_csv(data/'test_features.csv',index=False)
    sf=work[['response_id']].copy(); sf['is_correct']=.5; sf.to_csv(data/'submission_format.csv',index=False)
    td=data/'test_transcripts'
    if td.is_symlink() or td.exists():
        if td.is_symlink() or td.is_file(): td.unlink()
        else: shutil.rmtree(td)
    os.symlink(TR,td,target_is_directory=True)
    ns=import_main(EX/'main.py'); old=np.load(EX/'assets/v135_assets.npz'); X75,Xr,Zold,Rold=ns['build_base_predictions'](work,td,old)
    print('MATRIX_SHAPES',X75.shape,Xr.shape)
    raw75=Zold*old['v75_num_std']+old['v75_num_mean']; rawr=Rold*old['related_num_std']+old['related_num_mean']
    m75,s75=raw75[:ntr].mean(0),raw75[:ntr].std(0); mr,sr=rawr[:ntr].mean(0),rawr[:ntr].std(0)
    A=patch(X75,28,raw75,m75,s75); B=patch(Xr,14,rawr,mr,sr); y=train.is_correct.to_numpy(int); yt=test.is_correct.to_numpy(int)
    f75=fit(A[:ntr],y); fr=fit(B[:ntr],y); p75=f75.predict_proba(A[ntr:])[:,1]; pr=fr.predict_proba(B[ntr:])[:,1]
    gm=float(train.is_correct.mean()); stats=train.groupby('learning_objective').is_correct.agg(['sum','count'])
    pp=np.array([(stats.loc[o,'sum']+2*gm)/(stats.loc[o,'count']+2) if o in stats.index else gm for o in test.learning_objective],float)
    rows=[]
    for w in [0,0.25,0.5,0.65,0.75,1.0]:
        q=np.clip(w*p75+(1-w)*pr,EPS,1-EPS); rows.append({'w75':w,'logloss':float(log_loss(yt,q)),'auc':float(roc_auc_score(yt,q))})
    prior={'logloss':float(log_loss(yt,np.clip(pp,EPS,1-EPS))),'auc':float(roc_auc_score(yt,pp))}; best=min(rows,key=lambda r:r['logloss'])
    result={'protocol':'V178_FAST_CLEAN_BASE','train_rows':ntr,'test_rows':len(test),'prior':prior,'blend_grid':rows,'best':best,'v75_ll':next(r['logloss'] for r in rows if r['w75']==1.0),'related_ll':next(r['logloss'] for r in rows if r['w75']==0),'decision':'PROMOTE_BASE_REBUILD' if best['logloss']<prior['logloss']-0.01 else 'BASE_MARGIN_SMALL'}
    (OUT/'v178_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
