#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

HERE=Path(__file__).resolve().parent
V146=HERE.parent/'trace_the_ace_v146'
sys.path.insert(0,str(V146))
from run_v146_residual_router import load_bundle, fit_base, inner_oof_base

SPLITS=('full_session','full_objective','control_session','control_objective')

def select_split(name,X,y,sg,og,ci):
    if name=='full_session': return X,y,np.asarray(sg).astype(str),np.arange(len(y),dtype=np.int64)
    if name=='full_objective': return X,y,np.asarray(og).astype(str),np.arange(len(y),dtype=np.int64)
    if name=='control_session': return X[ci],y[ci],np.asarray(sg)[ci].astype(str),np.asarray(ci,dtype=np.int64)
    if name=='control_objective': return X[ci],y[ci],np.asarray(og)[ci].astype(str),np.asarray(ci,dtype=np.int64)
    raise ValueError(name)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--bundle',type=Path,required=True); p.add_argument('--split',choices=SPLITS,required=True); p.add_argument('--fold',type=int,choices=range(1,6),required=True); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    X,_S,y,sg,og,ci,_Sswap,_Sempty=load_bundle(a.bundle.resolve())
    Xs,ys,groups,source_index=select_split(a.split,X,y,sg,og,ci)
    groups=np.asarray(pd.Series(groups).astype(str))
    folds=list(GroupKFold(5).split(np.zeros(len(ys)),ys,groups))
    tr,va=folds[a.fold-1]
    t0=time.time()
    p_inner=inner_oof_base(Xs[tr],ys[tr],groups[tr])
    base=fit_base(Xs[tr],ys[tr]); pb=np.clip(base.predict_proba(Xs[va])[:,1],1e-5,1-1e-5)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(a.out,
        protocol=np.asarray('V148B_FOLD_PARALLEL_V75_CROSSFIT_CACHE'), split=np.asarray(a.split), fold=np.asarray(a.fold),
        source_index=source_index, y=np.asarray(ys,dtype=np.int8), groups=groups.astype(object),
        tr=np.asarray(tr,dtype=np.int64), va=np.asarray(va,dtype=np.int64),
        p_inner=np.asarray(p_inner,dtype=np.float64), p_heldout=np.asarray(pb,dtype=np.float64))
    print(json.dumps({'split':a.split,'fold':a.fold,'rows':len(ys),'train_rows':len(tr),'valid_rows':len(va),'seconds':time.time()-t0,'bytes':a.out.stat().st_size},indent=2),flush=True)
if __name__=='__main__': main()
