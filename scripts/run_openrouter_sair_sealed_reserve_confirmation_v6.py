#!/usr/bin/env python3
"""OpenRouter V6: sealed 250-problem reserve confirmation using frozen V5 bank.

No capability acquisition occurs in V6. The exact semantic bank frozen after V5
is loaded from the repository, reverified against its original acquisition
tasks, serialized/restarted, and then applied to the final 250 FALSE rows that
V5 explicitly withheld.

One cold OpenRouter response is captured for each reserve task. Warm/restart and
targeted ablation use that exact response only as fallback.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_V3 = _load(
    "_sair_v6_v3",
    REPO_ROOT / "scripts" / "run_openrouter_model_acquired_verified_reuse_v3.py",
)
_NORMAL = _load(
    "_sair_v6_normal",
    REPO_ROOT / "scripts" / "run_sair_normal_reuse_replication_v1.py",
)

BANK_PATH = REPO_ROOT / "experiments" / "openrouter_sair_v5" / "frozen_model_acquired_verified_bank.json"
MANIFEST_PATH = REPO_ROOT / "experiments" / "openrouter_sair_v5" / "frozen_bank_manifest.json"


def _load_bank() -> list[Any]:
    rows = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    return [
        _V3.Capability(
            capability_id=row["capability_id"],
            table=_V3.normalize_table(row["table"]),
            source_task_id=row["source_task_id"],
            verifier_evidence=dict(row["verifier_evidence"]),
        )
        for row in rows
    ]


def _reverify_frozen_bank(bank: list[Any], acquisition_tasks: list[Any]) -> list[dict[str, Any]]:
    by_id = {p.problem_id: p for p in acquisition_tasks}
    evidence = []
    for cap in bank:
        problem = by_id.get(cap.source_task_id)
        if problem is None:
            raise RuntimeError(f"frozen capability source not in V5 acquisition split: {cap.source_task_id}")
        checked = _V3.check_finite_countermodel(problem.source, problem.target, cap.table).to_dict()
        evidence.append({
            "capability_id": cap.capability_id,
            "source_task_id": cap.source_task_id,
            "terminal_candidate_ok": checked["terminal_candidate_ok"],
            "verification": checked,
        })
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default=_V3.MODEL)
    parser.add_argument("--provider", default=_V3.PROVIDER)
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    frozen_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    problems, provenance = _NORMAL._load()
    false_tasks = [p for p in problems if not p.answer]
    true_tasks = [p for p in problems if p.answer]
    if len(false_tasks) != 500 or len(true_tasks) != 500:
        raise RuntimeError("disjoint normal set size changed")

    acquisition_tasks = false_tasks[:50]
    prior_fresh_tasks = false_tasks[50:250]
    reserve_tasks = false_tasks[250:]
    if len(reserve_tasks) != 250:
        raise RuntimeError("reserve split changed")

    bank = _load_bank()
    bank_reverification = _reverify_frozen_bank(bank, acquisition_tasks)
    if not all(row["terminal_candidate_ok"] for row in bank_reverification):
        raise RuntimeError("frozen bank failed independent reverification")

    restarted = _V3._restart(bank, out / "restarted_frozen_bank.json")

    cold_rows = [
        _V3._fresh_cold(
            api_key,
            p.problem_id,
            p.source,
            p.target,
            args.model,
            args.provider,
        )
        for p in reserve_tasks
    ]

    rows = {
        "cold": _V3._evaluate("cold", (), cold_rows),
        "warm": _V3._evaluate("warm", bank, cold_rows),
        "restart": _V3._evaluate("restart", restarted, cold_rows),
        "ablation": _V3._evaluate("ablation", bank, cold_rows, ablate=True),
    }
    aggregate = {name: _V3._aggregate(items) for name, items in rows.items()}
    cold, warm = aggregate["cold"], aggregate["warm"]
    restart, ablation = aggregate["restart"], aggregate["ablation"]

    reserve_comparisons = {
        "model_call_reduction": 1.0 - warm["model_calls"] / cold["model_calls"] if cold["model_calls"] else None,
        "token_reduction": 1.0 - warm["total_tokens"] / cold["total_tokens"] if cold["total_tokens"] else None,
        "cost_reduction": 1.0 - warm["openrouter_cost"] / cold["openrouter_cost"] if cold["openrouter_cost"] else None,
        "latency_reduction": 1.0 - warm["model_latency_ms"] / cold["model_latency_ms"] if cold["model_latency_ms"] else None,
        "warm_minus_cold_terminal_yield": warm["terminal_yield"] - cold["terminal_yield"],
        "ablation_minus_warm_model_calls": ablation["model_calls"] - warm["model_calls"],
        "ablation_minus_warm_tokens": ablation["total_tokens"] - warm["total_tokens"],
    }

    acq = frozen_manifest["acquisition_cost"]
    v5_cold = frozen_manifest["v5_fresh_cold"]
    v5_warm = frozen_manifest["v5_fresh_warm"]

    cumulative_cold = {
        "model_calls": acq["model_calls"] + v5_cold["model_calls"] + cold["model_calls"],
        "total_tokens": acq["total_tokens"] + v5_cold["total_tokens"] + cold["total_tokens"],
        "openrouter_cost": acq["openrouter_cost"] + v5_cold["openrouter_cost"] + cold["openrouter_cost"],
        "model_latency_ms": acq["latency_ms"] + v5_cold["model_latency_ms"] + cold["model_latency_ms"],
    }
    cumulative_dev = {
        "model_calls": acq["model_calls"] + v5_warm["model_calls"] + warm["model_calls"],
        "total_tokens": acq["total_tokens"] + v5_warm["total_tokens"] + warm["total_tokens"],
        "openrouter_cost": acq["openrouter_cost"] + v5_warm["openrouter_cost"] + warm["openrouter_cost"],
        "model_latency_ms": acq["latency_ms"] + v5_warm["model_latency_ms"] + warm["model_latency_ms"],
    }
    cumulative = {
        "cold": cumulative_cold,
        "developmental": cumulative_dev,
        "model_call_reduction": 1.0 - cumulative_dev["model_calls"] / cumulative_cold["model_calls"],
        "token_reduction": 1.0 - cumulative_dev["total_tokens"] / cumulative_cold["total_tokens"],
        "cost_reduction": 1.0 - cumulative_dev["openrouter_cost"] / cumulative_cold["openrouter_cost"],
        "latency_reduction": 1.0 - cumulative_dev["model_latency_ms"] / cumulative_cold["model_latency_ms"],
    }

    restart_match = all(
        restart[k] == warm[k]
        for k in (
            "tasks", "verified_terminal_results", "terminal_yield",
            "verified_reuse_hits", "model_calls", "input_tokens", "output_tokens",
            "total_tokens", "model_latency_ms", "openrouter_cost",
        )
    )

    acquisition_ids = {p.problem_id for p in acquisition_tasks}
    prior_fresh_ids = {p.problem_id for p in prior_fresh_tasks}
    reserve_ids = {p.problem_id for p in reserve_tasks}
    bank_source_ids = {cap.source_task_id for cap in bank}

    gates = {
        "pinned_sair_commit": provenance["commit"] == frozen_manifest["sair_commit"],
        "sample200_pairs_excluded": provenance["excluded_pair_count"] == 200,
        "frozen_bank_source_run": frozen_manifest["source_run_id"] == 35402563917,
        "frozen_bank_size_3": len(bank) == 3,
        "bank_sources_only_from_v5_acquisition": bank_source_ids <= acquisition_ids,
        "bank_sources_disjoint_from_prior_fresh": bank_source_ids.isdisjoint(prior_fresh_ids),
        "bank_sources_disjoint_from_reserve": bank_source_ids.isdisjoint(reserve_ids),
        "reserve_split_exact_250": len(reserve_tasks) == 250,
        "reserve_was_v5_declared_untouched": frozen_manifest["untouched_reserve_false_count"] == 250,
        "frozen_bank_reverifies": all(row["terminal_candidate_ok"] for row in bank_reverification),
        "restart_preserves_ids": [c.capability_id for c in bank] == [c.capability_id for c in restarted],
        "restart_matches_warm_substantive_metrics": restart_match,
        "warm_not_worse_terminal_yield": warm["terminal_yield"] >= cold["terminal_yield"],
        "warm_uses_fewer_model_calls": warm["model_calls"] < cold["model_calls"],
        "warm_uses_fewer_tokens": warm["total_tokens"] < cold["total_tokens"],
        "ablation_restores_cold_model_calls": ablation["model_calls"] == cold["model_calls"],
        "ablation_restores_cold_tokens": ablation["total_tokens"] == cold["total_tokens"],
        "ablation_restores_cold_terminal_yield": ablation["terminal_yield"] == cold["terminal_yield"],
    }

    report = {
        "protocol": "MATHGRAPH_OPENROUTER_SAIR_SEALED_RESERVE_CONFIRMATION_V6",
        "model": args.model,
        "provider": args.provider,
        "provenance": provenance,
        "frozen_bank_manifest": frozen_manifest,
        "bank_reverification": bank_reverification,
        "reserve_manifest": [
            {
                "task_id": p.problem_id,
                "eq1_id": p.eq1_id,
                "eq2_id": p.eq2_id,
                "normal_index": p.sample_index,
            }
            for p in reserve_tasks
        ],
        "fresh_cold_responses": cold_rows,
        "rows": rows,
        "aggregate": aggregate,
        "reserve_comparisons": reserve_comparisons,
        "cumulative_500_false_stream": cumulative,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "V6 is a sealed-reserve confirmation. It performs no capability acquisition and uses "
            "the three-capability bank frozen from V5 before these final 250 FALSE normal problems "
            "were evaluated. Every bank artifact is independently reverified against its original "
            "acquisition problem before use. Cold OpenRouter responses are captured once and used "
            "as identical fallback. This remains public-development-data evidence, not private SAIR "
            "evaluation or weight-level learning."
        ),
    }

    (out / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "verdict": report["verdict"],
        "model": report["model"],
        "provider": report["provider"],
        "reserve_task_count": len(reserve_tasks),
        "frozen_bank_size": len(bank),
        "aggregate": aggregate,
        "reserve_comparisons": reserve_comparisons,
        "cumulative_500_false_stream": cumulative,
        "gates": gates,
        "claim_boundary": report["claim_boundary"],
    }, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
