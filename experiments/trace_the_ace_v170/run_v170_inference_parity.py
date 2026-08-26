#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

# Reuse canonical offline implementation already preserved in repo.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--features', required=True)
    ap.add_argument('--labels', required=True)
    ap.add_argument('--transcripts', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    X=pd.read_csv(args.features); ydf=pd.read_csv(args.labels)
    print('FEATURE_HEADERS', list(X.columns)); print('LABEL_HEADERS', list(ydf.columns))
    df=X.merge(ydf,on='response_id',validate='one_to_one')

    # Locate recovered production package on persistent workspace.
    candidates=[]
    for base in [Path('/workspace'), Path('/workspace/trace_the_ace'), Path('/workspace/trace-ace-work')]:
        if base.exists():
            for p in base.rglob('main.py'):
                try:
                    txt=p.read_text(errors='ignore')
                except Exception: continue
                if '/code_execution/submission.csv' in txt or 'submission.csv' in txt:
                    candidates.append(p)
    # Also inspect zip archives for main.py and extract best-looking package.
    import zipfile, tempfile, shutil
    zips=[]
    for base in [Path('/workspace'),Path('/workspace/trace_the_ace')]:
        if base.exists(): zips += list(base.rglob('*.zip'))
    extract=Path('/workspace/trace-ace-work/v170_recovered'); extract.mkdir(parents=True,exist_ok=True)
    for z in zips:
        try:
            with zipfile.ZipFile(z) as q:
                names=q.namelist()
                if 'main.py' in names and any('v75_canonical_trajectory.py' in n for n in names):
                    d=extract/z.stem; d.mkdir(parents=True,exist_ok=True); q.extractall(d); candidates.append(d/'main.py')
        except Exception: pass
    print('PRODUCTION_MAIN_CANDIDATES',[str(x) for x in candidates])

    # Structural parity audit: compare production and canonical V75 source equations.
    prod_text='\n'.join(p.read_text(errors='ignore') for p in candidates[:5])
    v75s=list(ROOT.rglob('v75_canonical_trajectory.py'))
    canon_text=v75s[0].read_text(errors='ignore') if v75s else ''
    keys=['prior_alpha','trajectory','objective','sigmoid','logit','clip','predict','feedback','recency']
    structural={k:{'production_count':prod_text.lower().count(k),'canonical_count':canon_text.lower().count(k)} for k in keys}

    # Recover any saved V154/V157/V75 result prediction arrays/CSVs and measure parity if available.
    pred_files=[]
    for base in [Path('/workspace/trace-ace-results'),Path('/workspace/trace-ace-work')]:
        if base.exists():
            for p in base.rglob('*'):
                if p.is_file() and p.suffix.lower() in ['.csv','.npz','.npy'] and any(s in p.name.lower() for s in ['pred','oof','submission']): pred_files.append(p)
    print('PREDICTION_ARTIFACTS',[str(x) for x in pred_files[:100]])

    # Most decisive currently available test: recompute objective-prior production baseline from recovered manifest/assets
    # and compare its in-sample LL to known offline/public scales. This identifies whether offline metric is OOF vs fitted-runtime.
    global_mean=float(df.is_correct.mean())
    obj=df.groupby('learning_objective_id').is_correct.agg(['sum','count'])
    prior10=(obj['sum']+10*global_mean)/(obj['count']+10)
    prior2=(obj['sum']+2*global_mean)/(obj['count']+2)
    p10=df.learning_objective_id.map(prior10).fillna(global_mean).to_numpy()
    p2=df.learning_objective_id.map(prior2).fillna(global_mean).to_numpy()
    metrics={'global_ll':float(log_loss(df.is_correct,np.full(len(df),global_mean))),
             'fullfit_objective_prior_alpha10_ll':float(log_loss(df.is_correct,np.clip(p10,1e-6,1-1e-6))),
             'fullfit_objective_prior_alpha2_ll':float(log_loss(df.is_correct,np.clip(p2,1e-6,1-1e-6))),
             'known_public_v154_v157_ll':0.6037,
             'known_offline_v75_scale_ll':0.5457}
    result={'protocol':'V170_INFERENCE_EQUATION_PARITY_SEPARATOR','rows':len(df),'production_main_candidates':[str(x) for x in candidates],
            'canonical_v75_files':[str(x) for x in v75s], 'structural_source_comparison':structural,
            'prediction_artifacts':[str(x) for x in pred_files], 'metrics':metrics}
    if pred_files:
        result['decision']='PREDICTION_ARTIFACTS_FOUND__NEXT_ROW_PARITY'
        result['residual']='Saved predictions exist; directly align and diff them against recovered runtime outputs.'
    elif not candidates:
        result['decision']='RECOVERED_RUNTIME_NOT_MOUNTED'
        result['residual']='Need recovered V157 zip materialized onto persistent workspace.'
    else:
        result['decision']='SOURCE_CONTRACT_FOUND_BUT_NO_SAVED_ROW_PREDICTIONS'
        result['residual']='Execute recovered runtime against a train-shaped harness or reconstruct its predictor function, then row-diff against canonical V75 OOF.'
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
