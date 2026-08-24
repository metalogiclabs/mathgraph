#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_v145_semantic_gate import FIELDS, choose_subset, compile_rows, resolve_transcripts
from v75_canonical_trajectory import SEED, load_training


def load_scores(path: Path) -> np.ndarray:
    rows=[]
    for line in path.read_text().splitlines():
        r=json.loads(line)
        rows.append([float(r[k]) for k in FIELDS])
    a=np.asarray(rows,dtype=np.float32)
    if not np.isfinite(a).all():
        raise ValueError(f"non-finite scores in {path}")
    return a


def main(a):
    frame=choose_subset(load_training(a.features,a.labels),a.limit)
    transcripts=resolve_transcripts(a.transcripts.resolve(),a.out.parent/"bundle_compile_work")
    views,numeric,_=compile_rows(frame,transcripts)
    S=load_scores(a.v145_work/"semantic_scores.jsonl")
    if len(S)!=len(frame):
        raise ValueError(f"semantic row mismatch {len(S)} != {len(frame)}")
    objective_groups=(frame.learning_objective_id if "learning_objective_id" in frame else frame.learning_objective).astype(str).to_numpy()
    rng=np.random.default_rng(SEED)
    ci=np.sort(rng.choice(len(frame),size=min(a.control_limit,len(frame)),replace=False))
    Sswap=load_scores(a.v145_work/"objective_swap_scores.jsonl")
    Sempty=load_scores(a.v145_work/"evidence_empty_scores.jsonl")
    if len(Sswap)!=len(ci) or len(Sempty)!=len(ci):
        raise ValueError("counterfactual row mismatch")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    payload={
        "y":frame.target.to_numpy(np.int8),
        "session_id":frame.session_id.astype(str).to_numpy(),
        "objective":frame.learning_objective.astype(str).to_numpy(),
        "objective_group":objective_groups,
        "numeric":np.asarray(numeric,dtype=np.float32),
        "semantic":S,
        "control_index":ci.astype(np.int32),
        "objective_swap":Sswap,
        "evidence_empty":Sempty,
    }
    for key in ("raw","student","local","canonical","terminal"):
        payload[f"view_{key}"]=np.asarray([v[key] for v in views],dtype=str)
    np.savez_compressed(a.out,**payload)
    print(json.dumps({"bundle":str(a.out),"rows":len(frame),"controls":len(ci),"bytes":a.out.stat().st_size},indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--features",type=Path,required=True)
    p.add_argument("--labels",type=Path,required=True)
    p.add_argument("--transcripts",type=Path,required=True)
    p.add_argument("--v145-work",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--limit",type=int,default=8000)
    p.add_argument("--control-limit",type=int,default=2500)
    main(p.parse_args())
