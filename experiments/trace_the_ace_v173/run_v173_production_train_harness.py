#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, zipfile
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import log_loss, roc_auc_score

WS=Path('/workspace')
ZIP=WS/'V157_RECOVERED_SUBMISSION.zip'
OUT=WS/'trace-ace-results/v173'
EX=WS/'trace-ace-work/v173_v157'
DATA=Path('/code_execution/data')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert ZIP.exists(), ZIP
    if EX.exists(): shutil.rmtree(EX)
    EX.mkdir(parents=True)
    with zipfile.ZipFile(ZIP) as z: z.extractall(EX)
    main_py=EX/'main.py'; assert main_py.exists()
    print('MAIN', main_py)

    feat=WS/'trace_the_ace/train_features_TMQTWsB.csv'
    lab=WS/'trace_the_ace/train_labels_44ujmj2.csv'
    trdir=WS/'trace_the_ace/transcripts_extracted'
    X=pd.read_csv(feat); Y=pd.read_csv(lab)
    print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    df=X.merge(Y,on='response_id',validate='one_to_one')

    # Build the competition filesystem exactly, but feed the known training rows as test rows.
    DATA.mkdir(parents=True,exist_ok=True)
    shutil.copy2(feat, DATA/'test_features.csv')
    sf=X[['response_id']].copy(); sf['is_correct']=0.5
    sf.to_csv(DATA/'submission_format.csv',index=False)
    target=DATA/'test_transcripts'
    if target.is_symlink() or target.exists():
        if target.is_symlink() or target.is_file(): target.unlink()
        else: shutil.rmtree(target)
    os.symlink(trdir,target,target_is_directory=True)
    sub=Path('/code_execution/submission.csv')
    if sub.exists(): sub.unlink()

    proc=subprocess.run([sys.executable,str(main_py)],cwd=str(EX),text=True,capture_output=True,timeout=1800)
    print('RETURN',proc.returncode)
    print('STDOUT\n',proc.stdout[-10000:]); print('STDERR\n',proc.stderr[-10000:])
    result={'protocol':'V173_EXACT_V157_PRODUCTION_TRAIN_SHAPED_HARNESS','returncode':proc.returncode}
    if proc.returncode!=0 or not sub.exists():
        result.update(decision='PRODUCTION_RUNTIME_EXECUTION_FAILED',residual='Patch only the harness/contract incompatibility; do not change model.')
    else:
        P=pd.read_csv(sub); print('SUB_HEADERS',list(P.columns)); print('SUB_ROWS',len(P))
        pred_col='is_correct' if 'is_correct' in P.columns else [c for c in P.columns if c!='response_id'][0]
        Z=df[['response_id','is_correct']].merge(P[['response_id',pred_col]],on='response_id',validate='one_to_one',suffixes=('_y','_p'))
        y=Z['is_correct_y'].to_numpy(); p=np.clip(Z[pred_col].to_numpy(float),1e-6,1-1e-6)
        prod_ll=float(log_loss(y,p)); prod_auc=float(roc_auc_score(y,p))
        gm=float(y.mean()); obj=df.groupby('learning_objective_id').is_correct.agg(['sum','count']); prior=(obj['sum']+2*gm)/(obj['count']+2); pp=np.clip(df.learning_objective_id.map(prior).fillna(gm).to_numpy(),1e-6,1-1e-6); prior_ll=float(log_loss(y,pp))
        result.update(rows=len(P),production_train_logloss=prod_ll,production_train_auc=prod_auc,alpha2_fullfit_prior_logloss=prior_ll,production_minus_prior=prod_ll-prior_ll,pred_mean=float(p.mean()),pred_std=float(p.std()))
        if prod_ll>prior_ll+0.02:
            result.update(decision='PRODUCTION_EQUATION_DESTROYS_OBJECTIVE_SIGNAL',residual='A large gap appears even on identical rows; ablate runtime transforms and retain the strongest production-safe equation.')
        elif prod_ll<=prior_ll+0.01:
            result.update(decision='PRODUCTION_EQUATION_PARITY_APPROXIMATELY_OK',residual='Runtime preserves train signal; public gap is primarily train-test shift / hidden test regime.')
        else:
            result.update(decision='MODERATE_PRODUCTION_EQUATION_PENALTY',residual='Decompose runtime terms by ablation before submission.')
        P.to_csv(OUT/'v173_production_predictions.csv',index=False)
    (OUT/'v173_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
