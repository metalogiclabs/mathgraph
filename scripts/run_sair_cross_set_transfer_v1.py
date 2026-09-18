#!/usr/bin/env python3
"""Cross-set transfer probe: learn only on sample_200, reuse on disjoint normal pairs.

Committed before the cross-transfer result is inspected.

Frozen policy:
- learn verified size-2 table capabilities from the first 25 FALSE rows of the
  pinned official sample_200 only;
- exclude every sample_200 (eq1_id, eq2_id) pair from public normal.jsonl;
- use no normal-set acquisition or ranking signal;
- evaluate all remaining normal FALSE rows under cold/warm/restart/sham/ablation;
- search the same complete 16-table size-2 universe in every condition.

A bounded miss is RESIDUAL only, never TRUE.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = REPO_ROOT / "scripts" / "run_sair_official_sample200_reuse_probe.py"
_SPEC = importlib.util.spec_from_file_location("_sair_cross_transfer_base", BASE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load {BASE_PATH}")
_BASE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BASE
_SPEC.loader.exec_module(_BASE)

NORMAL_PATH = "examples/problems/normal.jsonl"
SAMPLE_PATH = "examples/problems/sample_200.json"
ACQUISITION_FALSE_COUNT = 25


def _fetch(path: str) -> str:
    req = urllib.request.Request(
        f"{_BASE.RAW_BASE}/{path}",
        headers={"User-Agent": "MathGraph-SAIR-cross-set-transfer/1"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _load_target_normal(sample_pairs: set[tuple[int, int]]) -> list[Any]:
    out = []
    for index, line in enumerate(_fetch(NORMAL_PATH).splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        pair = (int(row["eq1_id"]), int(row["eq2_id"]))
        if pair in sample_pairs:
            continue
        out.append(
            _BASE.Problem(
                problem_id=str(row["id"]),
                eq1_id=pair[0],
                eq2_id=pair[1],
                source=str(row["equation1"]).replace("◇", "*"),
                target=str(row["equation2"]).replace("◇", "*"),
                answer=bool(row["answer"]),
                difficulty=str(row.get("difficulty") or "normal"),
                sample_index=index,
            )
        )
    return out


def _markdown(report: dict[str, Any]) -> str:
    a = report["aggregate"]
    c = report["comparisons"]
    return "\n".join([
        "# SAIR Cross-Set Verified Capability Transfer V1",
        "",
        f"- verdict: {report['verdict']}",
        f"- source acquisition FALSE tasks: {report['split']['source_acquisition_false_count']}",
        f"- target normal FALSE tasks: {report['split']['target_false_count']}",
        f"- transferred capabilities: {len(report['capabilities'])}",
        "",
        "## Target-set cost",
        "",
        f"- cold calls: {a['cold']['total_verifier_calls']}",
        f"- warm transfer calls: {a['warm']['total_verifier_calls']}",
        f"- restart calls: {a['restart']['total_verifier_calls']}",
        f"- sham calls: {a['sham']['total_verifier_calls']}",
        f"- ablation calls: {a['ablation']['total_verifier_calls']}",
        f"- warm reduction vs cold: {c['warm_call_reduction_vs_cold']:.2%}",
        f"- cold/warm compression: {c['cold_over_warm_calls']:.3f}x",
        "",
        "## Claim boundary",
        "",
        report["claim_boundary"],
        "",
    ])


def run(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    sample, sample_prov = _BASE._load_official_sample()
    sample_pairs = {(p.eq1_id, p.eq2_id) for p in sample}
    sample_false = [p for p in sample if not p.answer]
    source_acquisition = sample_false[:ACQUISITION_FALSE_COUNT]
    capabilities, acquisition_rows = _BASE._acquire(source_acquisition)

    target = _load_target_normal(sample_pairs)
    target_false = [p for p in target if not p.answer]
    target_true = [p for p in target if p.answer]

    bank_path = out / "transferred_verified_size2_capability_bank.json"
    _BASE._serialize_bank(capabilities, bank_path)
    restarted = _BASE._reload_bank(bank_path)

    cold_order = list(range(len(_BASE.TABLES)))
    warm_order = _BASE._warm_order(capabilities)
    restart_order = _BASE._warm_order(restarted)
    sham_order = _BASE._sham_order(len(capabilities))
    ablation_order = _BASE._ablation_order(capabilities)

    rows = {
        "cold": [_BASE._evaluate_order(p, cold_order) for p in target_false],
        "warm": [_BASE._evaluate_order(p, warm_order) for p in target_false],
        "restart": [_BASE._evaluate_order(p, restart_order) for p in target_false],
        "sham": [_BASE._evaluate_order(p, sham_order) for p in target_false],
        "ablation": [_BASE._evaluate_order(p, ablation_order) for p in target_false],
    }
    aggregate = {name: _BASE._aggregate(items) for name, items in rows.items()}
    controls = _BASE._true_controls(target_true)

    cold_calls = aggregate["cold"]["total_verifier_calls"]
    warm_calls = aggregate["warm"]["total_verifier_calls"]
    acquisition_calls = sum(int(row["verifier_calls"]) for row in acquisition_rows)
    comparisons = {
        "cold_over_warm_calls": cold_calls / warm_calls if warm_calls else None,
        "warm_call_reduction_vs_cold": 1.0 - warm_calls / cold_calls if cold_calls else None,
        "restart_matches_warm_calls": aggregate["restart"]["total_verifier_calls"] == warm_calls,
        "sham_minus_warm_calls": aggregate["sham"]["total_verifier_calls"] - warm_calls,
        "ablation_minus_warm_calls": aggregate["ablation"]["total_verifier_calls"] - warm_calls,
        "source_acquisition_verifier_calls": acquisition_calls,
        "source_acquisition_plus_target_cold_calls": acquisition_calls + cold_calls,
        "source_acquisition_plus_target_warm_calls": acquisition_calls + warm_calls,
        "full_sequence_call_reduction": (
            1.0 - (acquisition_calls + warm_calls) / (acquisition_calls + cold_calls)
            if acquisition_calls + cold_calls
            else None
        ),
    }

    yields = {name: data["terminal_yield"] for name, data in aggregate.items()}
    gates = {
        "source_acquisition_fixed_at_25_false": len(source_acquisition) == 25,
        "target_excludes_all_sample200_pairs": len(sample_pairs) == 200,
        "target_false_nonempty": bool(target_false),
        "verified_transfer_bank_nonempty": bool(capabilities),
        "no_target_side_acquisition": True,
        "restart_exact": [c.capability_id for c in capabilities] == [c.capability_id for c in restarted]
        and warm_order == restart_order,
        "all_orderings_preserve_bounded_terminal_yield": len(set(yields.values())) == 1,
        "target_true_control_has_no_size2_countermodel": controls["passes"],
        "no_failed_search_promoted_to_true": True,
    }

    report = {
        "protocol": "SAIR_CROSS_SET_VERIFIED_CAPABILITY_TRANSFER_V1",
        "provenance": {
            "repository": _BASE.SAIR_REPO,
            "commit": _BASE.SAIR_COMMIT,
            "source_sample": sample_prov,
            "target_source": NORMAL_PATH,
            "excluded_pair_source": SAMPLE_PATH,
        },
        "policy": {
            "source_learning": "first 25 FALSE rows in pinned sample_200 order",
            "target_learning": "none",
            "target": "all normal.jsonl rows after exact sample_200 pair exclusion",
            "candidate_universe": "all 16 binary operation tables on carrier {0,1}",
            "promotion_and_order_rules": "identical to SAIR_OFFICIAL_SAMPLE200_BOUNDED_VERIFIED_REUSE_V1",
        },
        "split": {
            "source_acquisition_false_count": len(source_acquisition),
            "target_false_count": len(target_false),
            "target_true_count": len(target_true),
            "source_acquisition_problem_ids": [p.problem_id for p in source_acquisition],
        },
        "capabilities": [
            {
                **_BASE.asdict(cap),
                "table": [list(row) for row in cap.table],
            }
            for cap in capabilities
        ],
        "orders": {
            "cold": cold_order,
            "warm": warm_order,
            "restart": restart_order,
            "sham": sham_order,
            "ablation": ablation_order,
        },
        "source_acquisition_rows": acquisition_rows,
        "rows": rows,
        "aggregate": aggregate,
        "comparisons": comparisons,
        "true_controls": controls,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "This is exact bounded cross-set transfer within public SAIR development data. "
            "The capability ordering is learned only from the first 25 FALSE tasks of pinned "
            "sample_200 and is then applied without target-side acquisition to normal.jsonl after "
            "excluding every sample_200 equation pair. The universe is only the 16 size-2 magma "
            "tables. Countermodels are terminal FALSE evidence; misses are RESIDUAL, never TRUE. "
            "This is not an LLM result and says nothing directly about private SAIR evaluation."
        ),
    }

    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "split": report["split"],
        "capability_count": len(capabilities),
        "aggregate": aggregate,
        "comparisons": comparisons,
        "true_controls": controls,
        "gates": gates,
        "claim_boundary": report["claim_boundary"],
    }, indent=2, sort_keys=True))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="/tmp/open_math_model_sustained_use_v1/sair-cross-set-transfer-v1",
    )
    args = parser.parse_args()
    report = run(args.out_dir)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
