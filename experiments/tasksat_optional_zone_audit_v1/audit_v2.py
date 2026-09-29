#!/usr/bin/env python3
import copy
import json
import sys
from pathlib import Path

tasksat_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tasksat_root / "src" / "smt"))

from tasknet_ast import TaskKind  # noqa: E402
from tasknet_parser import parse_tasknet  # noqa: E402
from tasknet_smt import TaskNetTL  # noqa: E402


def stock_sat(source: str) -> bool:
    tn = parse_tasknet(source)
    enc = TaskNetTL(tn, error_trace=False, use_optimization=False, track=False, portfolio=False)
    model, _ = enc.solve(analyze_core=False)
    return model is not None


def erased_exclusion_sat(source: str) -> bool:
    """Reference world for cases where all OPTIONAL/REQUEST tasks are forced absent.

    This does not claim to be the full intended semantics. It is the smallest
    consequence oracle: if a task is forced excluded, erase it before constructing
    zones, exactly matching the documentation's subset-of-optional-tasks schedule.
    """
    tn = parse_tasknet(source)
    ref = copy.deepcopy(tn)
    ref.tasks = [t for t in ref.tasks if t.kind not in (TaskKind.OPTIONAL, TaskKind.REQUEST)]
    enc = TaskNetTL(ref, error_trace=False, use_optimization=False, track=False, portfolio=False)
    model, _ = enc.solve(analyze_core=False)
    return model is not None


def source(n: int, horizon: int) -> str:
    ghosts = "\n".join(
        f"""  optional task ghost_{i} {{
    start_range [{horizon + 10}, {horizon + 10}];
  }}"""
        for i in range(n)
    )
    return f"""tasknet GhostFamily {{
  end = {horizon};
{ghosts}
}}
"""


matrix = []
mismatches = []
for n in range(0, 6):
    for h in range(1, 13):
        src = source(n, h)
        stock = stock_sat(src)
        ref = erased_exclusion_sat(src)
        predicted_stock = h >= (2 * n + 1)
        if stock != predicted_stock:
            raise AssertionError(
                f"stock law failed at n={n}, H={h}: stock={stock}, predicted={predicted_stock}"
            )
        if not ref:
            raise AssertionError(f"erasure reference should be SAT at n={n}, H={h}")
        row = {
            "declared_optional_tasks": n,
            "horizon": h,
            "stock_sat": stock,
            "erased_exclusion_sat": ref,
            "stock_boundary_law": f"H >= {2*n+1}",
        }
        matrix.append(row)
        if stock != ref:
            mismatches.append(row)

# Property-level consequence: a forced-excluded ghost changes the universal
# verdict only by contributing phantom observation points.
base_prop = """
tasknet BaseProperty {
  end = 3;
  properties {
    prop no_time_1: always not (time = 1);
  }
}
"""
ghost_prop = """
tasknet GhostProperty {
  end = 3;
  optional task ghost {
    start_range [10, 10];
  }
  properties {
    prop no_time_1: always not (time = 1);
  }
}
"""


def property_counterexample_sat(source: str, erased: bool = False) -> bool:
    tn = parse_tasknet(source)
    if erased:
        tn = copy.deepcopy(tn)
        tn.tasks = [t for t in tn.tasks if t.kind not in (TaskKind.OPTIONAL, TaskKind.REQUEST)]
    prop = tn.properties[0]
    enc = TaskNetTL(tn, error_trace=False, use_optimization=False, track=False, portfolio=False)
    enc.solver.add(~enc._encode_formula_at_pos(prop.formula, 0))
    return str(enc.solver.check()) == "sat"


base_cex = property_counterexample_sat(base_prop)
ghost_stock_cex = property_counterexample_sat(ghost_prop)
ghost_ref_cex = property_counterexample_sat(ghost_prop, erased=True)
assert base_cex is False, "base property must hold"
assert ghost_stock_cex is True, "stock encoding must find a phantom-zone counterexample"
assert ghost_ref_cex is False, "erasing the forced-excluded ghost must restore the property"

evidence = {
    "finding": "OPTIONAL_ZONE_COMPLETENESS_LAW_AND_PROPERTY_NONINERTNESS",
    "law": {
        "statement": "For N declared schedulable tasks, current strict integer zone skeleton requires H >= 2N+1.",
        "tested_optional_counts": [0, 1, 2, 3, 4, 5],
        "tested_horizons": [1, 12],
        "matrix_cases": len(matrix),
        "mismatches_stock_vs_erased_reference": len(mismatches),
        "mismatch_cases": mismatches,
    },
    "property_witness": {
        "formula": "always not (time = 1)",
        "base_counterexample_exists": base_cex,
        "forced_excluded_ghost_stock_counterexample_exists": ghost_stock_cex,
        "forced_excluded_ghost_erased_reference_counterexample_exists": ghost_ref_cex,
        "consequence": "stock property verdict changes solely from an excluded task's observation points",
    },
}
Path("tasksat_optional_zone_audit_v2_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
print("PASS_TASKSAT_OPTIONAL_ZONE_GENERAL_LAW")
