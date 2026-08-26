#!/usr/bin/env python3
import json, hashlib
from pathlib import Path
import pandas as pd

TRAIN='/workspace/trace_the_ace/train_features_TMQTWsB.csv'
OUT='/workspace/trace-ace-results/v172/v172_results.json'
roots=[Path('/workspace'),Path('/workspace/trace_the_ace'),Path('/workspace/trace-ace-work')]
train=pd.read_csv(TRAIN)
print('TRAIN_HEADERS',list(train.columns))
# Find candidate competition test feature files, excluding training CSVs.
cands=[]
for r in roots:
    if not r.exists(): continue
    for p in r.rglob('*.csv'):
        n=p.name.lower()
        if 'train_' in n or 'labels' in n: continue
        try:
            h=list(pd.read_csv(p,nrows=2).columns)
        except Exception: continue
        if 'learning_objective_id' in h and 'response_id' in h:
            cands.append((p,h))
print('TEST_CANDIDATES',[str(p) for p,_ in cands])
res={'protocol':'V172_TEST_OBJECTIVE_SHIFT_AUDIT','train_rows':len(train),'train_objectives':int(train.learning_objective_id.nunique()),'candidates':[]}
tr_freq=train.learning_objective_id.value_counts(normalize=True)
tr_ids=set(train.learning_objective_id.astype(str))
for p,h in cands:
    d=pd.read_csv(p)
    te_ids=set(d.learning_objective_id.astype(str))
    unseen=sorted(te_ids-tr_ids)
    te_freq=d.learning_objective_id.value_counts(normalize=True)
    all_ids=set(tr_freq.index.astype(str))|set(te_freq.index.astype(str))
    # string-key dictionaries for stable comparison
    tr={str(k):float(v) for k,v in tr_freq.items()}; te={str(k):float(v) for k,v in te_freq.items()}
    tv=0.5*sum(abs(tr.get(k,0)-te.get(k,0)) for k in all_ids)
    weighted_abs=sum(te.get(k,0)*abs(te.get(k,0)-tr.get(k,0)) for k in all_ids)
    rec={'path':str(p),'rows':len(d),'objectives':int(d.learning_objective_id.nunique()),'unseen_objectives':len(unseen),'unseen_ids':unseen[:100],
         'unseen_row_fraction':float(d.learning_objective_id.astype(str).isin(unseen).mean()) if unseen else 0.0,'objective_frequency_total_variation':float(tv),'weighted_abs_freq_shift':float(weighted_abs),
         'headers':h}
    res['candidates'].append(rec)
if not cands:
    res['decision']='ACTUAL_TEST_FEATURES_NOT_PRESENT'
    res['residual']='Need competition test_features.csv (or smoke-test equivalent) on /workspace to measure train-test objective shift.'
else:
    best=max(res['candidates'],key=lambda x:x['rows'])
    if best['unseen_row_fraction']>0.05 or best['objective_frequency_total_variation']>0.20:
        res['decision']='MATERIAL_OBJECTIVE_DISTRIBUTION_SHIFT'
        res['residual']='Test objective distribution differs materially; quantify whether prior shrinkage/robustification closes public gap.'
    else:
        res['decision']='OBJECTIVE_SHIFT_NOT_LARGE_ENOUGH'
        res['residual']='Objective coverage/frequency shift is not sufficient; execute recovered V157 inference equation on train-shaped heldout data next.'
Path(OUT).parent.mkdir(parents=True,exist_ok=True); Path(OUT).write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
