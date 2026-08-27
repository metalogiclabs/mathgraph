#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, zipfile, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score

WS=Path('/workspace'); ZIP=WS/'V157_RECOVERED_SUBMISSION.zip'
OUT=WS/'trace-ace-results/v176'; EXBASE=WS/'trace-ace-work/v176'
DATA=Path('/code_execution/data'); N_TARGET=1500
ALPHAS=[2.0,5.0,10.0,20.0,50.0,100.0]

def choose_split(df):
    sessions=df.groupby('session_id').size().rename('n').reset_index()
    sessions['h']=sessions.session_id.astype(str).map(lambda s:int(hashlib.sha256(s.encode()).hexdigest()[:16],16))
    sessions=sessions.sort_values(['h','session_id'])
    chosen=[]; rows=0
    for r in sessions.itertuples(index=False):
        chosen.append(r.session_id); rows+=int(r.n)
        if rows>=N_TARGET: break
    m=df.session_id.isin(set(chosen))
    return df.loc[~m].copy(),df.loc[m].copy()

def setup_harness(X,test,trdir):
    DATA.mkdir(parents=True,exist_ok=True)
    test[X.columns].to_csv(DATA/'test_features.csv',index=False)
    sf=test[['response_id']].copy(); sf['is_correct']=0.5; sf.to_csv(DATA/'submission_format.csv',index=False)
    target=DATA/'test_transcripts'
    if target.is_symlink() or target.exists():
        if target.is_symlink() or target.is_file(): target.unlink()
        else: shutil.rmtree(target)
    os.symlink(trdir,target,target_is_directory=True)

def run_variant(alpha, manifest, test):
    ex=EXBASE/f'a{str(alpha).replace(".","p")}'
    if ex.exists(): shutil.rmtree(ex)
    ex.mkdir(parents=True)
    with zipfile.ZipFile(ZIP) as z:z.extractall(ex)
    m=dict(manifest); m['prior_alpha']=alpha
    (ex/'assets/manifest.json').write_text(json.dumps(m,indent=2))
    sub=Path('/code_execution/submission.csv')
    if sub.exists(): sub.unlink()
    p=subprocess.run([sys.executable,str(ex/'main.py')],cwd=str(ex),text=True,capture_output=True,timeout=600)
    if p.returncode!=0 or not sub.exists(): return {'alpha':alpha,'returncode':p.returncode,'stderr_tail':p.stderr[-1200:]}
    P=pd.read_csv(sub); pc='is_correct' if 'is_correct' in P else [c for c in P if c!='response_id'][0]
    z=test[['response_id','is_correct']].merge(P[['response_id',pc]],on='response_id',validate='one_to_one')
    y=z.is_correct.to_numpy(int); pr=np.clip(z[pc].to_numpy(float),1e-6,1-1e-6)
    return {'alpha':alpha,'returncode':0,'logloss':float(log_loss(y,pr)),'auc':float(roc_auc_score(y,pr)),'mean':float(pr.mean()),'std':float(pr.std())}

def main():
    OUT.mkdir(parents=True,exist_ok=True); EXBASE.mkdir(parents=True,exist_ok=True)
    X=pd.read_csv(WS/'trace_the_ace/train_features_TMQTWsB.csv'); Y=pd.read_csv(WS/'trace_the_ace/train_labels_44ujmj2.csv')
    print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    df=X.merge(Y,on='response_id',validate='one_to_one'); train,test=choose_split(df)
    print('TRAIN_ROWS',len(train),'TEST_ROWS',len(test),'TEST_SESSIONS',test.session_id.nunique())
    setup_harness(X,test,WS/'trace_the_ace/transcripts_extracted')

    # Recover original manifest, then replace all directly label-derived aggregate fields with complement-only values.
    tmp=EXBASE/'manifest_src';
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(ZIP) as z:z.extract('assets/manifest.json',tmp)
    orig=json.loads((tmp/'assets/manifest.json').read_text())
    objcol='learning_objective' if 'learning_objective' in train.columns else 'learning_objective_id'
    g=float(train.is_correct.mean())
    agg=train.groupby(objcol).is_correct.agg(['sum','count'])
    clean=dict(orig); clean['global_mean']=g
    clean['objective_counts']={str(k):int(v) for k,v in agg['count'].items()}
    clean['objective_sums']={str(k):float(v) for k,v in agg['sum'].items()}
    clean['rows']=int(len(train)); clean['v176_note']='manifest aggregates rebuilt from deterministic session-complement only; base/related/stack assets intentionally frozen for causal ablation'

    y=test.is_correct.to_numpy(int)
    # Pure complement prior for reference.
    pp=(agg['sum']+2*g)/(agg['count']+2)
    pure=np.clip(test[objcol].map(pp).fillna(g).to_numpy(float),1e-6,1-1e-6)
    pure_ll=float(log_loss(y,pure)); pure_auc=float(roc_auc_score(y,pure))

    variants=[run_variant(a,clean,test) for a in ALPHAS]
    good=[r for r in variants if r.get('returncode')==0]
    best=min(good,key=lambda r:r['logloss']) if good else None
    original_v174=0.49088
    result={'protocol':'V176_MANIFEST_ONLY_DECONTAMINATION','sample_rows':len(test),'complement_rows':len(train),'sample_sessions':int(test.session_id.nunique()),
            'original_v174_full_asset_logloss_approx':original_v174,'clean_manifest_global_mean':g,'pure_complement_prior_alpha2_logloss':pure_ll,'pure_complement_prior_alpha2_auc':pure_auc,
            'variants':variants,'best':best,
            'interpretation':'Only manifest objective counts/sums/global mean are decontaminated. V75/related/stack coefficients remain full-data by design, so this measures the causal contribution of manifest leakage but is not yet a fully clean model estimate.'}
    if best:
        delta=best['logloss']-original_v174; result['delta_vs_v174']=delta
        if delta>=0.02: result['decision']='MANIFEST_LEAKAGE_MAJOR'
        elif delta>=0.005: result['decision']='MANIFEST_LEAKAGE_MATERIAL_BUT_NOT_DOMINANT'
        else: result['decision']='MANIFEST_LEAKAGE_SMALL__MODEL_ASSETS_DOMINATE'
    else: result['decision']='RUNTIME_VARIANTS_FAILED'
    result['residual']='Next rebuild V75, related, and stack coefficients on complement only; retain exact same 1500-row sample.'
    (OUT/'v176_results.json').write_text(json.dumps(result,indent=2)); (OUT/'clean_manifest.json').write_text(json.dumps(clean,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
