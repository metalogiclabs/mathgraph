#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, zipfile, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score

WS=Path('/workspace')
ZIP=WS/'V157_RECOVERED_SUBMISSION.zip'
OUT=WS/'trace-ace-results/v174'
EX=WS/'trace-ace-work/v174_v157'
DATA=Path('/code_execution/data')
N_TARGET=1500

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert ZIP.exists(), ZIP
    if EX.exists(): shutil.rmtree(EX)
    EX.mkdir(parents=True)
    with zipfile.ZipFile(ZIP) as z: z.extractall(EX)
    main_py=EX/'main.py'; assert main_py.exists()

    feat=WS/'trace_the_ace/train_features_TMQTWsB.csv'
    lab=WS/'trace_the_ace/train_labels_44ujmj2.csv'
    trdir=WS/'trace_the_ace/transcripts_extracted'
    X=pd.read_csv(feat); Y=pd.read_csv(lab)
    print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    df=X.merge(Y,on='response_id',validate='one_to_one')

    sessions=(df.groupby('session_id').size().rename('n').reset_index())
    sessions['h']=sessions.session_id.astype(str).map(lambda s:int(hashlib.sha256(s.encode()).hexdigest()[:16],16))
    sessions=sessions.sort_values(['h','session_id'])
    chosen=[]; rows=0
    for r in sessions.itertuples(index=False):
        chosen.append(r.session_id); rows += int(r.n)
        if rows>=N_TARGET: break
    mask=df.session_id.isin(set(chosen))
    test=df.loc[mask].copy(); train=df.loc[~mask].copy()
    print('SAMPLE_ROWS',len(test),'SAMPLE_SESSIONS',test.session_id.nunique(),'TRAIN_ROWS',len(train))

    gm=float(train.is_correct.mean())
    obj=train.groupby('learning_objective_id').is_correct.agg(['sum','count'])
    prior10=(obj['sum']+10*gm)/(obj['count']+10)
    test['strict_prior']=np.clip(test.learning_objective_id.map(prior10).fillna(gm).to_numpy(float),1e-6,1-1e-6)
    y=test.is_correct.to_numpy(int)
    prior_ll=float(log_loss(y,test.strict_prior)); prior_auc=float(roc_auc_score(y,test.strict_prior))

    DATA.mkdir(parents=True,exist_ok=True)
    test[X.columns].to_csv(DATA/'test_features.csv',index=False)
    sf=test[['response_id']].copy(); sf['is_correct']=0.5
    sf.to_csv(DATA/'submission_format.csv',index=False)
    target=DATA/'test_transcripts'
    if target.is_symlink() or target.exists():
        if target.is_symlink() or target.is_file(): target.unlink()
        else: shutil.rmtree(target)
    os.symlink(trdir,target,target_is_directory=True)
    sub=Path('/code_execution/submission.csv')
    if sub.exists(): sub.unlink()

    proc=subprocess.run([sys.executable,str(main_py)],cwd=str(EX),text=True,capture_output=True,timeout=600)
    print('RETURN',proc.returncode)
    print('STDOUT_TAIL\n',proc.stdout[-5000:]); print('STDERR_TAIL\n',proc.stderr[-5000:])
    result={'protocol':'V174_BOUNDED_EXACT_V157_PRODUCTION_PARITY','sample_rows':len(test),'sample_sessions':int(test.session_id.nunique()),'complement_train_rows':len(train),'crossfit_prior_alpha':10,'crossfit_prior_logloss':prior_ll,'crossfit_prior_auc':prior_auc,'returncode':proc.returncode}
    if proc.returncode!=0 or not sub.exists():
        result.update(decision='BOUNDED_RUNTIME_EXECUTION_FAILED',residual='Runtime still fails or exceeds 10 minutes on 1500 rows; inspect performance hotspot rather than model.')
    else:
        P=pd.read_csv(sub); print('SUB_HEADERS',list(P.columns),'SUB_ROWS',len(P))
        pred_col='is_correct' if 'is_correct' in P.columns else [c for c in P.columns if c!='response_id'][0]
        Z=test[['response_id','is_correct','strict_prior']].merge(P[['response_id',pred_col]],on='response_id',validate='one_to_one')
        yy=Z['is_correct'].to_numpy(int); pp=np.clip(Z[pred_col].to_numpy(float),1e-6,1-1e-6)
        prod_ll=float(log_loss(yy,pp)); prod_auc=float(roc_auc_score(yy,pp)); exact_prior_ll=float(log_loss(yy,Z.strict_prior.to_numpy(float))); gap=prod_ll-exact_prior_ll
        result.update(production_logloss=prod_ll,production_auc=prod_auc,strict_prior_same_rows_logloss=exact_prior_ll,production_minus_strict_prior=gap,pred_mean=float(pp.mean()),pred_std=float(pp.std()),rows_returned=len(P),prediction_column=pred_col)
        if gap>0.02:
            result.update(decision='PRODUCTION_EQUATION_DESTROYS_SIGNAL',residual='Exact V157 runtime is materially worse than strict objective prior on identical bounded rows. Next: ablate runtime transforms and build production-safe prior baseline.')
        elif gap<=0.01:
            result.update(decision='PRODUCTION_RUNTIME_PRESERVES_SIGNAL',residual='V157 runtime is close to strict held-out prior on identical rows. Public gap points to hidden-test regime / distribution shift.')
        else:
            result.update(decision='MODERATE_RUNTIME_PENALTY',residual='Runtime loses 0.01-0.02 logloss versus strict prior; decompose prior shrinkage, trajectory and calibration transforms.')
        P.to_csv(OUT/'v174_production_predictions.csv',index=False)
        Z[['response_id','is_correct','strict_prior']].to_csv(OUT/'v174_strict_prior.csv',index=False)
    (OUT/'v174_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
