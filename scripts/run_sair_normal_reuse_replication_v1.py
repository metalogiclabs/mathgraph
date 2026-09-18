#!/usr/bin/env python3
"""Pre-result replication of bounded verified reuse on SAIR public normal.jsonl.

This replication is committed before its result is inspected. To separate it
from the earlier official sample_200 probe, every exact (eq1_id, eq2_id) pair
present in sample_200 is excluded before splitting.

Frozen policy:
- pinned SAIR repository commit;
- public normal.jsonl only;
- exclude sample_200 equation pairs;
- first 100 remaining FALSE rows are acquisition;
- every later remaining FALSE row is fresh evaluation;
- complete size-2 magma universe (16 tables);
- same promotion, warm, restart, fixed-sham and ablation ordering rules as V1.

A failed bounded search is RESIDUAL only, never TRUE.
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
BASE_RUNNER = REPO_ROOT / "scripts" / "run_sair_official_sample200_reuse_probe.py"
_SPEC = importlib.util.spec_from_file_location("_sair_sample200_reuse_base", BASE_RUNNER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load base runner from {BASE_RUNNER}")
_BASE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BASE
_SPEC.loader.exec_module(_BASE)

SAIR_COMMIT = _BASE.SAIR_COMMIT
RAW_BASE = _BASE.RAW_BASE
NORMAL_PATH = "examples/problems/normal.jsonl"
SAMPLE_PATH = "examples/problems/sample_200.json"
ACQUISITION_FALSE_COUNT = 100


def _fetch_text(path: str) -> str:
    url = f"{RAW_BASE}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "MathGraph-SAIR-normal-reuse-replication/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _load() -> tuple[list[Any], dict[str, Any]]:
    sample = json.loads(_fetch_text(SAMPLE_PATH))
    excluded_pairs = {(int(row["eq1_id"]), int(row["eq2_id"])) for row in sample}

    rows = []
    raw_normal = _fetch_text(NORMAL_PATH)
    for index, line in enumerate(raw_normal.splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        pair = (int(row["eq1_id"]), int(row["eq2_id"]))
        if pair in excluded_pairs:
            continue
        rows.append(
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
    return rows, {
        "repository": _BASE.SAIR_REPO,
        "commit": SAIR_COMMIT,
        "source": NORMAL_PATH,
        "excluded_pair_source": SAMPLE_PATH,
        "excluded_pair_count": len(excluded_pairs),
        "remaining_problem_count": len(rows),
    }


def _markdown(report: dict[str, Any]) -> str:
    a = report["aggregate"]
    c = report["comparisons"]
    return "\n".join([
        "# SAIR Public Normal — Bounded Verified Reuse Replication V1",
        "",
        f"- verdict: {report['verdict']}",
        f"- pinned commit: {report['provenance']['commit']}",
        f"- remaining problems after sample_200 pair exclusion: {report['provenance']['remaining_problem_count']}",
        f"- acquisition FALSE tasks: {report['split']['acquisition_false_count']}",
        f"- fresh FALSE tasks: {report['split']['fresh_false_count']}",
        f"- promoted capabilities: {len(report['capabilities'])}",
        "",
        "## Fresh set",
        "",
        f"- cold calls: {a['cold']['total_verifier_calls']}",
        f"- warm calls: {a['warm']['total_verifier_calls']}",
        f"- restart calls: {a['restart']['total_verifier_calls']}",
        f"- sham calls: {a['sham']['total_verifier_calls']}",
        f"- ablation calls: {a['ablation']['total_verifier_calls']}",
        f"- warm reduction vs cold: {c['warm_call_reduction_vs_cold']:.2%}",
        f"- cold/warm compression: {c['cold_over_warm_calls']:.3f}x",
        "",
        "## Full acquisition + fresh sequence",
        "",
        f"- cold baseline calls: {c['full_sequence_cold_calls']}",
        f"- developmental calls: {c['full_sequence_developmental_calls']}",
        f"- reduction: {c['full_sequence_call_reduction']:.2%}",
        "",
        "## Claim boundary",
        "",
        report["claim_boundary"],
        "",
    ])


def run(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    problems, provenance = _load()
    false_tasks = [p for p in problems if not p.answer]
    true_tasks = [p for p in problems if p.answer]
    if len(false_tasks) <= ACQUISITION_FALSE_COUNT:
        raise RuntimeError(
            f"need >{ACQUISITION_FALSE_COUNT} FALSE tasks after exclusion, found {len(false_tasks)}"
        )

    acquisition = false_tasks[:ACQUISITION_FALSE_COUNT]
    fresh = false_tasks[ACQUISITION_FALSE_COUNT:]
    capabilities, acquisition_rows = _BASE._acquire(acquisition)

    bank_path = out / "verified_size2_capability_bank.json"
    _BASE._serialize_bank(capabilities, bank_path)
    restarted = _BASE._reload_bank(bank_path)

    cold_order = list(range(len(_BASE.TABLES)))
    warm_order = _BASE._warm_order(capabilities)
    restart_order = _BASE._warm_order(restarted)
    sham_order = _BASE._sham_order(len(capabilities))
    ablation_order = _BASE._ablation_order(capabilities)

    rows = {
        "cold": [_BASE._evaluate_order(p, cold_order) for p in fresh],
        "warm": [_BASE._evaluate_order(p, warm_order) for p in fresh],
        "restart": [_BASE._evaluate_order(p, restart_order) for p in fresh],
        "sham": [_BASE._evaluate_order(p, sham_order) for p in fresh],
        "ablation": [_BASE._evaluate_order(p, ablation_order) for p in fresh],
    }
    aggregate = {name: _BASE._aggregate(items) for name, items in rows.items()}
    controls = _BASE._true_controls(true_tasks)

    cold_calls = aggregate["cold"]["total_verifier_calls"]
    warm_calls = aggregate["warm"]["total_verifier_calls"]
    acquisition_calls = sum(int(row["verifier_calls"]) for row in acquisition_rows)
    full_cold = acquisition_calls + cold_calls
    full_dev = acquisition_calls + warm_calls

    comparisons = {
        "cold_over_warm_calls": cold_calls / warm_calls if warm_calls else None,
        "warm_call_reduction_vs_cold": 1.0 - warm_calls / cold_calls if cold_calls else None,
        "restart_matches_warm_calls": aggregate["restart"]["total_verifier_calls"] == warm_calls,
        "sham_minus_warm_calls": aggregate["sham"]["total_verifier_calls"] - warm_calls,
        "ablation_minus_warm_calls": aggregate["ablation"]["total_verifier_calls"] - warm_calls,
        "acquisition_verifier_calls": acquisition_calls,
        "full_sequence_cold_calls": full_cold,
        "full_sequence_developmental_calls": full_dev,
        "full_sequence_call_reduction": 1.0 - full_dev / full_cold if full_cold else None,
    }

    yields = {name: data["terminal_yield"] for name, data in aggregate.items()}
    gates = {
        "sample200_pairs_excluded": provenance["excluded_pair_count"] == 200,
        "acquisition_split_fixed_at_100_false": len(acquisition) == ACQUISITION_FALSE_COUNT,
        "fresh_false_nonempty": bool(fresh),
        "verified_capability_bank_nonempty": bool(capabilities),
        "restart_exact": [c.capability_id for c in capabilities] == [c.capability_id for c in restarted]
        and restart_order == warm_order,
        "all_orderings_preserve_bounded_terminal_yield": len(set(yields.values())) == 1,
        "true_label_control_has_no_size2_countermodel": controls["passes"],
        "no_failed_search_promoted_to_true": True,
    }

    report = {
        "protocol": "SAIR_PUBLIC_NORMAL_BOUNDED_VERIFIED_REUSE_REPLICATION_V1",
        "provenance": provenance,
        "policy": {
            "candidate_universe": "all 16 binary operation tables on carrier {0,1}",
            "sample200_pair_exclusion": True,
            "acquisition_rule": "first 100 remaining FALSE rows in pinned normal.jsonl order",
            "fresh_rule": "all later remaining FALSE rows",
            "promotion_and_order_rules": "identical to SAIR_OFFICIAL_SAMPLE200_BOUNDED_VERIFIED_REUSE_V1",
        },
        "split": {
            "false_total": len(false_tasks),
            "true_total": len(true_tasks),
            "acquisition_false_count": len(acquisition),
            "fresh_false_count": len(fresh),
            "acquisition_problem_ids": [p.problem_id for p in acquisition],
            "fresh_problem_ids": [p.problem_id for p in fresh],
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
        "acquisition_rows": acquisition_rows,
        "rows": rows,
        "aggregate": aggregate,
        "comparisons": comparisons,
        "true_controls": controls,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "This is an exact bounded replication on the pinned public SAIR normal set after "
            "excluding every equation pair in sample_200. It searches only the complete size-2 "
            "magma universe. Finite countermodels are verifier-backed FALSE evidence; misses are "
            "RESIDUAL only. The replication split and ordering policy were committed before this "
            "run was inspected. It is not an LLM result and does not establish behavior on private "
            "SAIR evaluation tasks or larger finite carriers."
        ),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "provenance": provenance,
        "split": {
            "false_total": len(false_tasks),
            "true_total": len(true_tasks),
            "acquisition_false_count": len(acquisition),
            "fresh_false_count": len(fresh),
        },
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
        default="/tmp/open_math_model_sustained_use_v1/sair-normal-replication",
    )
    args = parser.parse_args()
    report = run(args.out_dir)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
