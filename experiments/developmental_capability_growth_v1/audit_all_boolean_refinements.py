#!/usr/bin/env python3
"""Exhaustive global audit for DEVELOPMENTAL_CAPABILITY_GROWTH_V1.

Enumerates all 2^8 Boolean one-bit feature refinements of the 8-state world.
This removes dependence on the small named candidate family when asking what
the verified obstruction mathematically constrains.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations, product
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("developmental_capability_growth_v1", HERE / "run.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)


def fn_from_vector(vector):
    lookup = dict(zip(m.WORLD, vector))
    return lambda x: lookup[x]


def separates_all_certified_conflicts(feature) -> bool:
    """Whether feature separates every same-R0 pair needing different labels."""
    for xs in m.cells(BASELINE).values():
        for x, y in combinations(xs, 2):
            if m.target_discovery(x) != m.target_discovery(y):
                if feature(x) == feature(y):
                    return False
    return True


BASELINE = m.Representation("PARITY_QUOTIENT", (("parity", m.parity),))

rows = []
for vector in product((0, 1), repeat=len(m.WORLD)):
    feature = fn_from_vector(vector)
    rep = BASELINE.extend("anonymous_boolean_feature", feature)
    succeeds = m.target_in_closure(rep, m.target_discovery)
    exhaustive = m.exhaustive_target_in_closure(rep, m.target_discovery)
    separates = separates_all_certified_conflicts(feature)
    rows.append(
        {
            "vector": list(vector),
            "succeeds": succeeds,
            "exhaustive_succeeds": exhaustive,
            "separates_all_certified_conflicts": separates,
            "cell_count": len(m.cells(rep)),
            "partition_signature": repr(m.partition_signature(rep)),
        }
    )

successful = [r for r in rows if r["succeeds"]]
partition_classes = Counter(r["partition_signature"] for r in successful)
cell_counts = Counter(r["cell_count"] for r in successful)

# In this exact finite setup, extending R0 by one Boolean feature repairs T1 iff
# the feature separates every pair that the obstruction certificate says R0
# incorrectly identifies. This is a complete necessary-and-sufficient test,
# not merely a correlation on the named candidate family.
gates = {
    "A0_all_256_boolean_refinements_enumerated": len(rows) == 256,
    "A1_analytic_and_literal_closure_tests_agree": all(
        r["succeeds"] == r["exhaustive_succeeds"] for r in rows
    ),
    "A2_obstruction_separation_is_necessary_and_sufficient": all(
        r["succeeds"] == r["separates_all_certified_conflicts"] for r in rows
    ),
    "A3_success_set_is_nontrivial_and_constrained": 0 < len(successful) < len(rows),
}

report = {
    "protocol": "DEVELOPMENTAL_CAPABILITY_GROWTH_V1_GLOBAL_BOOLEAN_AUDIT",
    "boolean_refinements_tested": len(rows),
    "successful_refinements": len(successful),
    "failed_refinements": len(rows) - len(successful),
    "successful_partition_classes": len(partition_classes),
    "successful_cell_count_distribution": dict(sorted(cell_counts.items())),
    "minimum_successful_cell_count": min(r["cell_count"] for r in successful),
    "maximum_successful_cell_count": max(r["cell_count"] for r in successful),
    "interpretation": (
        "The obstruction does not uniquely name a literal feature. It exactly constrains "
        "the successful refinement class: a one-bit refinement succeeds iff it separates "
        "every conflicting pair exposed by the old representation."
    ),
    "gates": gates,
    "verdict": "PASS_GLOBAL_REFINEMENT_CLASS_AUDIT" if all(gates.values()) else "FAIL",
}

print("GLOBAL BOOLEAN REFINEMENT AUDIT")
print("-------------------------------")
print(f"All one-bit features tested: {len(rows)}")
print(f"Successful refinements:      {len(successful)}")
print(f"Partition classes:           {len(partition_classes)}")
print(f"Successful cell counts:      {dict(sorted(cell_counts.items()))}")
print("Success iff obstruction conflicts are separated:", gates["A2_obstruction_separation_is_necessary_and_sufficient"])
print("VERDICT:", report["verdict"])
print("\nFULL CERTIFICATE")
print(json.dumps(report, indent=2, sort_keys=True))

if report["verdict"] != "PASS_GLOBAL_REFINEMENT_CLASS_AUDIT":
    raise SystemExit(1)
