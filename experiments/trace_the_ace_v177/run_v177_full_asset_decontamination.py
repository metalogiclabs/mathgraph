#!/usr/bin/env python3
import ast, copy, hashlib, importlib.util, json, os, shutil, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

WS=Path('/workspace'); ZIP=WS/'V157_RECOVERED_SUBMISSION.zip'
OUT=WS/'trace-ace-results/v177'; EX=WS/'trace-ace-work/v177_v157'; N_TARGET=1500
FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; TR=WS/'trace_the_ace/transcripts_extracted'
EPS=1e-6

def sigmoid(x): return 1/(1+np.exp(-np.clip(np.asarray(x,float),-40,40)))
def logit(p):
    p=np.clip(np.asarray(p,float),EPS,1-EPS); return np.log(p/(1-p))

def import_transformed_main(path):
    src=path.read_text(); tree=ast.parse(src)
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name=='build_base_predictions':
            for i,st in enumerate(node.body):
                if isinstance(st,ast.Return):
                    # Production function has computed X75/Xr and standardized Z/R by this point.
                    st.value=ast.Tuple(elts=[ast.Name(id='X75',ctx=ast.Load()),ast.Name(id='Xr',ctx=ast.Load()),ast.Name(id='Z',ctx=ast.Load()),ast.Name(id='R',ctx=ast.Load())],ctx=ast.Load())
    ast.fix_missing_locations(tree); code=compile(tree,str(path),'exec')
    ns={'__name__':'v177_prod','__file__':str(path)}
    old=list(sys.path); sys.path.insert(0,str(path.parent))
    try: exec(code,ns)
    finally: sys.path[:]=old
    return ns

def choose_split(df):
    sessions=df.groupby('session_id').size().rename('n').reset_index()
    sessions['h']=sessions.session_id.astype(str).map(lambda s:int(hashlib.sha256(s.encode()).hexdigest()[:16],16))
    sessions=sessions.sort_values(['h','session_id']); chosen=[]; rows=0
    for r in sessions.itertuples(index=False):
        chosen.append(r.session_id); rows+=int(r.n)
        if rows>=N_TARGET: break
    mask=df.session_id.isin(set(chosen)); return df.loc[~mask].copy(),df.loc[mask].copy()

def patch_numeric(X, nnum, raw, mean, std):
    std=np.where(std<1e-8,1.0,std); z=(raw-mean)/std
    return hstack([X[:,:X.shape[1]-nnum],csr_matrix(z)],format='csr')

