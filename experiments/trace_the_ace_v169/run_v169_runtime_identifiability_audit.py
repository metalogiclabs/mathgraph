#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss


def headers(p: Path):
    return list(pd.read_csv(p, nrows=0).columns)


def binary_entropy(p):
    p=np.clip(np.asarray(p,float),1e-12,1-1e-12)
    return -(p*np.log(p)+(1-p)*np.log(1-p))


def main(a):
    fh=headers(a.features); lh=headers(a.labels)
    print('FEATURE_HEADERS',fh,flush=True); print('LABEL_HEADERS',lh,flush=True)
    need={'response_id','session_id','learning_objective'}
    if not need.issubset(fh): raise ValueError(f'missing feature cols {sorted(need-set(fh))}')
    target='is_correct' if 'is_correct' in lh else ('correct' if 'correct' in lh else None)
    if target is None: raise ValueError(f'no target in labels: {lh}')
    f=pd.read_csv(a.features,dtype=str)
    y=pd.read_csv(a.labels)
    d=f.merge(y[['response_id',target]],on='response_id',validate='one_to_one').rename(columns={target:'target'})
    d['target']=d.target.astype(int)

    # Recovered V135/V157 runtime contract: the predictive feature builder consumes only
    # (session_id, learning_objective, full session transcript). response_id is used only
    # to merge predictions into submission_format. Therefore all rows with the same
    # (session_id, learning_objective) are observationally identical to that runtime.
    key=['session_id','learning_objective']
    g=d.groupby(key,dropna=False).target.agg(['size','sum','mean']).reset_index()
    g['mixed']=(g['sum']>0)&(g['sum']<g['size'])
    g['entropy']=binary_entropy(g['mean'])

    d2=d.merge(g[key+['size','mean','mixed']],on=key,how='left',validate='many_to_one')
    oracle=np.clip(d2['mean'].to_numpy(float),1e-6,1-1e-6)
    ll_oracle=float(log_loss(d2.target,oracle,labels=[0,1]))
    global_mean=float(d2.target.mean())
    ll_global=float(log_loss(d2.target,np.full(len(d2),global_mean),labels=[0,1]))

    dup_rows=int((d2['size']>1).sum())
    mixed_rows=int(d2['mixed'].sum())
    singleton_rows=int((d2['size']==1).sum())
    mixed_groups=int(g['mixed'].sum())
    duplicate_groups=int((g['size']>1).sum())

    # Within identical-runtime-state pairs, quantify how often labels disagree.
    pair_total=0; pair_disagree=0
    for r in g.itertuples(index=False):
        n=int(r.size); s=int(r.sum)
        if n<2: continue
        pair_total += n*(n-1)//2
        pair_disagree += s*(n-s)
    pair_disagreement=float(pair_disagree/pair_total) if pair_total else 0.0

    # Response IDs are not used by the recovered runtime. Record their apparent structure only.
    rid=d.response_id.astype(str)
    numeric_fraction=float(rid.str.contains(r'\d',regex=True).mean())
    contains_session_fraction=float(np.mean([str(s) in str(r) for s,r in zip(d.session_id,rid)]))

    summary={
      'protocol':'V169_RUNTIME_IDENTIFIABILITY_AUDIT',
      'runtime_contract':{
        'recovered_v135_sha256':'12e1d73c725d21830687d32cf6e9e1a8d81feb767ce3e1b23000e5a01cb4996a',
        'recovered_v157_sha256':'bfa377ea070782880dc848a49451d65fe4fbededcbda83bd464aa17a77174db6',
        'learned_assets_identical_v135_v144_v157':True,
        'prediction_state_key':['session_id','learning_objective','full_session_transcript'],
        'response_id_used_as_predictive_feature':False,
      },
      'rows':int(len(d)), 'sessions':int(d.session_id.nunique()),
      'objectives':int(d.learning_objective.nunique()),
      'runtime_state_groups':int(len(g)),
      'singleton_rows':singleton_rows,
      'duplicate_state_rows':dup_rows,
      'duplicate_state_row_fraction':float(dup_rows/len(d)),
      'duplicate_state_groups':duplicate_groups,
      'mixed_label_state_groups':mixed_groups,
      'mixed_label_state_rows':mixed_rows,
      'mixed_label_state_row_fraction':float(mixed_rows/len(d)),
      'identical_state_pair_label_disagreement':pair_disagreement,
      'runtime_state_oracle_logloss_in_sample':ll_oracle,
      'global_mean_logloss':ll_global,
      'response_id_structure':{
        'contains_numeric_fraction':numeric_fraction,
        'contains_session_id_fraction':contains_session_fraction,
      },
      'largest_state_multiplicity':int(g['size'].max()),
      'median_state_multiplicity':float(g['size'].median()),
      'p95_state_multiplicity':float(g['size'].quantile(.95)),
    }

    # Decision is about representational identifiability, not leaderboard performance.
    if mixed_rows/len(d) >= .10:
        summary['decision']='RESPONSE_LOCAL_IDENTITY_MISSING_FROM_PRODUCTION_RUNTIME'
        summary['residual']='A material fraction of labels differ among rows that V157 maps to exactly the same observable state. The next production representation must expose a lawful response-local/ordinal key; more fitting on the existing runtime state cannot recover that information.'
    elif dup_rows/len(d) >= .25:
        summary['decision']='PRODUCTION_RUNTIME_COLLAPSES_MANY_RESPONSE_ROWS'
        summary['residual']='Many scored rows share the same runtime state. Test a lawful response-local alignment before further model tuning.'
    else:
        summary['decision']='STATE_COLLAPSE_NOT_PRIMARY'
        summary['residual']='The recovered runtime state is mostly row-identifying; seek another production mismatch.'

    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--features',type=Path,required=True)
    p.add_argument('--labels',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
