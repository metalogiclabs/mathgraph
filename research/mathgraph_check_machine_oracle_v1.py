"""Machine-labelled finite semantics benchmark, with independent Lean check source.

No outside human labels, AI judges, network calls, or proprietary model APIs.
This measures a deliberately restricted Boolean DSL, *not* English-to-Lean
fidelity and not a cost/quality comparison with Palomar's statement reviewer.

Independent authority levels:
  1. This script's bitset evaluator derives finite oracle labels without
     importing the production scalar evaluator or reusing its truth signatures.
  2. The library under test computes its scalar truth signatures and witness.
  3. Generated Lean source, independently checked with `lean` and `by decide`,
     confirms a predeclared subset of equivalences and counterexamples.
"""
from __future__ import annotations

import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import random

from mathgraph_check.finite_logic import compare_finite_formulas

SEED = 0x4D475632
N_EQUAL = 192
N_DIFFERENT = 192
N_UNSUPPORTED = 32
VARS = ("p", "q", "r")
WIDTH = 1 << len(VARS)
MASK = (1 << WIDTH) - 1


def canonical_bytes(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def bitset_oracle(expr):
    """Reference interpreter: whole-domain bit-vectors (not scalar recursion)."""
    op, value = next(iter(expr.items()))
    if op == "const":
        return MASK if value else 0
    if op == "var":
        return sum(1 << k for k, values in enumerate(product((False, True), repeat=3))
                   if values[VARS.index(value)])
    if op == "not":
        return MASK ^ bitset_oracle(value)
    a, b = (bitset_oracle(x) for x in value)
    return {
        "and": lambda: a & b,
        "or": lambda: a | b,
        "xor": lambda: a ^ b,
        "implies": lambda: (MASK ^ a) | b,
        "iff": lambda: MASK ^ (a ^ b),
    }[op]()


def formula(rng, depth=3):
    if depth == 0 or rng.randrange(5) == 0:
        return ({"var": rng.choice(VARS)} if rng.randrange(4)
                else {"const": bool(rng.getrandbits(1))})
    op = rng.choice(("not", "and", "or", "xor", "implies", "iff"))
    if op == "not":
        return {"not": formula(rng, depth - 1)}
    return {op: [formula(rng, depth - 1), formula(rng, depth - 1)]}


def equivalent_rewrite(rng, f):
    return rng.choice((
        lambda: {"not": {"not": f}},
        lambda: {"and": [f, {"const": True}]},
        lambda: {"or": [{"const": False}, f]},
        lambda: {"iff": [f, {"const": True}]},
        lambda: {"implies": [{"const": True}, f]},
        lambda: {"xor": [f, {"const": False}]},
    ))()


def distinct_rewrite(rng, f):
    # Mutations are filtered by an independent reference oracle; we never
    # assume that a syntactic edit necessarily alters protected behaviour.
    candidates = [
        lambda: {"not": f},
        lambda: {"and": [f, {"var": rng.choice(VARS)}]},
        lambda: {"or": [f, {"var": rng.choice(VARS)}]},
        lambda: {"implies": [f, {"var": rng.choice(VARS)}]},
        lambda: formula(rng, 3),
    ]
    for _ in range(60):
        target = rng.choice(candidates)()
        if bitset_oracle(target) != bitset_oracle(f):
            return target
    return {"not": f}  # Boolean negation differs on every valuation.


def generated_cases():
    rng = random.Random(SEED)
    cases = []
    for kind in ("equivalent", "different"):
        for i in range(N_EQUAL if kind == "equivalent" else N_DIFFERENT):
            f = formula(rng)
            target = (equivalent_rewrite(rng, f) if kind == "equivalent"
                      else distinct_rewrite(rng, f))
            cases.append({"id": f"{kind}-{i:03d}", "source": f, "formal": target,
                          "generator_intent": kind})
    for i in range(N_UNSUPPORTED):
        f = formula(rng)
        cases.append({"id": f"outside-{i:03d}", "source": f,
                      "formal": {"forallNat": f},
                      "generator_intent": "unsupported"})
    # Predeclared adversarial semantics, not hand-labelled by comparing results.
    p, q = {"var": "p"}, {"var": "q"}
    cases += [
        {"id": "sentinel-vacuous-negative",
         "source": {"implies": [{"and": [p, {"not": p}]}, q]},
         "formal": {"implies": [p, q]}, "generator_intent": "different"},
        {"id": "sentinel-vacuous-positive",
         "source": {"implies": [{"and": [p, {"not": p}]}, q]},
         "formal": {"const": True}, "generator_intent": "equivalent"},
        {"id": "sentinel-demorgan",
         "source": {"not": {"and": [p, q]}},
         "formal": {"or": [{"not": p}, {"not": q}]},
         "generator_intent": "equivalent"},
        {"id": "sentinel-hidden-vacuity",
         "source": {"const": False},
         "formal": {"and": [p, {"not": p}]},
         "generator_intent": "equivalent"},
    ]
    return cases


def lean_expr(formula):
    """Code generator for a completely independent Lean Bool expression."""
    op, v = next(iter(formula.items()))
    if op == "var":
        return v
    if op == "const":
        return "true" if v else "false"
    if op == "not":
        return "(!" + lean_expr(v) + ")"
    a, b = (lean_expr(x) for x in v)
    if op == "and":
        return f"({a} && {b})"
    if op == "or":
        return f"({a} || {b})"
    if op == "xor":
        return f"(({a} && (!{b})) || ((!{a}) && {b}))"
    if op == "implies":
        return f"((!{a}) || {b})"
    if op == "iff":
        return f"(({a} && {b}) || ((!{a}) && (!{b})))"
    raise ValueError("not a finite supported formula")


def bit_witness(a, b):
    xor = a ^ b
    if not xor:
        return None
    bit = (xor & -xor).bit_length() - 1
    values = list(product((False, True), repeat=3))[bit]
    return {"assignment": dict(zip(VARS, values)),
            "source": bool(a & (1 << bit)), "formal": bool(b & (1 << bit))}


def run(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    cases = generated_cases()
    corpus_hash = hashlib.sha256(canonical_bytes(cases)).hexdigest()
    metrics = {"equivalent": 0, "different": 0, "unsupported": 0,
               "false_alarms": 0, "missed_differences": 0,
               "wrong_witnesses": 0, "wrong_status_or_unknown": 0,
               "truth_promotions": 0, "kernel_bypass_promotions": 0}
    results = []
    lean_candidates = {"equivalent": [], "different": []}
    for case in cases:
        source, formal, intent = case["source"], case["formal"], case["generator_intent"]
        if intent == "unsupported":
            expected = "UNKNOWN_UNSUPPORTED_GRAMMAR"
            oracle = None
        else:
            a, b = bitset_oracle(source), bitset_oracle(formal)
            oracle = ("equivalent" if a == b else "different")
            expected = ("FINITE_MATCH_ON_DECLARED_DOMAIN" if a == b
                        else "FINITE_COUNTEREXAMPLE")
            if oracle != intent:
                raise AssertionError(f"generation predicate broken: {case['id']}")
        observed = compare_finite_formulas(source, formal, list(VARS))
        if intent == "equivalent":
            metrics["equivalent"] += 1
        elif intent == "different":
            metrics["different"] += 1
        else:
            metrics["unsupported"] += 1
        if observed["result"] != expected:
            if expected == "FINITE_MATCH_ON_DECLARED_DOMAIN":
                metrics["false_alarms"] += 1
            elif expected == "FINITE_COUNTEREXAMPLE":
                metrics["missed_differences"] += 1
            else:
                metrics["wrong_status_or_unknown"] += 1
        if oracle == "different":
            if observed["witness"] != bit_witness(a, b):
                metrics["wrong_witnesses"] += 1
        elif observed["witness"] is not None:
            metrics["wrong_witnesses"] += 1
        if observed["epistemic"]["truth_promotion"]:
            metrics["truth_promotions"] += 1
        if observed["epistemic"]["lean_kernel_verified_for_this_query"]:
            metrics["kernel_bypass_promotions"] += 1
        if observed["epistemic"]["verified_badge"] != "NOT_ISSUED":
            metrics["kernel_bypass_promotions"] += 1
        results.append({"id": case["id"], "expected": expected,
                        "observed": observed["result"], "witness": observed["witness"]})
        if oracle in lean_candidates:
            lean_candidates[oracle].append((case, bit_witness(a, b)))
    assert all(metrics[k] == 0 for k in (
        "false_alarms", "missed_differences", "wrong_witnesses",
        "wrong_status_or_unknown", "truth_promotions", "kernel_bypass_promotions")), metrics
    lines = [
        "-- Independently kernel-checked finite oracle challenge generated by",
        "-- research/mathgraph_check_machine_oracle_v1.py, deterministic source hash " + corpus_hash,
        "-- This concerns Bool^3 only, NOT English source-statement fidelity.",
        "import Init", "namespace MathGraphMachineOracleV1", "",
    ]
    selected_ids = []
    for kind in ("equivalent", "different"):
        group = lean_candidates[kind]
        # Predeclared unbiased systematic sample, plus fixed adversarial controls.
        selected = [x for i, x in enumerate(group) if i % 3 == 0 or x[0]["id"].startswith("sentinel-")]
        for case, witness in selected:
            idx = len(selected_ids)
            selected_ids.append(case["id"])
            a, b = lean_expr(case["source"]), lean_expr(case["formal"])
            equality = f"(∀ p q r : Bool, ({a}) = ({b}))"
            if kind == "equivalent":
                lines.append(f"theorem oracle_{idx:03d} : {equality} := by decide")
            else:
                lines.append(f"theorem oracle_{idx:03d} : ¬ {equality} := by decide")
                values = witness["assignment"]
                instantiated = {"p": str(values["p"]).lower(),
                                "q": str(values["q"]).lower(),
                                "r": str(values["r"]).lower()}
                # Explicit lambda application avoids naive text substitutions.
                lhs = f"((fun p q r : Bool => {a}) {instantiated['p']} {instantiated['q']} {instantiated['r']})"
                rhs = f"((fun p q r : Bool => {b}) {instantiated['p']} {instantiated['q']} {instantiated['r']})"
                lines.append(f"theorem witness_{idx:03d} : {lhs} ≠ {rhs} := by decide")
            lines.append("")
    lines.append("end MathGraphMachineOracleV1\n")
    (outdir / "MachineOracleV1.lean").write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "schema": "mathgraph.machine-oracle-bool3.v1",
        "seed": SEED,
        "generator": "finite Bool^3 DSL with independent bitset oracle",
        "corpus_sha256": corpus_hash,
        "sampled_lean_cases": len(selected_ids),
        "sampled_lean_ids_sha256": hashlib.sha256(canonical_bytes(selected_ids)).hexdigest(),
        "external_human_labels": 0,
        "llm_calls": 0,
        "total_cases": len(cases),
        "metrics": metrics,
        "semantic_fidelity_in_unrestricted_natural_language": "UNKNOWN",
        "palomar_statement_alignment_comparison": "NOT_RUN",
        "lean_kernel_verified": "PENDING_SEPARATE_PINNED_LEAN_CI",
        "false_truth_promotion": False,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    (outdir / "corpus.json").write_text(json.dumps(cases, sort_keys=True, indent=2) + "\n")
    (outdir / "results.json").write_text(json.dumps(results, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    run(args.out)
