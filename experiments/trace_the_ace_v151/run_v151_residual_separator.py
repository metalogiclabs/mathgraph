#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, roc_auc_score

HERE = Path(__file__).resolve().parent
V150 = HERE.parent / 'trace_the_ace_v150'
V145 = HERE.parent / 'trace_the_ace_v145'
sys.path.insert(0, str(V150)); sys.path.insert(0, str(V145))
from run_v150_fast_phase_change import load_bundle, fit_base, predict_base, sem_features, choose_delta, safe_logit
from run_v145_semantic_gate import FIELDS

SEED = 1729


def build_base_cache(num, obj, y, groups):
    groups = np.asarray(groups).astype(str)
    folds = []
    for k, (tr, va) in enumerate(GroupKFold(5).split(np.zeros(len(y)), y, groups), 1):
        inner = np.zeros(len(tr))
        gtr = groups[tr]
        n = min(4, len(np.unique(gtr)))
        for itr, iva in GroupKFold(n).split(np.zeros(len(tr)), y[tr], gtr):
            bm = fit_base(num[tr][itr], obj[tr][itr], y[tr][itr])
            inner[iva] = predict_base(bm, num[tr][iva], obj[tr][iva])
        bm = fit_base(num[tr], obj[tr], y[tr])
        pb = predict_base(bm, num[va], obj[va])
        folds.append((k, tr, va, inner, pb))
    return folds


def eval_variant(S, y, folds):
    p0 = np.zeros(len(y)); p1 = np.zeros(len(y)); rows=[]
    for k,tr,va,inner,pb in folds:
        sc = StandardScaler().fit(S[tr]); Str=sc.transform(S[tr]); Sva=sc.transform(S[va])
        router, par = choose_delta(inner, y[tr], sem_features(inner, Str))
        d = router.predict(sem_features(pb, Sva)); gate = np.abs(d) >= par['threshold']
        pr = expit(safe_logit(pb) + par['lambda'] * d * gate)
        p0[va]=pb; p1[va]=pr
        rows.append({'fold':k,'base':float(log_loss(y[va],pb)),'routed':float(log_loss(y[va],pr)),'coverage':float(gate.mean())})
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {'base_logloss':ll0,'routed_logloss':ll1,'improvement':ll0-ll1,
            'base_auc':float(roc_auc_score(y,p0)),'routed_auc':float(roc_auc_score(y,p1)),
            'fold_wins':int(sum(r['routed']<r['base'] for r in rows)),'folds':rows}


def make_variants(real, empty, swap):
    out={'real':real,'empty':empty,'swap':swap}
    for a in (.25,.5,.75): out[f'empty_to_real_{a:.2f}']=empty + a*(real-empty)
    for j,f in enumerate(FIELDS):
        a=empty.copy(); a[:,j]=real[:,j]; out[f'empty_plus_{f}']=a
        b=real.copy(); b[:,j]=empty[:,j]; out[f'real_without_{f}']=b
    rng=np.random.default_rng(SEED)
    out['empty_plus_shuffled_evidence_delta']=empty + (real-empty)[rng.permutation(len(real))]
    return out


def main(a):
    b=load_bundle(a.bundle.resolve()); ci=b['ci']
    y=b['y'][ci]; num=b['numeric'][ci]; obj=b['objective'][ci]
    real=b['S'][ci]; empty=b['Sempty']; swap=b['Sswap']
    variants=make_variants(real,empty,swap)
    caches={
      'session':build_base_cache(num,obj,y,b['session'][ci]),
      'objective':build_base_cache(num,obj,y,b['objective'][ci]),
    }
    results={}
    for name,S in variants.items():
        results[name]={}
        for split in ('session','objective'):
            results[name][split]=eval_variant(S,y,caches[split])
        print(name, results[name]['session']['improvement'], results[name]['objective']['improvement'], flush=True)
    ranking=sorted(results, key=lambda n:(results[n]['objective']['improvement'],results[n]['session']['improvement']), reverse=True)
    best=ranking[0]; eb=results['empty']; rb=results['real']; br=results[best]
    massive=(br['objective']['improvement']>=.003 and br['session']['improvement']>=.001 and br['objective']['fold_wins']>=4 and br['session']['fold_wins']>=3)
    separator=(br['objective']['improvement'] >= eb['objective']['improvement']+.0005 and br['session']['improvement'] >= eb['session']['improvement']-.0002)
    evidence_harm=(eb['objective']['improvement'] > rb['objective']['improvement']+.001)
    if massive: decision='PHASE_CHANGE_CANDIDATE'
    elif separator: decision='FIELD_SEPARATOR_FOUND'
    elif evidence_harm: decision='EVIDENCE_HARM_LOCALIZED_TO_PRIOR_VS_EVIDENCE'
    else: decision='NO_USEFUL_SEPARATOR'
    out={'protocol':'V151_RESIDUAL_RELATIVE_SEMANTIC_SEPARATOR','warning':'DISCOVERY_TRIAGE_NOT_SUBMISSION_EVIDENCE','rows':len(y),'fields':list(FIELDS),
         'residual':'V150 showed no global semantic phase change; test whether transcript evidence should split from the objective-conditioned prior and which semantic dimensions force that split.',
         'ranking':ranking,'best_variant':best,'results':results,'decision':decision}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps({'decision':decision,'best_variant':best,'best':br,'empty':eb,'real':rb},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v151_results.json')); main(p.parse_args())
