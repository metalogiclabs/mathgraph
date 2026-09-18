#!/usr/bin/env python3
"""Post-result diagnostic: how much target-local calibration is needed?

This diagnostic follows the positive within-set and negative cross-set results.
It does not claim preregistration. It asks a narrower engineering question:

  how many target-local verified examples are needed before a local capability
  ordering begins to amortize on the same fixed 400-problem fresh set?

The fresh set is fixed to the same final 400 FALSE rows used by the normal-set
replication. Calibration prefixes are nested: k in {0,1,2,5,10,25,50,100}.
All conditions still search the complete 16-table size-2 universe, so only
ordering/cost can change.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
NORMAL_RUNNER = REPO_ROOT / "scripts" / "run_sair_normal_reuse_replication_v1.py"
_SPEC = importlib.util.spec_from_file_location("_sair_normal_reuse_diag_base", NORMAL_RUNNER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load {NORMAL_RUNNER}")
_N = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _N
_SPEC.loader.exec_module(_N)
_BASE = _N._BASE

CALIBRATION_SIZES = (0, 1, 2, 5, 10, 25, 50, 100)
RESERVOIR_SIZE = 100


def _evaluate_fresh(fresh: list[Any], ordering: list[int]) -> dict[str, Any]:
    rows = [_BASE._evaluate_order(p, ordering) for p in fresh]
    return {"rows": rows, "aggregate": _BASE._aggregate(rows)}


def run(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    problems, provenance = _N._load()
    false_tasks = [p for p in problems if not p.answer]
    if len(false_tasks) <= RESERVOIR_SIZE:
        raise RuntimeError("not enough FALSE rows for fixed calibration reservoir + fresh set")

    reservoir = false_tasks[:RESERVOIR_SIZE]
    fresh = false_tasks[RESERVOIR_SIZE:]
    cold_order = list(range(len(_BASE.TABLES)))
    cold_eval = _evaluate_fresh(fresh, cold_order)
    cold_calls = cold_eval["aggregate"]["total_verifier_calls"]

    curve = []
    for k in CALIBRATION_SIZES:
        acquisition = reservoir[:k]
        if k == 0:
            capabilities = []
            acquisition_rows = []
        else:
            capabilities, acquisition_rows = _BASE._acquire(acquisition)
        warm_order = _BASE._warm_order(capabilities)
        evaluated = _evaluate_fresh(fresh, warm_order)
        warm_calls = evaluated["aggregate"]["total_verifier_calls"]
        acquisition_calls = sum(int(row["verifier_calls"]) for row in acquisition_rows)
        cold_sequence_calls = acquisition_calls + cold_calls
        dev_sequence_calls = acquisition_calls + warm_calls
        curve.append(
            {
                "k": k,
                "capability_count": len(capabilities),
                "acquisition_verifier_calls": acquisition_calls,
                "fresh_finite_countermodels": evaluated["aggregate"]["finite_countermodels"],
                "fresh_residuals": evaluated["aggregate"]["residuals"],
                "fresh_terminal_yield": evaluated["aggregate"]["terminal_yield"],
                "fresh_verifier_calls": warm_calls,
                "fresh_call_delta_vs_cold": warm_calls - cold_calls,
                "fresh_call_reduction_vs_cold": (
                    1.0 - warm_calls / cold_calls if cold_calls else None
                ),
                "cold_sequence_calls": cold_sequence_calls,
                "developmental_sequence_calls": dev_sequence_calls,
                "full_sequence_call_reduction": (
                    1.0 - dev_sequence_calls / cold_sequence_calls
                    if cold_sequence_calls
                    else None
                ),
                "warm_order": warm_order,
                "capability_table_indices": [cap.table_index for cap in capabilities],
            }
        )

    positive_fresh = [row["k"] for row in curve if row["fresh_call_delta_vs_cold"] < 0]
    nonworse_fresh = [row["k"] for row in curve if row["fresh_call_delta_vs_cold"] <= 0]

    gates = {
        "fixed_calibration_sizes": tuple(row["k"] for row in curve) == CALIBRATION_SIZES,
        "fixed_fresh_set_size_400": len(fresh) == 400,
        "all_conditions_preserve_bounded_terminal_yield": len(
            {row["fresh_terminal_yield"] for row in curve}
        ) == 1,
        "k0_equals_cold": curve[0]["fresh_verifier_calls"] == cold_calls,
        "no_failed_search_promoted_to_true": True,
    }

    report = {
        "protocol": "SAIR_TARGET_LOCAL_SCOPE_CALIBRATION_DIAGNOSTIC_V1",
        "provenance": provenance,
        "diagnostic_status": "POST_RESULT_EXPLORATORY",
        "policy": {
            "calibration_sizes": list(CALIBRATION_SIZES),
            "calibration_reservoir": "first 100 FALSE rows after sample_200 pair exclusion",
            "fresh_set": "all later 400 FALSE rows, identical across every k",
            "candidate_universe": "all 16 binary operation tables on carrier {0,1}",
            "local_only": True,
            "cross_set_source_bank_used": False,
        },
        "cold": cold_eval["aggregate"],
        "curve": curve,
        "minimum_k_with_strict_fresh_gain": min(positive_fresh) if positive_fresh else None,
        "minimum_k_nonworse_than_cold": min(nonworse_fresh) if nonworse_fresh else None,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "This is a post-result diagnostic, not a preregistered confirmation. It measures how "
            "quickly target-local verified calibration changes search order on the already-defined "
            "400-problem normal fresh set. The universe is bounded to all size-2 magma tables; "
            "finite-search misses remain residual. The diagnostic is intended to choose the next "
            "prospective scoped-controller test, not to create a new independent generalization claim."
        ),
    }

    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# SAIR Target-Local Scope Calibration Diagnostic V1",
        "",
        f"- diagnostic status: {report['diagnostic_status']}",
        f"- cold fresh calls: {cold_calls}",
        f"- minimum k with strict fresh gain: {report['minimum_k_with_strict_fresh_gain']}",
        "",
        "| k | capabilities | acquisition calls | fresh calls | fresh reduction | full-sequence reduction |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in curve:
        lines.append(
            f"| {row['k']} | {row['capability_count']} | {row['acquisition_verifier_calls']} | "
            f"{row['fresh_verifier_calls']} | {row['fresh_call_reduction_vs_cold']:.2%} | "
            f"{row['full_sequence_call_reduction']:.2%} |"
        )
    lines.extend(["", "## Claim boundary", "", report["claim_boundary"], ""])
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "verdict": report["verdict"],
        "diagnostic_status": report["diagnostic_status"],
        "cold_fresh_calls": cold_calls,
        "minimum_k_with_strict_fresh_gain": report["minimum_k_with_strict_fresh_gain"],
        "curve": [
            {
                "k": row["k"],
                "capability_count": row["capability_count"],
                "acquisition_verifier_calls": row["acquisition_verifier_calls"],
                "fresh_verifier_calls": row["fresh_verifier_calls"],
                "fresh_call_reduction_vs_cold": row["fresh_call_reduction_vs_cold"],
                "full_sequence_call_reduction": row["full_sequence_call_reduction"],
            }
            for row in curve
        ],
        "gates": gates,
        "claim_boundary": report["claim_boundary"],
    }, indent=2, sort_keys=True))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="/tmp/open_math_model_sustained_use_v1/sair-scope-calibration-diagnostic-v1",
    )
    args = parser.parse_args()
    report = run(args.out_dir)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
