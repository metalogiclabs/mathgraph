#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

from run_v146_residual_router import load_bundle, evaluate
from v75_canonical_trajectory import SEED


def main(bundle: Path, out: Path, limit: int):
    X,S,y,session_groups,objective_groups,ci,Sswap,Sempty=load_bundle(bundle.resolve())
    n=len(y)
    if limit <= 0 or limit > n:
        limit=n
    rng=np.random.default_rng(SEED)
    take=np.sort(rng.permutation(n)[:limit])
    X=X[take]; S=S[take]; y=y[take]
    session_groups=session_groups[take]
    objective_groups=objective_groups[take]
    shuffled=S[rng.permutation(len(S))]
    results={
        "protocol":"V146_FAST_DIAGNOSTIC_ONLY",
        "rows":len(y),
        "note":"Triage only; not submission evidence and does not replace the preregistered V146 gate.",
        "session":evaluate("session",X,S,y,session_groups),
        "objective":evaluate("objective",X,S,y,objective_groups),
        "shuffled":{
            "session":evaluate("session_shuffled",X,shuffled,y,session_groups),
            "objective":evaluate("objective_shuffled",X,shuffled,y,objective_groups),
        },
    }
    results["signal_over_shuffle"]={
        split: results[split]["improvement"]-results["shuffled"][split]["improvement"]
        for split in ("session","objective")
    }
    out=out.resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path("v146_fast_results.json"))
    p.add_argument("--limit",type=int,default=2500)
    a=p.parse_args()
    main(a.bundle,a.out,a.limit)