def fit_lr(X,y,C):
    m=LogisticRegression(C=C,max_iter=300,solver='liblinear',random_state=20260815)
    m.fit(X,y); return m

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if EX.exists(): shutil.rmtree(EX)
    EX.mkdir(parents=True); assert ZIP.exists()
    with zipfile.ZipFile(ZIP) as z:z.extractall(EX)
    Xdf=pd.read_csv(FEAT); Ydf=pd.read_csv(LAB)
    print('FEATURE_HEADERS',list(Xdf.columns)); print('LABEL_HEADERS',list(Ydf.columns))
    df=Xdf.merge(Ydf,on='response_id',validate='one_to_one'); train,test=choose_split(df)
    print('TRAIN_ROWS',len(train),'TEST_ROWS',len(test),'TEST_SESSIONS',test.session_id.nunique())

    # Build a temporary competition-shaped dataset containing all rows so the exact production
    # feature constructor gives us its own X75/Xr matrices. No labels enter this step.
    data=Path('/code_execution/data'); data.mkdir(parents=True,exist_ok=True)
    df[Xdf.columns].to_csv(data/'test_features.csv',index=False)
    sf=df[['response_id']].copy(); sf['is_correct']=0.5; sf.to_csv(data/'submission_format.csv',index=False)
    td=data/'test_transcripts'
    if td.is_symlink() or td.exists():
        if td.is_symlink() or td.is_file():td.unlink()
        else:shutil.rmtree(td)
    os.symlink(TR,td,target_is_directory=True)

    ns=import_transformed_main(EX/'main.py')
    old_assets=np.load(EX/'assets/v135_assets.npz')
    X75,Xr,Zold,Rold=ns['build_base_predictions'](df,td,old_assets)
    print('MATRIX_SHAPES',X75.shape,Xr.shape,Zold.shape,Rold.shape)
    assert X75.shape[1]==len(old_assets['v75_coef']) and Xr.shape[1]==len(old_assets['related_coef'])

    raw75=Zold*old_assets['v75_num_std']+old_assets['v75_num_mean']
    rawr=Rold*old_assets['related_num_std']+old_assets['related_num_mean']
    train_idx=train.index.to_numpy(); test_idx=test.index.to_numpy(); y=train.is_correct.to_numpy(int); yt=test.is_correct.to_numpy(int)
    m75=raw75[train_idx].mean(0); s75=raw75[train_idx].std(0); mr=rawr[train_idx].mean(0); sr=rawr[train_idx].std(0)
    X75c=patch_numeric(X75,28,raw75,m75,s75); Xrc=patch_numeric(Xr,14,rawr,mr,sr)

    # 4-fold session-grouped OOF, matching manifest stack_training contract.
    o75=np.zeros(len(train)); orr=np.zeros(len(train)); gkf=GroupKFold(n_splits=4)
    groups=train.session_id.astype(str).to_numpy()
    for fold,(tr,va) in enumerate(gkf.split(np.zeros(len(train)),y,groups)):
        a=fit_lr(X75c[train_idx[tr]],y[tr],0.25); b=fit_lr(Xrc[train_idx[tr]],y[tr],0.25)
        o75[va]=a.predict_proba(X75c[train_idx[va]])[:,1]; orr[va]=b.predict_proba(Xrc[train_idx[va]])[:,1]
        print('OOF_FOLD',fold,'rows',len(va))

    gm=float(train.is_correct.mean()); stats=train.groupby('learning_objective').is_correct.agg(['sum','count'])
    pp=np.array([(stats.loc[o,'sum']+2*gm)/(stats.loc[o,'count']+2) if o in stats.index else gm for o in train.learning_objective],float)
    cnt=np.array([stats.loc[o,'count'] if o in stats.index else 0 for o in train.learning_objective],float)
    S=np.column_stack([logit(o75),logit(orr),logit(o75)-logit(orr),logit(pp),np.log1p(cnt)])
    stack=fit_lr(S,y,0.1)
    print('OOF_BASE_LL',log_loss(y,o75),log_loss(y,orr),'STACK_LL',log_loss(y,stack.predict_proba(S)[:,1]))

    # Final complement-only base fits.
    f75=fit_lr(X75c[train_idx],y,0.25); fr=fit_lr(Xrc[train_idx],y,0.25)
    assets={k:old_assets[k] for k in old_assets.files}
    assets.update(v75_coef=f75.coef_.ravel(),v75_intercept=f75.intercept_.ravel(),v75_num_mean=m75,v75_num_std=np.where(s75<1e-8,1.0,s75),related_coef=fr.coef_.ravel(),related_intercept=fr.intercept_.ravel(),related_num_mean=mr,related_num_std=np.where(sr<1e-8,1.0,sr),stack_coef=stack.coef_.ravel(),stack_intercept=stack.intercept_.ravel())
    np.savez(EX/'assets/v135_assets.npz',**assets)
    manifest=json.loads((EX/'assets/manifest.json').read_text()); manifest['global_mean']=gm; manifest['prior_alpha']=2.0
    manifest['objective_counts']={str(k):int(v) for k,v in train.groupby('learning_objective').size().items()}
    manifest['objective_sums']={str(k):float(v) for k,v in train.groupby('learning_objective').is_correct.sum().items()}
    manifest['v177_note']='All label-derived runtime assets rebuilt on 33,572-row deterministic session complement; 1,500-row sample excluded.'
    (EX/'assets/manifest.json').write_text(json.dumps(manifest))

    # Score exact production equation directly on untouched sample, avoiding another expensive feature pass.
    p75=f75.predict_proba(X75c[test_idx])[:,1]; pr=fr.predict_proba(Xrc[test_idx])[:,1]
    objs=test.learning_objective.astype(str).to_numpy(); counts=manifest['objective_counts']; sums=manifest['objective_sums']
    n=np.array([counts.get(str(k),0) for k in objs],float); ss=np.array([sums.get(str(k),0.0) for k in objs],float)
    pprior=np.clip((ss+2*gm)/(n+2),EPS,1-EPS); q=.65*p75+.35*pr; seen=n>0
    St=np.column_stack([logit(p75),logit(pr),logit(p75)-logit(pr),logit(pprior),np.log1p(n)])
    q[seen]=stack.predict_proba(St[seen])[:,1]; q=np.clip(q,EPS,1-EPS)
    ll=float(log_loss(yt,q)); auc=float(roc_auc_score(yt,q))
    priorll=float(log_loss(yt,pprior));
    result={'protocol':'V177_FULL_LABEL_ASSET_DECONTAMINATION','train_rows':len(train),'test_rows':len(test),'test_sessions':int(test.session_id.nunique()),'fully_clean_production_logloss':ll,'fully_clean_production_auc':auc,'clean_prior_logloss':priorll,'pred_mean':float(q.mean()),'pred_std':float(q.std()),'oof_v75_logloss':float(log_loss(y,o75)),'oof_related_logloss':float(log_loss(y,orr)),'oof_stack_logloss':float(log_loss(y,stack.predict_proba(S)[:,1])),'delta_vs_v174_full_asset':ll-0.49088,'delta_vs_v176_manifest_only':ll-0.49308725959120225}
    if ll<0.535: result.update(decision='CLEAN_RUNTIME_STRONG__PROMOTION_CANDIDATE',residual='Clean complement-only runtime materially beats objective prior. Next cross-fit across multiple deterministic folds and package full-data candidate.')
    elif ll<0.56: result.update(decision='CLEAN_RUNTIME_USEFUL__NEEDS_ROBUSTIFICATION',residual='Signal survives full decontamination but margin is modest. Tune stack/calibration under repeated session-cold folds before submission.')
    else: result.update(decision='FULL_ASSET_OPTIMISM_EXPLAINS_GAP',residual='Most apparent runtime gain was label-asset contamination. Fall back to robust cross-fitted representation and rebuild final package.')
    (OUT/'v177_results.json').write_text(json.dumps(result,indent=2)); pd.DataFrame({'response_id':test.response_id.astype(str),'is_correct':yt,'prediction':q,'prior':pprior}).to_csv(OUT/'v177_predictions.csv',index=False); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
