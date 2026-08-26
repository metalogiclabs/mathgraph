#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

SEED=20260827

def headers(p: Path):
    return list(pd.read_csv(p,nrows=0).columns)

def jsd_from_counts(a,b):
    keys=sorted(set(a)|set(b)); pa=np.array([a.get(k,0) for k in keys],float); pb=np.array([b.get(k,0) for k in keys],float)
    pa/=pa.sum(); pb/=pb.sum(); m=.5*(pa+pb)
    def kl(p,q):
        z=p>0; return float(np.sum(p[z]*np.log(p[z]/q[z])))
    return .5*kl(pa,m)+.5*kl(pb,m)

def counts(x):
    return pd.Series(x).astype(str).value_counts().to_dict()

def find_artifacts(root: Path):
    hits=[]
    if not root.exists(): return hits
    for p in root.rglob('*'):
        if not p.is_file(): continue
        n=p.name.lower()
        if any(t in n for t in ('submission','predict','runtime','portable')) or n.endswith('.zip'):
            try: sz=p.stat().st_size
            except: sz=-1
            hits.append({'path':str(p),'bytes':sz})
            if len(hits)>=200: break
    return hits

def collect_results(root: Path):
    out=[]
    if not root.exists(): return out
    for p in root.rglob('*.json'):
        try: d=json.loads(p.read_text())
        except: continue
        row={'path':str(p),'protocol':d.get('protocol'),'decision':d.get('decision')}
        for k in ('session','objective_cold','small_v75','full_v75','small_v75_prior','full_v75_prior'):
            v=d.get(k)
            if isinstance(v,dict):
                for mk in ('logloss','base_logloss','graph_logloss','mixture_logloss','improvement','auc','base_auc','graph_auc','mixture_auc'):
                    if mk in v: row[f'{k}.{mk}']=v[mk]
        for k in ('scale_gain','grafted_scale_gain','full_prior_gain','separator'): 
            if k in d: row[k]=d[k]
        out.append(row)
    return out

def main(a):
    print('FEATURE_HEADERS',headers(a.features),flush=True)
    print('LABEL_HEADERS',headers(a.labels),flush=True)
    f=pd.read_csv(a.features); l=pd.read_csv(a.labels)
    frame=f.merge(l[['response_id','is_correct']],on='response_id',validate='one_to_one')
    rng=np.random.default_rng(SEED)
    ix=np.sort(rng.choice(len(frame),size=min(8000,len(frame)),replace=False))
    small=frame.iloc[ix]
    objcol='learning_objective_id' if 'learning_objective_id' in frame else 'learning_objective'
    full_obj=counts(frame[objcol]); small_obj=counts(small[objcol])
    dist={
      'full_rows':len(frame),'small_rows':len(small),
      'full_sessions':int(frame.session_id.nunique()),'small_sessions':int(small.session_id.nunique()),
      'full_objectives':int(frame[objcol].nunique()),'small_objectives':int(small[objcol].nunique()),
      'full_positive_rate':float(frame.is_correct.mean()),'small_positive_rate':float(small.is_correct.mean()),
      'objective_jsd_8k_vs_full':jsd_from_counts(small_obj,full_obj),
      'objectives_absent_from_8k':int(len(set(full_obj)-set(small_obj))),
    }
    results=collect_results(a.results)
    artifacts=find_artifacts(a.workspace)
    source_facts={
      'v154_is_triage_only': True,
      'v154_warning':'TRIAGE_ONLY_NOT_SUBMISSION_EVIDENCE',
      'v162_validation':'single GroupShuffleSplit session-cold holdout; not leaderboard-distribution evidence',
      'v165_v166_base':'full-data session-grouped offline base around 0.5457; not itself a submitted runtime score',
      'known_public_v154_v157_score':0.6037,
    }
    # Extract strongest observed full-data offline base from available results.
    offline=[]
    for r in results:
        for k,v in r.items():
            if isinstance(v,(int,float)) and ('base_logloss' in k or k.endswith('.logloss')):
                if 0<v<2: offline.append((float(v),r.get('protocol'),k,r.get('path')))
    offline.sort()
    best_offline=offline[0] if offline else None
    gap=(source_facts['known_public_v154_v157_score']-best_offline[0]) if best_offline else None
    production_like=[x for x in artifacts if any(t in Path(x['path']).name.lower() for t in ('submission','predict','runtime','portable'))]
    if gap is not None and gap>0.02:
        decision='CV_TO_PRODUCTION_MISMATCH_IS_PRIMARY_RESIDUAL'
    elif not production_like:
        decision='NO_CURRENT_PRODUCTION_ARTIFACT_TO_VALIDATE'
    else:
        decision='ALIGNMENT_GAP_NOT_LARGE'
    out={
      'protocol':'V167_CV_PRODUCTION_ALIGNMENT_AUDIT',
      'distribution':dist,
      'source_facts':source_facts,
      'best_offline_metric':best_offline,
      'public_minus_best_offline_gap':gap,
      'result_inventory':results,
      'production_artifact_candidates':production_like[:50],
      'decision':decision,
      'next_if_mismatch':'Stop treating offline 0.545x as submission evidence. Reconstruct the exact last scored runtime, then port the full-data V75 feature/model path into that identical inference contract and smoke-test it end-to-end before any more representation work.'
    }
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--features',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--results',type=Path,required=True); p.add_argument('--workspace',type=Path,required=True); p.add_argument('--out',type=Path,required=True); main(p.parse_args())
