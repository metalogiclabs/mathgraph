#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

HERE=Path(__file__).resolve().parent
V146=HERE.parent/'trace_the_ace_v146'
sys.path.insert(0,str(V146))
from run_v146_residual_router import load_bundle, diagnostics, choose_router, safe_logit
V147=HERE.parent/'trace_the_ace_v147'
sys.path.insert(0,str(V147))
from run_v147_comparative_router import features, choose_policy
V145=HERE.parent/'trace_the_ace_v145'
sys.path.insert(0,str(V145))
from run_v145_semantic_gate import FIELDS, grouped_bootstrap_improvement
from v75_canonical_trajectory import SEED

SPLITS=('full_session','full_objective','control_session','control_objective')


def load_cache(root:Path,name:str):
    b=np.load(root/f'{name}.npz',allow_pickle=True)
    folds=[]
    for k in range(1,6):
        folds.append({
            'fold':k,
            'tr':b[f'fold{k}_tr'].astype(int),
            'va':b[f'fold{k}_va'].astype(int),
            'p_inner':b[f'fold{k}_p_inner'].astype(float),
            'pb':b[f'fold{k}_p_heldout'].astype(float),
        })
    return {
        'groups':b['groups'].astype(str),
        'y':b['y'].astype(int),
        'source_index':b['source_index'].astype(int),
        'folds':folds,
    }


def evaluate_continuous(S,cache):
    y=cache['y']; groups=cache['groups']; n=len(y)
    p0=np.zeros(n); p1=np.zeros(n); folds=[]; cover=[]; params=[]
    for it in cache['folds']:
        k,tr,va=it['fold'],it['tr'],it['va']
        sc=StandardScaler().fit(S[tr]); Str=sc.transform(S[tr]); Sva=sc.transform(S[va])
        router,par=choose_router(it['p_inner'],y[tr],diagnostics(it['p_inner'],Str))
        d=router.predict(diagnostics(it['pb'],Sva)); gate=np.abs(d)>=par['threshold']
        pr=expit(safe_logit(it['pb'])+par['lambda']*d*gate)
        p0[va]=it['pb']; p1[va]=pr; cover.append(float(gate.mean())); params.append(par)
        folds.append({'fold':k,'base':float(log_loss(y[va],it['pb'])),'routed':float(log_loss(y[va],pr)),'coverage':float(gate.mean())})
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {'base_logloss':ll0,'routed_logloss':ll1,'improvement':ll0-ll1,
            'base_auc':float(roc_auc_score(y,p0)),'routed_auc':float(roc_auc_score(y,p1)),
            'bootstrap_improvement_95':grouped_bootstrap_improvement(y,p0,p1,groups),
            'fold_wins':int(sum(f['routed']<f['base'] for f in folds)),
            'mean_coverage':float(np.mean(cover)),'folds':folds,'router_params':params}


def evaluate_comparative(S,cache):
    y=cache['y']; groups=cache['groups']; n=len(y)
    p0=np.zeros(n); p1=np.zeros(n); folds=[]; counts=np.zeros(3,dtype=int)
    for it in cache['folds']:
        k,tr,va=it['fold'],it['tr'],it['va']
        sc=StandardScaler().fit(S[tr]); Str=sc.transform(S[tr]); Sva=sc.transform(S[va])
        clf,par=choose_policy(it['p_inner'],y[tr],features(it['p_inner'],Str))
        act=clf.predict(features(it['pb'],Sva)); counts += np.bincount(act,minlength=3)
        shift=np.where(act==0,-par['delta'],np.where(act==2,par['delta'],0.0))
        pr=expit(safe_logit(it['pb'])+shift)
        p0[va]=it['pb']; p1[va]=pr
        folds.append({'fold':k,'base':float(log_loss(y[va],it['pb'])),'comparative':float(log_loss(y[va],pr)),
                      'params':par,'actions':{'down':int((act==0).sum()),'keep':int((act==1).sum()),'up':int((act==2).sum())}})
    ll0=float(log_loss(y,p0)); ll1=float(log_loss(y,p1))
    return {'base_logloss':ll0,'comparative_logloss':ll1,'improvement':ll0-ll1,
            'base_auc':float(roc_auc_score(y,p0)),'comparative_auc':float(roc_auc_score(y,p1)),
            'bootstrap_improvement_95':grouped_bootstrap_improvement(y,p0,p1,groups),
            'fold_wins':int(sum(f['comparative']<f['base'] for f in folds)),
            'actions':{'down':int(counts[0]),'keep':int(counts[1]),'up':int(counts[2])},'folds':folds}


def main(a):
    X,S,y,sg,og,ci,Sswap,Sempty=load_bundle(a.bundle.resolve())
    root=a.cache.resolve()
    caches={s:load_cache(root,s) for s in SPLITS}
    rng=np.random.default_rng(SEED); shuffled=S[rng.permutation(len(S))]

    # Integrity: durable caches must map exactly to the frozen bundle labels.
    assert np.array_equal(caches['full_session']['y'],y)
    assert np.array_equal(caches['full_objective']['y'],y)
    assert np.array_equal(caches['control_session']['source_index'],ci)
    assert np.array_equal(caches['control_objective']['source_index'],ci)

    out={'protocol':'V149_FROZEN_V75_CROSSFIT_ROUTER_REPLAY','rows':len(y),'fields':FIELDS,
         'continuous':{},'comparative':{}}
    for mode,fn in [('continuous',evaluate_continuous),('comparative',evaluate_comparative)]:
        out[mode]['session']=fn(S,caches['full_session'])
        out[mode]['objective']=fn(S,caches['full_objective'])
        out[mode]['shuffled']={
            'session':fn(shuffled,caches['full_session']),
            'objective':fn(shuffled,caches['full_objective'])}
        out[mode]['counterfactual_controls']={}
        for name,Sc in [('objective_swap',Sswap),('evidence_empty',Sempty)]:
            out[mode]['counterfactual_controls'][name]={
                'session':fn(Sc,caches['control_session']),
                'objective':fn(Sc,caches['control_objective'])}

    c=out['continuous']; s,o=c['session'],c['objective']; ss,so=c['shuffled']['session'],c['shuffled']['objective']
    controls_ok=all(c[split]['improvement']>c['counterfactual_controls'][ctrl][split]['improvement']
                    for split in ('session','objective') for ctrl in ('objective_swap','evidence_empty'))
    promote=(o['improvement']>=.001 and s['improvement']>=.0002 and o['fold_wins']>=4 and s['fold_wins']>=3
             and o['bootstrap_improvement_95'][0]>0 and s['bootstrap_improvement_95'][0]>=0
             and o['improvement']>so['improvement']+.0005 and s['improvement']>ss['improvement']+.0002 and controls_ok)
    out['continuous_decision']='PROMOTE_TO_SUBMISSION_CANDIDATE' if promote else 'DO_NOT_SPEND_SUBMISSION'

    q=out['comparative']; qs,qo=q['session'],q['objective']
    signal=(qo['improvement']>q['shuffled']['objective']['improvement'] and qs['improvement']>q['shuffled']['session']['improvement'])
    robust=(qo['improvement']>0 and qs['improvement']>0 and qo['fold_wins']>=4 and qs['fold_wins']>=3 and signal)
    out['comparative_decision']='COMPARATIVE_SIGNAL' if robust else 'NO_COMPARATIVE_SIGNAL'

    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--cache',type=Path,required=True); p.add_argument('--out',type=Path,default=Path('v149_results.json')); a=p.parse_args(); main(a)
