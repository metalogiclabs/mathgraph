#!/usr/bin/env python3
"""Pre-result bounded reuse probe on SAIR Stage 2 official public sample_200.

The policy is fixed before inspecting this run's size-2 reuse result:
- pin one public SAIR repository commit;
- take FALSE problems in official sample_200 order;
- first 25 FALSE problems are acquisition;
- the rest are fresh evaluation;
- search the complete 2-element magma universe (16 tables);
- promote first verified acquisition countermodels;
- rank promoted tables only by acquisition-set support;
- compare cold, warm, restart, fixed-sham, and ablation candidate orderings.

Failure to find a size-2 countermodel is RESIDUAL only, never TRUE.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import urllib.request
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
FINITE_WORLD_PATH = REPO_ROOT / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("_finite_magma_world_sair_probe", FINITE_WORLD_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load finite checker from {FINITE_WORLD_PATH}")
_FINITE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FINITE
_SPEC.loader.exec_module(_FINITE)
check_finite_countermodel = _FINITE.check_finite_countermodel


SAIR_REPO = "SAIRcompetition/equational-theories-lean-stage2"
SAIR_COMMIT = "817a4653bf762584931d49c6714c9fcfab7df66a"
RAW_BASE = f"https://raw.githubusercontent.com/{SAIR_REPO}/{SAIR_COMMIT}"
SAMPLE_PATH = "examples/problems/sample_200.json"
LABEL_PATHS = (
    "examples/problems/normal.jsonl",
    "examples/problems/hard1.jsonl",
    "examples/problems/hard2.jsonl",
    "examples/problems/hard3.jsonl",
)
ACQUISITION_FALSE_COUNT = 25


@dataclass(frozen=True)
class Problem:
    problem_id: str
    eq1_id: int
    eq2_id: int
    source: str
    target: str
    answer: bool
    difficulty: str
    sample_index: int


@dataclass(frozen=True)
class Capability:
    table_index: int
    table: tuple[tuple[int, ...], ...]
    capability_id: str
    acquisition_support: int
    origin_problem_ids: tuple[str, ...]


def _fetch_text(path: str) -> tuple[str, dict[str, Any]]:
    url = f"{RAW_BASE}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "MathGraph-SAIR-reuse-probe/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw.decode("utf-8"), {
        "path": path,
        "url": url,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def _load_official_sample() -> tuple[list[Problem], dict[str, Any]]:
    sample_text, sample_meta = _fetch_text(SAMPLE_PATH)
    sample = json.loads(sample_text)
    labels: dict[str, dict[str, Any]] = {}
    label_meta = []
    for path in LABEL_PATHS:
        text, meta = _fetch_text(path)
        label_meta.append(meta)
        for line in text.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            labels[str(row["id"])] = row

    problems: list[Problem] = []
    missing: list[str] = []
    for i, row in enumerate(sample):
        pid = str(row["id"])
        label = labels.get(pid)
        if label is None:
            missing.append(pid)
            continue
        problems.append(
            Problem(
                problem_id=pid,
                eq1_id=int(row["eq1_id"]),
                eq2_id=int(row["eq2_id"]),
                source=str(row["equation1"]).replace("◇", "*"),
                target=str(row["equation2"]).replace("◇", "*"),
                answer=bool(label["answer"]),
                difficulty=str(label.get("difficulty") or pid.split("_", 1)[0]),
                sample_index=i,
            )
        )
    if missing:
        raise RuntimeError(f"missing labels for {len(missing)} sample problems: {missing[:10]}")
    if len(problems) != len(sample):
        raise RuntimeError("sample/label join was incomplete")
    return problems, {
        "repository": SAIR_REPO,
        "commit": SAIR_COMMIT,
        "sample": sample_meta,
        "labels": label_meta,
        "sample_problem_count": len(problems),
    }


def _all_size2_tables() -> list[tuple[tuple[int, ...], ...]]:
    return [
        ((a, b), (c, d))
        for a, b, c, d in product(range(2), repeat=4)
    ]


TABLES = _all_size2_tables()


def _capability_id(table_index: int, table: Sequence[Sequence[int]]) -> str:
    payload = json.dumps([list(row) for row in table], separators=(",", ":"))
    return "sair2_" + hashlib.sha256(
        f"{table_index}:{payload}".encode("utf-8")
    ).hexdigest()[:16]


def _solves(problem: Problem, table: Sequence[Sequence[int]]) -> bool:
    return bool(check_finite_countermodel(problem.source, problem.target, table).terminal_candidate_ok)


def _evaluate_order(problem: Problem, ordering: Sequence[int]) -> dict[str, Any]:
    for calls, table_index in enumerate(ordering, start=1):
        checked = check_finite_countermodel(problem.source, problem.target, TABLES[table_index])
        if checked.terminal_candidate_ok:
            return {
                "problem_id": problem.problem_id,
                "sample_index": problem.sample_index,
                "answer": problem.answer,
                "status": "FINITE_COUNTERMODEL",
                "verifier_calls": calls,
                "table_index": table_index,
                "capability_id": _capability_id(table_index, TABLES[table_index]),
                "witness_env": dict(checked.witness_env),
            }
    return {
        "problem_id": problem.problem_id,
        "sample_index": problem.sample_index,
        "answer": problem.answer,
        "status": "RESIDUAL",
        "verifier_calls": len(ordering),
        "table_index": None,
        "capability_id": None,
        "witness_env": {},
    }


def _acquire(acquisition: Sequence[Problem]) -> tuple[list[Capability], list[dict[str, Any]]]:
    cold_order = tuple(range(len(TABLES)))
    rows = [_evaluate_order(problem, cold_order) for problem in acquisition]
    origins: dict[int, list[str]] = {}
    for row in rows:
        if row["status"] == "FINITE_COUNTERMODEL":
            origins.setdefault(int(row["table_index"]), []).append(str(row["problem_id"]))

    capabilities: list[Capability] = []
    for table_index, problem_ids in origins.items():
        support = sum(_solves(problem, TABLES[table_index]) for problem in acquisition)
        capabilities.append(
            Capability(
                table_index=table_index,
                table=TABLES[table_index],
                capability_id=_capability_id(table_index, TABLES[table_index]),
                acquisition_support=int(support),
                origin_problem_ids=tuple(problem_ids),
            )
        )
    capabilities.sort(key=lambda cap: (-cap.acquisition_support, cap.table_index))
    return capabilities, rows


def _warm_order(capabilities: Sequence[Capability]) -> list[int]:
    promoted = [cap.table_index for cap in capabilities]
    promoted_set = set(promoted)
    return promoted + [i for i in range(len(TABLES)) if i not in promoted_set]


def _sham_order(front_size: int) -> list[int]:
    fixed = []
    lo, hi = 0, len(TABLES) - 1
    while lo <= hi:
        fixed.append(hi)
        hi -= 1
        if lo <= hi:
            fixed.append(lo)
            lo += 1
    front = fixed[:front_size]
    front_set = set(front)
    return front + [i for i in range(len(TABLES)) if i not in front_set]


def _ablation_order(capabilities: Sequence[Capability]) -> list[int]:
    promoted = [cap.table_index for cap in capabilities]
    promoted_set = set(promoted)
    return [i for i in range(len(TABLES)) if i not in promoted_set] + promoted


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    solved = sum(row["status"] == "FINITE_COUNTERMODEL" for row in rows)
    calls = sum(int(row["verifier_calls"]) for row in rows)
    return {
        "tasks": len(rows),
        "finite_countermodels": int(solved),
        "residuals": int(len(rows) - solved),
        "terminal_yield": solved / len(rows) if rows else 0.0,
        "total_verifier_calls": calls,
        "mean_verifier_calls": calls / len(rows) if rows else 0.0,
    }


def _serialize_bank(capabilities: Sequence[Capability], path: Path) -> None:
    payload = [
        {
            **asdict(cap),
            "table": [list(row) for row in cap.table],
        }
        for cap in capabilities
    ]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reload_bank(path: Path) -> list[Capability]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        Capability(
            table_index=int(row["table_index"]),
            table=tuple(tuple(int(x) for x in r) for r in row["table"]),
            capability_id=str(row["capability_id"]),
            acquisition_support=int(row["acquisition_support"]),
            origin_problem_ids=tuple(str(x) for x in row["origin_problem_ids"]),
        )
        for row in rows
    ]


def _true_controls(true_tasks: Sequence[Problem]) -> dict[str, Any]:
    contradictions = []
    for problem in true_tasks:
        row = _evaluate_order(problem, tuple(range(len(TABLES))))
        if row["status"] == "FINITE_COUNTERMODEL":
            contradictions.append(row)
    return {
        "true_task_count": len(true_tasks),
        "size2_tables_checked_per_task": len(TABLES),
        "countermodels_found": len(contradictions),
        "contradictions": contradictions,
        "passes": len(contradictions) == 0,
        "note": "No countermodel in this bounded universe is not a proof of TRUE.",
    }


def _markdown(report: dict[str, Any]) -> str:
    a = report["aggregate"]
    c = report["comparisons"]
    lines = [
        "# SAIR Stage 2 Official Sample-200 — Bounded Verified Reuse Probe",
        "",
        f"- verdict: {report['verdict']}",
        f"- official commit: {report['provenance']['commit']}",
        f"- sample problems: {report['provenance']['sample_problem_count']}",
        f"- FALSE acquisition tasks: {report['split']['acquisition_false_count']}",
        f"- FALSE fresh tasks: {report['split']['fresh_false_count']}",
        f"- promoted size-2 capabilities: {len(report['capabilities'])}",
        "",
        "## Fresh-set search cost",
        "",
        f"- cold verifier calls: {a['cold']['total_verifier_calls']}",
        f"- warm verifier calls: {a['warm']['total_verifier_calls']}",
        f"- restart verifier calls: {a['restart']['total_verifier_calls']}",
        f"- sham verifier calls: {a['sham']['total_verifier_calls']}",
        f"- ablation verifier calls: {a['ablation']['total_verifier_calls']}",
        f"- warm reduction vs cold: {c['warm_call_reduction_vs_cold']:.2%}",
        f"- warm compression vs cold: {c['cold_over_warm_calls']:.3f}x",
        "",
        "## Full acquisition + fresh sequence",
        "",
        f"- cold baseline calls: {c['full_sequence_cold_calls']}",
        f"- developmental calls: {c['full_sequence_developmental_calls']}",
        f"- full-sequence reduction: {c['full_sequence_call_reduction']:.2%}",
        "",
        "## Controls",
        "",
        f"- TRUE-label size-2 contradictions: {report['true_controls']['countermodels_found']}",
        f"- restart exact: {report['gates']['restart_exact']}",
        f"- terminal yield preserved: {report['gates']['all_orderings_preserve_bounded_terminal_yield']}",
        "",
        "## Claim boundary",
        "",
        report["claim_boundary"],
    ]
    return "\n".join(lines) + "\n"


def run(out_dir: str | Path) -> dict[str, Any]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    problems, provenance = _load_official_sample()

    false_tasks = [p for p in problems if not p.answer]
    true_tasks = [p for p in problems if p.answer]
    if len(false_tasks) <= ACQUISITION_FALSE_COUNT:
        raise RuntimeError(
            f"need >{ACQUISITION_FALSE_COUNT} FALSE tasks, found {len(false_tasks)}"
        )

    acquisition = false_tasks[:ACQUISITION_FALSE_COUNT]
    fresh = false_tasks[ACQUISITION_FALSE_COUNT:]

    capabilities, acquisition_rows = _acquire(acquisition)
    bank_path = output / "verified_size2_capability_bank.json"
    _serialize_bank(capabilities, bank_path)
    restarted = _reload_bank(bank_path)

    cold_order = list(range(len(TABLES)))
    warm_order = _warm_order(capabilities)
    restart_order = _warm_order(restarted)
    sham_order = _sham_order(len(capabilities))
    ablation_order = _ablation_order(capabilities)

    rows = {
        "cold": [_evaluate_order(p, cold_order) for p in fresh],
        "warm": [_evaluate_order(p, warm_order) for p in fresh],
        "restart": [_evaluate_order(p, restart_order) for p in fresh],
        "sham": [_evaluate_order(p, sham_order) for p in fresh],
        "ablation": [_evaluate_order(p, ablation_order) for p in fresh],
    }
    aggregate = {name: _aggregate(items) for name, items in rows.items()}
    controls = _true_controls(true_tasks)

    cold_calls = aggregate["cold"]["total_verifier_calls"]
    warm_calls = aggregate["warm"]["total_verifier_calls"]
    acquisition_calls = sum(int(row["verifier_calls"]) for row in acquisition_rows)
    full_cold = acquisition_calls + cold_calls
    full_developmental = acquisition_calls + warm_calls

    comparisons = {
        "cold_over_warm_calls": cold_calls / warm_calls if warm_calls else None,
        "warm_call_reduction_vs_cold": 1.0 - warm_calls / cold_calls if cold_calls else None,
        "restart_matches_warm_calls": aggregate["restart"]["total_verifier_calls"] == warm_calls,
        "sham_minus_warm_calls": aggregate["sham"]["total_verifier_calls"] - warm_calls,
        "ablation_minus_warm_calls": aggregate["ablation"]["total_verifier_calls"] - warm_calls,
        "acquisition_verifier_calls": acquisition_calls,
        "full_sequence_cold_calls": full_cold,
        "full_sequence_developmental_calls": full_developmental,
        "full_sequence_call_reduction": 1.0 - full_developmental / full_cold if full_cold else None,
    }

    bounded_yields = {name: data["terminal_yield"] for name, data in aggregate.items()}
    gates = {
        "official_sample_join_complete": provenance["sample_problem_count"] == 200,
        "acquisition_split_fixed_at_25_false": len(acquisition) == ACQUISITION_FALSE_COUNT,
        "fresh_false_nonempty": bool(fresh),
        "verified_capability_bank_nonempty": bool(capabilities),
        "restart_exact": [cap.capability_id for cap in capabilities]
        == [cap.capability_id for cap in restarted]
        and restart_order == warm_order,
        "all_orderings_preserve_bounded_terminal_yield": len(set(bounded_yields.values())) == 1,
        "true_label_control_has_no_size2_countermodel": controls["passes"],
        "no_failed_search_promoted_to_true": True,
    }

    report: dict[str, Any] = {
        "protocol": "SAIR_OFFICIAL_SAMPLE200_BOUNDED_VERIFIED_REUSE_V1",
        "provenance": provenance,
        "policy": {
            "finite_universe": "all 16 binary operation tables on carrier {0,1}",
            "acquisition_rule": "first 25 FALSE tasks in official sample_200 order",
            "promotion_rule": "first independently verified size-2 countermodel per acquisition task; deduplicate exact tables",
            "warm_order_rule": "promoted tables by descending acquisition support then lexicographic table index; remaining tables lexicographic",
            "sham_order_rule": "fixed alternating high/low table indices, independent of acquisition evidence",
            "ablation_order_rule": "non-promoted tables lexicographic, promoted tables moved to the end",
            "fresh_rule": "remaining FALSE tasks in official sample_200 order",
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
                **asdict(cap),
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
            "This is a bounded exact search-order/reuse result on SAIR Stage 2 public official "
            "sample_200 at pinned commit 817a4653. It searches only the complete 2-element magma "
            "universe. Verified finite countermodels are terminal FALSE evidence; absence of a "
            "size-2 countermodel remains RESIDUAL and is never treated as TRUE. The split and "
            "ordering policy were fixed in this branch before observing this run's sample_200 "
            "reuse metrics. This is not an LLM result and not a claim about all SAIR problems."
        ),
    }

    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "split": report["split"],
                "capability_count": len(capabilities),
                "aggregate": aggregate,
                "comparisons": comparisons,
                "true_controls": controls,
                "gates": gates,
                "claim_boundary": report["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="/tmp/open_math_model_sustained_use_v1/sair-official-sample200",
    )
    args = parser.parse_args()
    report = run(args.out_dir)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
