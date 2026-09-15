#!/usr/bin/env python3
"""Opened-only structural constructor diagnostic for V56.

Learns no fresh facts. The family grammar is frozen from structural statistics
of already-open V55 certificates:
  * row_constant_except_one
  * col_constant_except_one
  * at_most_two_row_templates
  * at_most_two_col_templates
  * idempotent_full

For each opened diagnostic case, only the equations and carrier size are given
to Z3. Any candidate is independently checked by MathGraph.
"""

from __future__ import annotations
import argparse, hashlib, importlib.util, itertools, json, sys, time
from pathlib import Path
from z3 import Array, Int, IntSort, Select, Solver, Bool, If, sat, unknown

EXPECTED_3000_SHA256="fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7"
EXPECTED_3500_SHA256="fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8"
CASES={
 "40732_to_3525":6,
 "40747_to_44433":6,
 "40790_to_60019":6,
 "39818_to_44162":5,
 "40736_to_3509":6,
 "11228_to_10358":5,
 "42486_to_46040":5,
 "834_to_22246":5,
}
FAMILIES=("row_exception","col_exception","two_rows","two_cols","idempotent")

_FMW_PATH=Path(__file__).resolve().parents[2]/"mathgraph"/"finite_magma_world.py"
_SPEC=importlib.util.spec_from_file_location("v56_structured_fmw",_FMW_PATH)
_FMW=importlib.util.module_from_spec(_SPEC); sys.modules[_SPEC.name]=_FMW; _SPEC.loader.exec_module(_FMW)

def norm(s):
 out=str(s)
 for op in ("◇","⋄","·","∙","∗","＊","×"): out=out.replace(op,"*")
 return out

def load(path,expected):
 data=Path(path).read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected: raise RuntimeError("dataset hash mismatch")
 return [json.loads(x) for x in data.decode().splitlines() if x.strip()]

def envs(names,n):
 for vals in itertools.product(range(n),repeat=len(names)): yield dict(zip(names,vals))

def ev(t,op,n,e):
 if t.name is not None:return e[t.name]
 return Select(op,ev(t.left,op,n,e)*n+ev(t.right,op,n,e))

def add_family(s,op,n,family,prefix):
 if family=="row_exception":
  # By carrier relabeling, the unique exceptional row can be named 0.
  for i in range(1,n):
   base=Select(op,i*n)
   for j in range(1,n): s.add(Select(op,i*n+j)==base)
 elif family=="col_exception":
  for j in range(1,n):
   base=Select(op,j)
   for i in range(1,n): s.add(Select(op,i*n+j)==base)
 elif family=="two_rows":
  cls=[Bool(f"{prefix}_r{i}") for i in range(n)]
  s.add(cls[0]); s.add(~cls[1])
  for i in range(n):
   for j in range(n):
    s.add(Select(op,i*n+j)==If(cls[i],Select(op,j),Select(op,n+j)))
 elif family=="two_cols":
  cls=[Bool(f"{prefix}_c{j}") for j in range(n)]
  s.add(cls[0]); s.add(~cls[1])
  for i in range(n):
   for j in range(n):
    s.add(Select(op,i*n+j)==If(cls[j],Select(op,i*n),Select(op,i*n+1)))
 elif family=="idempotent":
  for i in range(n): s.add(Select(op,i*n+i)==i)
 else: raise ValueError(family)

def solve(p,n,family,timeout_ms):
 src=_FMW.parse_equation(norm(p["equation1"])); tgt=_FMW.parse_equation(norm(p["equation2"]))
 op=Array(f"op_{p['id']}_{n}_{family}",IntSort(),IntSort())
 s=Solver(); s.set(timeout=timeout_ms)
 for k in range(n*n):
  v=Select(op,k); s.add(v>=0,v<n)
 add_family(s,op,n,family,p["id"])
 sv=tuple(sorted(src.variables()))
 for e in envs(sv,n): s.add(ev(src.lhs,op,n,e)==ev(src.rhs,op,n,e))
 tv=tuple(sorted(tgt.variables())); w={x:Int(f"w_{p['id']}_{family}_{x}") for x in tv}
 for x in w.values():s.add(x>=0,x<n)
 s.add(ev(tgt.lhs,op,n,w)!=ev(tgt.rhs,op,n,w))
 t=time.monotonic(); st=s.check(); ms=int((time.monotonic()-t)*1000)
 row={"id":p["id"],"n":n,"family":family,"status":str(st),"elapsed_ms":ms,"verified":False}
 if st==sat:
  m=s.model(); table=tuple(tuple(int(m.eval(Select(op,i*n+j),model_completion=True).as_long()) for j in range(n)) for i in range(n))
  cert=_FMW.check_finite_countermodel(norm(p["equation1"]),norm(p["equation2"]),table)
  if not cert.terminal_candidate_ok:raise RuntimeError("independent verifier rejected model")
  raw=json.dumps([list(r) for r in table],separators=(",",":"))
  row|={"verified":True,"table_sha256":hashlib.sha256(raw.encode()).hexdigest(),"table":[list(r) for r in table],"witness_env":cert.witness_env}
 elif st==unknown: row["reason_unknown"]=s.reason_unknown()
 return row

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--wb3000",required=True);ap.add_argument("--wb3500",required=True);ap.add_argument("--timeout-ms",type=int,default=2500);ap.add_argument("--out",required=True);a=ap.parse_args()
 rows=load(a.wb3000,EXPECTED_3000_SHA256)+load(a.wb3500,EXPECTED_3500_SHA256); by={r["id"]:r for r in rows}
 results=[]; winners=[]
 for pid,n in CASES.items():
  for fam in FAMILIES:
   r=solve(by[pid],n,fam,a.timeout_ms);results.append(r)
   if r["verified"]:
    winners.append(r);break
 summary={"schema":"mathgraph.v56.opened-structural-constructor","classification":"OPENED_DIAGNOSTIC_NOT_FRESH","cases":len(CASES),"families":list(FAMILIES),"solved_cases":len(winners),"winners":winners,"attempt_count":len(results),"elapsed_ms_total":sum(x["elapsed_ms"] for x in results),"proof_tables_read_by_solver":0}
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/"result.json").write_text(json.dumps(summary,indent=2,sort_keys=True));print(json.dumps(summary,indent=2,sort_keys=True))
 return 0
if __name__=="__main__":raise SystemExit(main())
