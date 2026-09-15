#!/usr/bin/env python3
"""V59 opened-data calibration: compile a retained finite model into a source-preserving neighborhood.

Calibration only. Uses the already-open V58 rows 2628:2756 and the exact
V58 final archive artifact. No row >= 2756 is read semantically here.

Generic operator
----------------
For a new implication S => T and each retained finite magma M:
  1. score M by the fraction of assignments on which it violates S;
  2. choose the few closest source fits;
  3. on the same carrier, ask a bounded finite CSP to find M' within Hamming
     radius K of M such that S holds universally and T fails somewhere;
  4. independently exhaustively verify M' with MathGraph.

The child must differ from its parent and the parent must not already solve the
target. This is a constructor over a retained capability, not table replay.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Sequence

from z3 import EnumSort, Function, If, Or, Solver, Sum, sat

ROOT = Path(__file__).resolve().parents[2]
_FMW_PATH = ROOT / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("v59_fmw", _FMW_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load finite_magma_world")
_FMW = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FMW
_SPEC.loader.exec_module(_FMW)

_V58_PATH = ROOT / "experiments" / "external_capability_compounding_v58" / "run.py"
_V58_SPEC = importlib.util.spec_from_file_location("v59_v58", _V58_PATH)
if _V58_SPEC is None or _V58_SPEC.loader is None:
    raise RuntimeError("cannot load V58 constructor")
_V58 = importlib.util.module_from_spec(_V58_SPEC)
sys.modules[_V58_SPEC.name] = _V58
_V58_SPEC.loader.exec_module(_V58)

OPEN_START = 2628
OPEN_COUNT = 128
TOP_PARENTS = 3
MAX_DISTANCE = 4
REPAIR_TIMEOUT_MS = 300
COLD_COMPARE_TIMEOUT_MS = TOP_PARENTS * REPAIR_TIMEOUT_MS
EXPECTED_SEED_SHA256 = "241f6223899b6decf77767d0ec182920417b65217846f8b68e24d7a13b2bd535"


def normalize(text: str) -> str:
    return _V58.normalize_external_equation(text)


def parse_eq(text: str):
    return _FMW.parse_equation(normalize(text))


def table_tuple(table):
    return _FMW.normalize_table(table)


def eval_table(term, table, env):
    if term.name is not None:
        return env[term.name]
    return table[eval_table(term.left, table, env)][eval_table(term.right, table, env)]


def assignments(names, n):
    names = tuple(names)
    for values in itertools.product(range(n), repeat=len(names)):
        yield dict(zip(names, values))


def source_violation_count(problem: dict, table: Sequence[Sequence[int]]) -> tuple[int, int]:
    table = table_tuple(table)
    eq = parse_eq(problem["equation1"])
    bad = 0
    total = 0
    for env in assignments(eq.variables(), len(table)):
        total += 1
        if eval_table(eq.lhs, table, env) != eval_table(eq.rhs, table, env):
            bad += 1
    return bad, total


def solves(problem: dict, table) -> bool:
    return bool(
        _FMW.check_finite_countermodel(
            normalize(problem["equation1"]),
            normalize(problem["equation2"]),
            table,
        ).terminal_candidate_ok
    )


def z3_eval(term, op, env):
    if term.name is not None:
        return env[term.name]
    return op(z3_eval(term.left, op, env), z3_eval(term.right, op, env))


def repair(problem: dict, parent: dict, serial: int):
    table = table_tuple(parent["table"])
    n = len(table)
    sort, elems = EnumSort(
        f"U_{serial}",
        [f"e_{serial}_{i}" for i in range(n)],
    )
    op = Function(f"m_{serial}", sort, sort, sort)
    solver = Solver()
    solver.set(timeout=REPAIR_TIMEOUT_MS)

    source = parse_eq(problem["equation1"])
    target = parse_eq(problem["equation2"])

    for values in itertools.product(range(n), repeat=len(source.variables())):
        env = {name: elems[value] for name, value in zip(source.variables(), values)}
        solver.add(z3_eval(source.lhs, op, env) == z3_eval(source.rhs, op, env))

    target_failures = []
    for values in itertools.product(range(n), repeat=len(target.variables())):
        env = {name: elems[value] for name, value in zip(target.variables(), values)}
        target_failures.append(z3_eval(target.lhs, op, env) != z3_eval(target.rhs, op, env))
    solver.add(Or(*target_failures))

    differences = []
    for i in range(n):
        for j in range(n):
            differences.append(If(op(elems[i], elems[j]) == elems[table[i][j]], 0, 1))
    distance_expr = Sum(differences)
    solver.add(distance_expr >= 1)
    solver.add(distance_expr <= MAX_DISTANCE)

    started = time.monotonic()
    status = solver.check()
    elapsed_ms = int(round((time.monotonic() - started) * 1000))
    if status != sat:
        return {
            "status": str(status),
            "elapsed_ms": elapsed_ms,
            "parent_cid": parent["cid"],
            "parent_n": n,
        }

    model = solver.model()
    lookup = {str(e): i for i, e in enumerate(elems)}
    child = []
    for i in range(n):
        row = []
        for j in range(n):
            val = model.eval(op(elems[i], elems[j]), model_completion=True)
            row.append(lookup[str(val)])
        child.append(row)
    child = table_tuple(child)
    distance = sum(child[i][j] != table[i][j] for i in range(n) for j in range(n))
    verified = solves(problem, child)
    if not verified:
        raise RuntimeError(f"MathGraph rejected repaired child on {problem['id']}")
    return {
        "status": "VERIFIED_CHILD",
        "elapsed_ms": elapsed_ms,
        "parent_cid": parent["cid"],
        "parent_n": n,
        "distance": distance,
        "child": [list(row) for row in child],
        "child_cid": hashlib.sha256(
            json.dumps([list(r) for r in child], separators=(",", ":")).encode()
        ).hexdigest(),
    }


def load_rows(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[OPEN_START:OPEN_START + OPEN_COUNT]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wrong-book-3000", required=True)
    ap.add_argument("--wrong-book-3500", required=True)
    ap.add_argument("--seed-archive", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    seed_path = Path(args.seed_archive)
    seed_bytes = seed_path.read_bytes()
    seed_file_sha = hashlib.sha256(seed_bytes).hexdigest()
    if seed_file_sha != EXPECTED_SEED_SHA256:
        raise RuntimeError(f"seed archive byte hash mismatch: {seed_file_sha}")
    seed = json.loads(seed_bytes)
    parents = seed["capabilities"]
    if len(parents) != 18:
        raise RuntimeError(f"expected 18 retained V58 capabilities, got {len(parents)}")

    rows = load_rows(Path(args.wrong_book_3000)) + load_rows(Path(args.wrong_book_3500))
    repaired = []
    direct = 0
    tested = 0
    serial = 0

    for problem in rows:
        direct_solvers = [p for p in parents if solves(problem, p["table"])]
        if direct_solvers:
            direct += 1
            continue

        scored = []
        for parent in parents:
            bad, total = source_violation_count(problem, parent["table"])
            scored.append((bad / max(total, 1), bad, len(parent["table"]), parent))
        scored.sort(key=lambda x: (x[0], x[1], x[2], -int(x[3].get("reuse_hits", 0)), x[3]["cid"]))

        tested += 1
        winner = None
        attempts = []
        for ratio, bad, _n, parent in scored[:TOP_PARENTS]:
            serial += 1
            res = repair(problem, parent, serial)
            attempts.append({
                "parent_cid": parent["cid"],
                "source_violation_ratio": ratio,
                "source_violations": bad,
                "result": {k: v for k, v in res.items() if k != "child"},
            })
            if res["status"] == "VERIFIED_CHILD":
                winner = (parent, res, ratio, bad)
                break

        if winner is None:
            continue

        parent, res, ratio, bad = winner
        # Parent must not already be a countermodel; the child must be genuinely new.
        if solves(problem, parent["table"]):
            raise RuntimeError("repair winner parent already solved target")
        if res["child_cid"] == parent["cid"]:
            raise RuntimeError("repair child equals parent")

        # Same total solver budget cold comparison. This is opened-data calibration,
        # not fresh evidence; it only tells us whether freezing the operator is sensible.
        cold = _V58.cvc5_construct(problem, timeout_ms=COLD_COMPARE_TIMEOUT_MS)
        repaired.append({
            "problem_id": problem["id"],
            "parent_cid": parent["cid"],
            "parent_acquired_on": parent["acquired_on"],
            "parent_n": len(parent["table"]),
            "source_violation_ratio": ratio,
            "source_violations": bad,
            "distance": res["distance"],
            "repair_elapsed_ms": res["elapsed_ms"],
            "child_cid": res["child_cid"],
            "cold_same_budget_status": cold.status,
            "cold_same_budget_elapsed_ms": cold.elapsed_ms,
            "attempts": attempts,
        })
        print(json.dumps(repaired[-1], sort_keys=True), flush=True)

    cold_miss_children = sum(
        r["cold_same_budget_status"] != "VERIFIED_FALSE" for r in repaired
    )
    distinct_parents = len({r["parent_cid"] for r in repaired})
    distances = {}
    for r in repaired:
        distances[str(r["distance"])] = distances.get(str(r["distance"]), 0) + 1

    checks = {
        "exact_v58_seed_archive": seed_file_sha == EXPECTED_SEED_SHA256 and len(parents) == 18,
        "generated_verified_children": len(repaired) >= 2,
        "more_than_one_parent_can_develop": distinct_parents >= 2,
        "same_budget_cold_miss_exists": cold_miss_children >= 1,
        "all_children_within_frozen_radius": all(1 <= r["distance"] <= MAX_DISTANCE for r in repaired),
    }
    result = {
        "schema": "mathgraph.external-capability-compounding.v59.calibration",
        "classification": "OPENED_V58_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "opened_rows": len(rows),
        "direct_seed_reuses": direct,
        "repair_candidates_tested": tested,
        "verified_repaired_children": len(repaired),
        "same_budget_cold_miss_children": cold_miss_children,
        "distinct_parent_capabilities": distinct_parents,
        "distance_histogram": distances,
        "frozen_candidate_parameters": {
            "top_parents": TOP_PARENTS,
            "max_distance": MAX_DISTANCE,
            "repair_timeout_ms_per_parent": REPAIR_TIMEOUT_MS,
            "total_repair_solver_budget_ms": COLD_COMPARE_TIMEOUT_MS,
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "examples": repaired[:24],
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (out / "children.json").write_text(json.dumps(repaired, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    if not result["all_checks_pass"]:
        raise SystemExit("V59 opened calibration failed")


if __name__ == "__main__":
    main()
