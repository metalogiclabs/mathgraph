"""Frozen finite ACSL-source claims and separate, falsifiable comparison controls.

No outcome from an actual compiler is inferred here. Native receipts are supplied
by native_run.py, and their absence is an explicit UNKNOWN.
"""
from __future__ import annotations

from itertools import combinations, product
from pathlib import Path
import sys

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
from decision_sufficient_observation_v1.decision_mode import compile_decision_sufficient

VALUES = (-1, 0, 1)
RESET_A = (-2, 0, 3)


def full_population() -> dict[str, list[tuple[int, ...]]]:
    resets = [(a, b) for a in RESET_A for b in VALUES]
    vectors = []
    replacements = []
    for n in range(4):
        for a in product(VALUES, repeat=n):
            padded_a = (*a, *((0,) * (3 - n)))
            for b in product(VALUES, repeat=n):
                padded_b = (*b, *((0,) * (3 - n)))
                vectors.append((n, *padded_a, *padded_b))
            for old, new in product(VALUES, repeat=2):
                replacements.append((n, *padded_a, old, new))
    return {
        "conditional_reset": resets,
        "vector_addition": vectors,
        "search_replace": replacements,
    }


def contract_output(case: str, row: tuple[int, ...]) -> tuple[int, ...]:
    if case == "conditional_reset":
        a, b = row
        return (0 if b != 0 else a, b)
    if case == "vector_addition":
        n, *arrays = row
        a, b = arrays[:3], arrays[3:]
        return (*(a[i] + b[i] if i < n else a[i] for i in range(3)), *b)
    if case == "search_replace":
        n, a0, a1, a2, old, new = row
        return tuple(new if i < n and x == old else x for i, x in enumerate((a0, a1, a2)))
    raise ValueError(f"Unknown frozen case {case}")


MUTANTS = {
    "conditional_reset": ("always_zero", "never_zero"),
    "vector_addition": ("skip_last", "mutate_b"),
    "search_replace": ("skip_last", "replace_unequal"),
}


def mutants(case: str) -> tuple[str, ...]:
    return MUTANTS[case]


def mutant_output(case: str, mutant: str, row: tuple[int, ...]) -> tuple[int, ...]:
    if mutant not in mutants(case):
        raise ValueError(f"Undeclared mutant {case}/{mutant}")
    if case == "conditional_reset":
        a, b = row
        return (0 if mutant == "always_zero" else a, b)
    if case == "vector_addition":
        n, *arrays = row
        a, b = list(arrays[:3]), list(arrays[3:])
        if mutant == "skip_last":
            for i in range(max(0, n-1)):
                a[i] += b[i]
        else:
            for i in range(n):
                a[i] += b[i]
            if n:
                b[0] += 1
        return (*a, *b)
    n, *contents = row
    a, old, new = list(contents[:3]), contents[3], contents[4]
    if mutant == "skip_last":
        for i in range(max(0, n-1)):
            if a[i] == old:
                a[i] = new
    else:
        for i in range(n):
            if a[i] != old:
                a[i] = new
    return tuple(a)


def synthesize_minimum_probes(case: str) -> dict:
    """Compare MathGraph's exact solver against an independently coded subset oracle.

    This probe search concerns three synthetic *behavior hypotheses*, not an
    empirical claim about whether the real generated Rust is defective.
    """
    if case != "conditional_reset":
        raise ValueError("Only reset three-hypothesis probe grammar was preregistered")
    probes = ((3, 0), (3, 1))
    candidates = [
        tuple(f((p[0], p[1]))[0] for f in (
            lambda x: contract_output(case, x),
            lambda x: mutant_output(case, "always_zero", x),
            lambda x: mutant_output(case, "never_zero", x)))
        for p in probes
    ]
    goals = (0, 1, 1)  # Correct behavior vs either wrong behavior.
    obj = {
        "name": "frozen_reset_hypotheses", "protected": [0, 0, 0],
        "operations": [],
        "readouts": [{"name": f"probe_{i}", "values": list(v), "cost": 1}
                     for i, v in enumerate(candidates)],
        "grants": ["probe_0", "probe_1"], "base_readouts": [],
        "desired_labels": list(goals),
    }
    result = compile_decision_sufficient(obj)
    # Distinct implementation: enumerate every subset, test the decoder
    # condition by direct pairwise comparison, select smallest cost.
    conventional = None
    for size in range(len(candidates)+1):
        for indices in combinations(range(len(candidates)), size):
            adequate = all(
                goals[i] == goals[j] or any(candidates[k][i] != candidates[k][j]
                                                for k in indices)
                for i, j in combinations(range(len(goals)), 2))
            if adequate:
                conventional = size
                break
        if conventional is not None:
            break
    result["conventional_minimum_cost"] = conventional
    result["relative_result"] = (
        "BASELINE_TIE" if result.get("basis_cost") == conventional
        else "DIFFERENT_COST_REQUIRES_INVESTIGATION")
    result["hypotheses"] = ["source_correct", "always_zero", "never_zero"]
    return result


def review_one(case: str, row: tuple[int, ...], evidence: dict) -> str:
    if not all(evidence.get(k) is True for k in
               ("source_pin_ok", "target_pin_ok", "contract_active")):
        return "UNKNOWN_SOURCE_AUTHORITY"
    source = evidence.get("native_source")
    target = evidence.get("native_target")
    if source is None or target is None:
        return "UNKNOWN_NATIVE_OBSERVATION"
    if tuple(source) != contract_output(case, row):
        return "SOURCE_CONTRACT_DISAGREEMENT"
    if tuple(target) != tuple(source):
        return "DEMONSTRATED_DEFECT"
    return "WARRANTED_BOUNDED_MATCH"
