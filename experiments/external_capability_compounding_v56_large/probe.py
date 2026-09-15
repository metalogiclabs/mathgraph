#!/usr/bin/env python3
"""Opened-data diagnostic for order-5/6 exact finite construction.

The case IDs and target carrier sizes below were learned from already-open V55
public certificates. This is therefore explicitly diagnostic, not fresh
evidence. The solver does NOT read the certificate tables; it receives only the
problem equations and independently synthesizes an operation table, which is
then rechecked by MathGraph's finite verifier.
"""

from __future__ import annotations

import argparse, hashlib, importlib.util, itertools, json, sys, time
from pathlib import Path
from z3 import Array, Int, IntSort, Select, Solver, sat, unknown

EXTERNAL_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
EXPECTED_3000_SHA256 = "fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7"
EXPECTED_3500_SHA256 = "fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8"

# Opened-certificate-derived carrier-size hints. No tables are embedded.
CASES = {
    "2314_to_47730": 5,
    "2318_to_31013": 6,
    "731_to_4023": 6,
    "690_to_23112": 6,
    "40732_to_3525": 6,
    "42486_to_46040": 5,
    "834_to_22246": 5,
}

_FMW_PATH = Path(__file__).resolve().parents[2] / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("v56_large_fmw", _FMW_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load finite verifier")
_FMW = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FMW
_SPEC.loader.exec_module(_FMW)


def norm(text: str) -> str:
    out = str(text)
    for op in ("◇","⋄","·","∙","∗","＊","×"):
        out = out.replace(op, "*")
    return out


def load(path: Path, expected: str) -> list[dict]:
    data = path.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != expected:
        raise RuntimeError(f"hash mismatch {got} != {expected}")
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


def eval_sym(term, op, n, env):
    if term.name is not None:
        return env[term.name]
    return Select(op, eval_sym(term.left, op, n, env) * n + eval_sym(term.right, op, n, env))


def envs(names, n):
    for vals in itertools.product(range(n), repeat=len(names)):
        yield dict(zip(names, vals))


def solve(problem: dict, n: int, timeout_ms: int) -> dict:
    src = _FMW.parse_equation(norm(problem["equation1"]))
    tgt = _FMW.parse_equation(norm(problem["equation2"]))
    op = Array(f"op_{problem['id']}_{n}", IntSort(), IntSort())
    s = Solver()
    s.set(timeout=timeout_ms)
    for idx in range(n*n):
        v = Select(op, idx)
        s.add(v >= 0, v < n)
    src_vars = tuple(sorted(src.variables()))
    for e in envs(src_vars, n):
        s.add(eval_sym(src.lhs, op, n, e) == eval_sym(src.rhs, op, n, e))
    tgt_vars = tuple(sorted(tgt.variables()))
    w = {name:Int(f"w_{problem['id']}_{name}") for name in tgt_vars}
    for v in w.values():
        s.add(v >= 0, v < n)
    s.add(eval_sym(tgt.lhs, op, n, w) != eval_sym(tgt.rhs, op, n, w))
    started = time.monotonic()
    status = s.check()
    elapsed = int((time.monotonic()-started)*1000)
    row = {
        "id":problem["id"], "n":n, "status":str(status), "elapsed_ms":elapsed,
        "source_assignments":n ** len(src_vars), "verified":False, "table_sha256":None
    }
    if status == sat:
        m=s.model()
        table=tuple(tuple(int(m.eval(Select(op,i*n+j),model_completion=True).as_long()) for j in range(n)) for i in range(n))
        checked=_FMW.check_finite_countermodel(norm(problem["equation1"]),norm(problem["equation2"]),table)
        if not checked.terminal_candidate_ok:
            raise RuntimeError(f"independent verification failed for {problem['id']}")
        raw=json.dumps([list(r) for r in table],separators=(",",":"))
        row["verified"]=True
        row["table_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
        row["witness_env"]=checked.witness_env
    elif status == unknown:
        row["reason_unknown"]=s.reason_unknown()
    return row


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--wrong-book-3000",required=True)
    ap.add_argument("--wrong-book-3500",required=True)
    ap.add_argument("--timeout-ms",type=int,default=12000)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()

    rows=load(Path(args.wrong_book_3000),EXPECTED_3000_SHA256)+load(Path(args.wrong_book_3500),EXPECTED_3500_SHA256)
    by_id={r["id"]:r for r in rows}
    results=[]
    for pid,n in CASES.items():
        if pid not in by_id:
            raise RuntimeError(f"opened case missing: {pid}")
        results.append(solve(by_id[pid],n,args.timeout_ms))

    summary={
        "schema":"mathgraph.external-capability-compounding.v56.large-finite-opened-probe",
        "classification":"OPENED_CERTIFICATE_GUIDED_DIAGNOSTIC_NOT_FRESH_EVIDENCE",
        "external_commit":EXTERNAL_COMMIT,
        "certificate_tables_read_by_solver":0,
        "cases":len(results),
        "verified_sat":sum(r["verified"] for r in results),
        "unknown":sum(r["status"]=="unknown" for r in results),
        "unsat":sum(r["status"]=="unsat" for r in results),
        "elapsed_ms_total":sum(r["elapsed_ms"] for r in results),
        "results":results,
        "conclusion":"ORDER_5_6_EXACT_CONSTRUCTOR_REACHABLE" if any(r["verified"] for r in results) else "ORDER_5_6_NOT_REACHED",
    }
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
