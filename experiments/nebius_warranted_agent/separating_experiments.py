"""Finite separating experiments for MathGraph Autopilot.

Boundary: scripted hypotheses, independently specified finite clamp oracle,
trusted local unittest runner. Neither general correctness nor Nebius inference.
"""
from __future__ import annotations
import ast
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
from tempfile import TemporaryDirectory

GOOD = '''def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))
'''
CAP10 = '''def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum, 10))
'''
CAP11 = '''def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum, 11))
'''
FLOOR0 = '''def clamp(value, minimum, maximum):
    return max(0, minimum, min(value, maximum))
'''
HYPOTHESES = {"correct": GOOD, "cap10": CAP10, "cap11": CAP11, "floor0": FLOOR0}
BASE = ((5, 0, 10), (-3, 0, 10), (14, 0, 10), (10, 0, 10))
VALUES = (-3, -2, -1, 0, 1, 2, 5, 9, 10, 11, 12, 15, 20)
LOWERS = (-2, 0, 2)
UPPERS = (5, 10, 11, 12, 20)
DOMAIN = tuple((v, lo, hi) for v, lo, hi in itertools.product(VALUES, LOWERS, UPPERS) if lo <= hi)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def oracle(case: tuple[int, int, int]) -> int:
    """Independent contract, expressed without the candidate's min/max calls."""
    value, minimum, maximum = case
    if minimum > maximum:
        raise ValueError("invalid bounds")
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value

