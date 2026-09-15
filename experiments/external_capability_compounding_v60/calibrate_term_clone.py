#!/usr/bin/env python3
"""V60 opened-data calibration of term-defined operation constructors.

Training: V58-opened rows 2628:2756 from both external datasets.
Validation: later V59-opened rows 2756:2820 from both datasets.
Fresh rows >= 2820 are not read here.

From each retained finite magma M, derive new magma operations by interpreting
small binary terms t(x,y) in M. The grammar is every binary term with at most
two uses of the parent operation. This yields exactly 22 constructor programs.
Constructor selection uses TRAIN only; validation is report-only.
"""

from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAL = ROOT / "experiments" / "external_capability_compounding_v59" / "calibrate_neighborhood.py"
spec = importlib.util.spec_from_file_location("v60_cal", CAL)
mod = importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
V58P = ROOT / "experiments" / "external_capability_compounding_v58" / "run.py"
spec2 = importlib.util.spec_from_file_location("v60_v58", V58P)
v58 = importlib.util.module_from_spec(spec2); sys.modules[spec2.name]=v58; spec2.loader.exec_module(v58)

TRAIN_START, TRAIN_COUNT = 2628, 128
VALID_START, VALID_COUNT = 2756, 64
MAX_OP_NODES = 2
MAX_SELECTED = 6
COLD_MS = 900
SEED_SHA = "241f6223899b6decf77767d0ec182920417b65217846f8b68e24d7a13b2bd535"

def term_key(t):
    if isinstance(t,str): return t
    return f"m({term_key(t[1])},{term_key(t[2])})"

def terms_exact(k):
    if k==0: return ["x","y"]
    out=[]
    for i in range(k):
        j=k-1-i
        for a in terms_exact(i):
            for b in terms_exact(j):
                out.append(("m",a,b))
    uniq={term_key(t):t for t in out}
    return [uniq[k] for k in sorted(uniq)]

TERMS=[]
for k in range(MAX_OP_NODES+1):
    TERMS.extend(terms_exact(k))
TERMS={term_key(t):t for t in TERMS}

def eval_term(t,parent,x,y):
    if t=="x": return x
    if t=="y": return y
    return parent[eval_term(t[1],parent,x,y)][eval_term(t[2],parent,x,y)]

def derive(parent,t):
    p=mod.table_tuple(parent); n=len(p)
    return tuple(tuple(eval_term(t,p,i,j) for j in range(n)) for i in range(n))

def read_slice(path,start,count):
    lines=Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines[start:start+count]]

def direct_solves(problem,parents):
    return any(mod.solves(problem,p["table"]) for p in parents)

def derived_solves(problem,parents,t):
    for p in parents:
        child=derive(p["table"],t)
        if child == mod.table_tuple(p["table"]):
            continue
        if mod.solves(problem,child):
            return p, child
    return None

def cid(table):
    return hashlib.sha256(json.dumps([list(r) for r in table],separators=(",",":")).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--book3000",required=True); ap.add_argument("--book3500",required=True)
    ap.add_argument("--seed",required=True); ap.add_argument("--out",required=True)
    args=ap.parse_args()

    raw=Path(args.seed).read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    if sha != SEED_SHA: raise RuntimeError(f"seed hash mismatch {sha}")
    parents=json.loads(raw)["capabilities"]
    if len(parents)!=18: raise RuntimeError("expected 18 V58 capabilities")

    train=read_slice(args.book3000,TRAIN_START,TRAIN_COUNT)+read_slice(args.book3500,TRAIN_START,TRAIN_COUNT)
    valid=read_slice(args.book3000,VALID_START,VALID_COUNT)+read_slice(args.book3500,VALID_START,VALID_COUNT)

    train_baseline={p["id"] for p in train if direct_solves(p,parents)}
    coverage={}
    witnesses={}
    for key,t in TERMS.items():
        hits=set(); ws=[]
        for problem in train:
            if problem["id"] in train_baseline: continue
            r=derived_solves(problem,parents,t)
            if r is not None:
                parent,child=r; hits.add(problem["id"])
                if len(ws)<8: ws.append({"problem_id":problem["id"],"parent_cid":parent["cid"],"child_cid":cid(child)})
        coverage[key]=hits; witnesses[key]=ws

    selected=[]; uncovered=set(p["id"] for p in train)-train_baseline
    covered=set()
    for _ in range(MAX_SELECTED):
        choices=[]
        for key in TERMS:
            if key in selected: continue
            gain=len(coverage[key]-covered)
            choices.append((gain,-key.count("m("),key))
        choices.sort(reverse=True)
        gain,_,best=choices[0]
        if gain<=0: break
        selected.append(best); covered |= coverage[best]

    valid_baseline={p["id"] for p in valid if direct_solves(p,parents)}
    validation=[]
    for problem in valid:
        if problem["id"] in valid_baseline: continue
        winner=None
        for key in selected:
            r=derived_solves(problem,parents,TERMS[key])
            if r is not None:
                parent,child=r; winner=(key,parent,child); break
        if winner is None: continue
        key,parent,child=winner
        cold=v58.cvc5_construct(problem,timeout_ms=COLD_MS)
        validation.append({
            "problem_id":problem["id"],"term":key,"parent_cid":parent["cid"],"child_cid":cid(child),
            "cold_status":cold.status,"cold_ms":cold.elapsed_ms,
        })
        print(json.dumps(validation[-1],sort_keys=True),flush=True)

    cold_miss=sum(x["cold_status"]!="VERIFIED_FALSE" for x in validation)
    selected_doc=[{
        "term":k,
        "train_novel_coverage":len(coverage[k]),
        "train_witnesses":witnesses[k],
    } for k in selected]
    memory={
        "schema":"mathgraph.term-clone-memory.v60",
        "parent_archive_sha256":SEED_SHA,
        "max_op_nodes":MAX_OP_NODES,
        "selected_terms":selected_doc,
        "selection_basis":"greedy novel coverage on V58-opened train rows only",
    }
    mem_raw=json.dumps(memory,sort_keys=True,separators=(",",":")).encode()
    memory["sha256"]=hashlib.sha256(mem_raw).hexdigest()

    checks={
        "grammar_exact_22":len(TERMS)==22,
        "train_has_novel_term_coverage":len(covered)>0,
        "selected_nonempty":len(selected)>0,
        "validation_novel_transfer":len(validation)>0,
        "validation_same_budget_cold_miss":cold_miss>0,
    }
    result={
        "schema":"mathgraph.external-capability-compounding.v60.calibration",
        "classification":"OPENED_DATA_TRAIN_VALIDATION_NOT_FRESH_EVIDENCE",
        "grammar_terms":len(TERMS),"selected_terms":selected_doc,
        "train_tasks":len(train),"train_direct_baseline":len(train_baseline),"train_novel_covered":len(covered),
        "validation_tasks":len(valid),"validation_direct_baseline":len(valid_baseline),
        "validation_novel_hits":len(validation),"validation_cold_misses":cold_miss,
        "validation_examples":validation[:20],"checks":checks,"all_checks_pass":all(checks.values()),
        "memory_sha256":memory["sha256"],
    }
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    (out/"constructor_memory.json").write_text(json.dumps(memory,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True),flush=True)
    if not result["all_checks_pass"]: raise SystemExit("V60 calibration failed")

if __name__=="__main__": main()
