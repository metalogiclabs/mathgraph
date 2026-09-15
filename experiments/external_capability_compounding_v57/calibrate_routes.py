#!/usr/bin/env python3
"""Opened-route calibration for V57.

This file uses five already-open V55/V56 problems only. Their expected route
classes were learned post-hoc from public certificates after those rows had
already been consumed. Therefore this is calibration, not fresh evidence.

The calibration tests a generic two-sided route engine:
  * E prover for TRUE-side equational implication.
  * Exact Z3 finite-model construction for FALSE-side n <= 6.
  * Independent MathGraph finite checking for any synthesized model.
  * UNKNOWN when neither bounded route succeeds.

No public proof file is read during this workflow.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from z3 import Array, Int, IntSort, Select, Solver, sat, unknown

CASES = {
    "42607_to_41601": {"expected": "TRUE_PROOF"},
    "1334_to_3294": {"expected": "TRUE_PROOF"},
    "2314_to_47730": {"expected": "FINITE_FALSE", "published_n": 5},
    "2318_to_31013": {"expected": "FINITE_FALSE", "published_n": 6},
    "1486_to_17185": {"expected": "NONSMALL_FALSE"},
}

ROOT = Path(__file__).resolve().parents[2]
_FMW_PATH = ROOT / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("v57_fmw", _FMW_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load finite verifier")
_FMW = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FMW
_SPEC.loader.exec_module(_FMW)


def norm(text: str) -> str:
    out = str(text)
    for op in ("◇", "⋄", "·", "∙", "∗", "＊", "×"):
        out = out.replace(op, "*")
    return out


def read_problem(path: Path, pid: str) -> dict:
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["id"] == pid:
            return row
    raise KeyError(pid)


def tptp_term(term, varmap: dict[str, str]) -> str:
    if term.name is not None:
        return varmap[term.name]
    return f"m({tptp_term(term.left,varmap)},{tptp_term(term.right,varmap)})"


def e_input(problem: dict) -> str:
    source = _FMW.parse_equation(norm(problem["equation1"]))
    target = _FMW.parse_equation(norm(problem["equation2"]))
    all_vars = sorted(set(source.variables()) | set(target.variables()))
    varmap = {name: f"V{i}" for i, name in enumerate(all_vars)}
    src_vars = ",".join(varmap[v] for v in source.variables())
    tgt_vars = ",".join(varmap[v] for v in target.variables())
    src = f"({tptp_term(source.lhs,varmap)}={tptp_term(source.rhs,varmap)})"
    tgt = f"({tptp_term(target.lhs,varmap)}={tptp_term(target.rhs,varmap)})"
    return (
        f"fof(source,axiom,![{src_vars}]:{src}).\n"
        f"fof(target,conjecture,![{tgt_vars}]:{tgt}).\n"
    )


def run_e(problem: dict, cpu_seconds: int) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".p", delete=False) as handle:
        handle.write(e_input(problem))
        path = handle.name
    started = time.monotonic()
    try:
        cp = subprocess.run(
            ["eprover", "--auto", f"--cpu-limit={cpu_seconds}", "--tstp-format", path],
            text=True,
            capture_output=True,
            timeout=cpu_seconds + 4,
            check=False,
        )
        stdout = cp.stdout
        proved = "SZS status Theorem" in stdout or "# Proof found!" in stdout
        return {
            "proved": proved,
            "returncode": cp.returncode,
            "elapsed_ms": int((time.monotonic()-started)*1000),
            "status_excerpt": "\n".join(
                line for line in stdout.splitlines()
                if "SZS status" in line or "Proof found" in line
            )[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"proved": False, "returncode": None, "elapsed_ms": int((time.monotonic()-started)*1000), "status_excerpt": "timeout"}
    finally:
        Path(path).unlink(missing_ok=True)


def eval_sym(term, op, n: int, env):
    if term.name is not None:
        return env[term.name]
    return Select(op, eval_sym(term.left,op,n,env)*n + eval_sym(term.right,op,n,env))


def envs(names, n):
    names=tuple(names)
    for values in itertools.product(range(n), repeat=len(names)):
        yield dict(zip(names, values))


def independent_check(problem: dict, table) -> bool:
    return bool(_FMW.check_finite_countermodel(norm(problem["equation1"]), norm(problem["equation2"]), table).terminal_candidate_ok)


def exact_model(problem: dict, n: int, timeout_ms: int) -> dict:
    source=_FMW.parse_equation(norm(problem["equation1"]))
    target=_FMW.parse_equation(norm(problem["equation2"]))
    op=Array(f"op_{problem['id']}_{n}",IntSort(),IntSort())
    s=Solver(); s.set(timeout=timeout_ms)
    for idx in range(n*n):
        v=Select(op,idx); s.add(v>=0,v<n)
    for env in envs(source.variables(),n):
        s.add(eval_sym(source.lhs,op,n,env)==eval_sym(source.rhs,op,n,env))
    w={name:Int(f"w_{problem['id']}_{n}_{name}") for name in target.variables()}
    for v in w.values(): s.add(v>=0,v<n)
    s.add(eval_sym(target.lhs,op,n,w)!=eval_sym(target.rhs,op,n,w))
    started=time.monotonic(); st=s.check(); elapsed=int((time.monotonic()-started)*1000)
    if st==sat:
        m=s.model()
        table=tuple(tuple(m.eval(Select(op,i*n+j),model_completion=True).as_long() for j in range(n)) for i in range(n))
        ok=independent_check(problem,table)
        if not ok: raise RuntimeError(f"independent checker rejected model {problem['id']} n={n}")
        return {"status":"sat","n":n,"elapsed_ms":elapsed,"verified":True,"table":[list(r) for r in table]}
    return {"status":"unknown" if st==unknown else "unsat","n":n,"elapsed_ms":elapsed,"verified":False}


def route(problem: dict, e_seconds: int, model_timeout_ms: int) -> dict:
    e=run_e(problem,e_seconds)
    if e["proved"]:
        return {"terminal":"TRUE_CANDIDATE","route":"E_PROOF","e":e,"models":[]}
    models=[]
    for n in range(2,7):
        res=exact_model(problem,n,model_timeout_ms)
        models.append(res)
        if res["status"]=="sat" and res["verified"]:
            return {"terminal":"FALSE","route":"FINITE_MODEL","e":e,"models":models,"n":n}
    return {"terminal":"UNKNOWN","route":"UNKNOWN","e":e,"models":models}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset3000",required=True)
    ap.add_argument("--dataset3500",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--e-seconds",type=int,default=5)
    ap.add_argument("--model-timeout-ms",type=int,default=5000)
    args=ap.parse_args()
    p3000=Path(args.dataset3000); p3500=Path(args.dataset3500)
    rows=[]
    for pid,meta in CASES.items():
        try: problem=read_problem(p3000,pid)
        except KeyError: problem=read_problem(p3500,pid)
        result=route(problem,args.e_seconds,args.model_timeout_ms)
        result={"id":pid,"expected":meta,**result}
        rows.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in {"models"}},sort_keys=True),flush=True)

    checks={
        "true_42607_proved": next(r for r in rows if r["id"]=="42607_to_41601")["route"]=="E_PROOF",
        "true_1334_proved": next(r for r in rows if r["id"]=="1334_to_3294")["route"]=="E_PROOF",
        "false_2314_model": next(r for r in rows if r["id"]=="2314_to_47730")["route"]=="FINITE_MODEL",
        "false_2318_model": next(r for r in rows if r["id"]=="2318_to_31013")["route"]=="FINITE_MODEL",
        "symbolic_1486_not_falsely_proved": next(r for r in rows if r["id"]=="1486_to_17185")["route"]!="E_PROOF",
    }
    summary={
        "schema":"mathgraph.external-capability-compounding.v57.route-calibration",
        "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "cases":rows,
        "checks":checks,
        "all_calibration_checks_pass":all(checks.values()),
    }
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))
    if not summary["all_calibration_checks_pass"]:
        raise SystemExit("V57 route calibration failed")

if __name__=="__main__":
    main()