def candidate_expression(code: str) -> ast.expr:
    """Verify the pure-expression language before interpreting it (never eval)."""
    if len(code.encode()) > 16000:
        raise ValueError("code too large")
    module = ast.parse(code)
    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        raise ValueError("not one function")
    fun = module.body[0]
    args = fun.args
    if (fun.name != "clamp" or fun.decorator_list or fun.returns is not None
        or args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg
        or args.defaults or args.kw_defaults
        or [a.arg for a in args.args] != ["value", "minimum", "maximum"]
        or any(a.annotation is not None for a in args.args)):
        raise ValueError("bad signature")
    body = fun.body
    if (len(body) == 2 and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        raise ValueError("not pure single-return")
    expr = body[0].value
    nodes = list(ast.walk(expr))
    if len(nodes) > 128:
        raise ValueError("too many nodes")
    for node in nodes:
        if isinstance(node, ast.Call):
            if (not isinstance(node.func, ast.Name) or node.func.id not in ("min", "max")
                or node.keywords or not 1 <= len(node.args) <= 8):
                raise ValueError("disallowed call")
        elif isinstance(node, ast.Name):
            if node.id not in ("value", "minimum", "maximum", "min", "max"):
                raise ValueError("disallowed name")
        elif isinstance(node, ast.Constant):
            if type(node.value) is not int or abs(node.value) > 1000:
                raise ValueError("disallowed constant")
        elif not isinstance(node, ast.Load):
            raise ValueError("disallowed AST node")
    return expr

def evaluate(expr: ast.expr, case: tuple[int, int, int]) -> int:
    """Independent AST interpreter, without executing arbitrary generated code."""
    env = dict(zip(("value", "minimum", "maximum"), case))
    def visit(node, depth):
        if depth > 32:
            raise ValueError("expression too deep")
        if isinstance(node, ast.Constant):
            return int(node.value)
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            values = [visit(a, depth + 1) for a in node.args]
            return min(values) if node.func.id == "min" else max(values)
        raise ValueError("not in grammar")
    return visit(expr, 0)

def passing_hypotheses(baseline=BASE):
    cases = tuple(baseline)
    expressions = {name: candidate_expression(code) for name, code in HYPOTHESES.items()}
    return {name: expr for name, expr in expressions.items()
            if all(evaluate(expr, c) == oracle(c) for c in cases)}

def case_cost(case):
    """Declared synthetic cost, not measured runtime, money or physical cost."""
    return 1 + sum(abs(x) for x in case)

def separating_basis(hypotheses, domain=DOMAIN):
    """Exact minimum-total-cost experiment set over a finite hypothesis grammar."""
    domain = tuple(dict.fromkeys(domain))
    if "correct" not in hypotheses:
        raise ValueError("reference missing")
    rivals = tuple(sorted(n for n in hypotheses if n != "correct"))
    if len(rivals) > 16:
        raise ValueError("hypothesis grammar too large")
    covers = []
    for case in domain:
        mask = sum(1 << i for i, name in enumerate(rivals)
                   if evaluate(hypotheses[name], case) != oracle(case))
        if mask:
            covers.append((case, mask, case_cost(case)))
    best = {0: (0, 0, ())}
    for case, cover, price in covers:
        updated = best.copy()
        for mask, (cost, size, tests) in best.items():
            target = mask | cover
            item = (cost + price, size + 1, tests + (case,))
            if target not in updated or item < updated[target]:
                updated[target] = item
        best = updated
    full = (1 << len(rivals)) - 1
    answer = best.get(full)
    unsplittable = [name for i, name in enumerate(rivals)
                   if not any(mask & (1 << i) for _, mask, _ in covers)]
    return {"grammar": "finite-clamp-mutants-v1", "hypotheses": sorted(hypotheses),
            "rivals": list(rivals), "domain_size": len(domain),
            "status": "MINIMUM_BASIS" if answer is not None else "OBSTRUCTION",
            "tests": [list(c) for c in answer[2]] if answer else [],
            "total_cost": answer[0] if answer else None,
            "unsplittable": unsplittable,
            "hypothesis_digests": {n: sha(HYPOTHESES[n].encode()) for n in sorted(hypotheses)}}

def generated_tests(cases):
    lines = ["\nclass SeparatingTests(unittest.TestCase):"]
    for i, case in enumerate(cases):
        v, lo, hi = case
        lines += [f"    def test_separating_{i:03d}(self):",
                  f"        self.assertEqual(clamp({v}, {lo}, {hi}), {oracle(case)})"]
    return "\n".join(lines) + "\n"

def run_demo():
    """Actual bounded subprocess tests, but scripted hypothetical code proposals."""
    from autopilot import TESTS, execute_tests, qualify, snapshot
    with TemporaryDirectory(prefix="mathgraph-separating-") as directory:
        root = Path(directory)
        (root / "calculator.py").write_text(CAP10)
        (root / "test_calculator.py").write_text(TESTS)
        source_sha = snapshot(root)
        receipt0, _ = execute_tests(root, source_sha)
        baseline, _ = qualify(root, source_sha, receipt0)
        if baseline != "WARRANTED":
            raise AssertionError("baseline control was not accepted")
        hypotheses = passing_hypotheses()
        basis = separating_basis(hypotheses)
        if basis["status"] != "MINIMUM_BASIS":
            raise AssertionError("expected finite separator")
        (root / "test_calculator.py").write_text(
            TESTS + generated_tests(tuple(c) for c in basis["tests"]))
        withdrawn, _ = qualify(root, source_sha, receipt0)
        if withdrawn != "REJECTED":
            raise AssertionError("changed test file retained old receipt")
        receipt1, _ = execute_tests(root, source_sha)
        detected, _ = qualify(root, source_sha, receipt1)
        if detected != "REJECTED" or receipt1.exit_code == 0:
            raise AssertionError("new test did not detect defective implementation")
        (root / "calculator.py").write_text(GOOD)
        stale, _ = qualify(root, source_sha, receipt1)
        if stale != "REJECTED":
            raise AssertionError("changed candidate retained old receipt")
        receipt2, _ = execute_tests(root, source_sha)
        repaired, _ = qualify(root, source_sha, receipt2)
        if repaired != "WARRANTED":
            raise AssertionError("fresh tests did not qualify repaired candidate")
        agreement = all(evaluate(candidate_expression(GOOD), c) == oracle(c) for c in DOMAIN)
        if not agreement:
            raise AssertionError("candidate disagrees with oracle in finite domain")
        return {"schema":"mathgraph.separating-experiment.v1",
                "provider":"SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS",
                "scope":"finite predeclared mutant grammar, bounded oracle and source-bound local unittest",
                "hypothesis_set":sorted(hypotheses), "baseline_count":len(BASE),
                "basis":basis, "comparison":{"fixed_test_only":baseline,
                "after_separating_test":detected, "after_scripted_repair":repaired,
                "finite_domain_checked":len(DOMAIN), "finite_domain_agreement":agreement},
                "timeline":[
                {"step":"fixed_tests", "state":baseline, "receipt":asdict(receipt0)},
                {"step":"missing_separating_evidence", "state":"UNKNOWN",
                 "reason":"existing suite admits multiple incompatible hypotheses"},
                {"step":"test_file_changed", "state":withdrawn},
                {"step":"separating_test", "state":detected, "receipt":asdict(receipt1)},
                {"step":"candidate_changed", "state":stale},
                {"step":"reacquired_tests", "state":repaired, "receipt":asdict(receipt2)}]}

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--report", default="separating-report.json")
    args = p.parse_args()
    result = run_demo()
    Path(args.report).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"comparison":result["comparison"],"basis":result["basis"],
                      "hypothesis_set":result["hypothesis_set"]}, indent=2))

if __name__ == "__main__":
    main()
