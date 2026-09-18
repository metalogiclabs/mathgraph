#!/usr/bin/env python3
"""OpenRouter V4: model-acquired verified reuse on pinned public SAIR sample_200.

This moves the V3 protocol onto the actual public SAIR Stage 2 development
distribution.

Frozen design:
- pin SAIR repository commit 817a4653...;
- use the 100 FALSE problems in official sample_200 order;
- first 25 FALSE problems are model-acquisition tasks;
- remaining 75 FALSE problems are untouched fresh tasks;
- the public answer field is used only to select the FALSE subset and is never
  included in any model prompt;
- Gemma proposes size-2/3 finite countermodels, MathGraph independently verifies
  them, and only verified proposals are promoted;
- serialize/reload the bank before fresh evaluation;
- capture one paired cold OpenRouter response per fresh task;
- warm/restart/ablation use the same frozen cold response only as fallback.

A failed finite search remains RESIDUAL and is never promoted to TRUE.
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
    "_sair_openrouter_v4_v3",
    REPO_ROOT / "scripts" / "run_openrouter_model_acquired_verified_reuse_v3.py",
)
_SAIR = _load(
    "_sair_openrouter_v4_sample",
    REPO_ROOT / "scripts" / "run_sair_official_sample200_reuse_probe.py",
)

ACQUISITION_FALSE_COUNT = 25


def _task_dict(problem: Any) -> dict[str, Any]:
    return {
        "task_id": problem.problem_id,
        "eq1_id": problem.eq1_id,
        "eq2_id": problem.eq2_id,
        "source": problem.source,
        "target": problem.target,
        "sample_index": problem.sample_index,
    }


def _evaluate_without_sham(
    bank: list[Any],
    restarted: list[Any],
    cold_rows: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    rows = {
        "cold": _V3._evaluate("cold", (), cold_rows),
        "warm": _V3._evaluate("warm", bank, cold_rows),
        "restart": _V3._evaluate("restart", restarted, cold_rows),
        "ablation": _V3._evaluate("ablation", bank, cold_rows, ablate=True),
    }
    return rows, {name: _V3._aggregate(items) for name, items in rows.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default=_V3.MODEL)
    parser.add_argument("--provider", default=_V3.PROVIDER)
    parser.add_argument("--acquisition-rounds", type=int, default=2)
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    problems, provenance = _SAIR._load_official_sample()
    false_tasks = [p for p in problems if not p.answer]
    true_tasks = [p for p in problems if p.answer]
    if len(false_tasks) != 100 or len(true_tasks) != 100:
        raise RuntimeError(
            f"expected official sample_200 to contain 100 FALSE/100 TRUE, got "
            f"{len(false_tasks)}/{len(true_tasks)}"
        )

    acquisition_tasks = false_tasks[:ACQUISITION_FALSE_COUNT]
    fresh_tasks = false_tasks[ACQUISITION_FALSE_COUNT:]

    promoted: dict[str, Any] = {}
    acquisition_attempts: list[dict[str, Any]] = []
    acquisition_outcomes: list[dict[str, Any]] = []

    for problem in acquisition_tasks:
        cap, attempts = _V3._acquire_task(
            api_key,
            problem.problem_id,
            problem.source,
            problem.target,
            args.model,
            args.provider,
            args.acquisition_rounds,
        )
        acquisition_attempts.extend(attempts)
        if cap is not None:
            promoted.setdefault(cap.capability_id, cap)
        acquisition_outcomes.append(
            {
                "task_id": problem.problem_id,
                "eq1_id": problem.eq1_id,
                "eq2_id": problem.eq2_id,
                "verified_capability_acquired": cap is not None,
                "capability_id": cap.capability_id if cap else None,
                "attempt_count": len(attempts),
            }
        )

    bank = list(promoted.values())
    restarted = _V3._restart(bank, out / "model_acquired_verified_bank.json")

    cold_rows = [
        _V3._fresh_cold(
            api_key,
            p.problem_id,
            p.source,
            p.target,
            args.model,
            args.provider,
        )
        for p in fresh_tasks
    ]

    rows, aggregate = _evaluate_without_sham(bank, restarted, cold_rows)
    acquisition = _V3._acquisition_cost(acquisition_attempts)

    cold = aggregate["cold"]
    warm = aggregate["warm"]
    restart = aggregate["restart"]
    ablation = aggregate["ablation"]

    full_cold_calls = acquisition["model_calls"] + cold["model_calls"]
    full_dev_calls = acquisition["model_calls"] + warm["model_calls"]
    full_cold_tokens = acquisition["total_tokens"] + cold["total_tokens"]
    full_dev_tokens = acquisition["total_tokens"] + warm["total_tokens"]
    full_cold_cost = acquisition["openrouter_cost"] + cold["openrouter_cost"]
    full_dev_cost = acquisition["openrouter_cost"] + warm["openrouter_cost"]
    full_cold_latency = acquisition["latency_ms"] + cold["model_latency_ms"]
    full_dev_latency = acquisition["latency_ms"] + warm["model_latency_ms"]

    comparisons = {
        "fresh_model_call_reduction": 1.0 - warm["model_calls"] / cold["model_calls"] if cold["model_calls"] else None,
        "fresh_token_reduction": 1.0 - warm["total_tokens"] / cold["total_tokens"] if cold["total_tokens"] else None,
        "fresh_cost_reduction": 1.0 - warm["openrouter_cost"] / cold["openrouter_cost"] if cold["openrouter_cost"] else None,
        "fresh_latency_reduction": 1.0 - warm["model_latency_ms"] / cold["model_latency_ms"] if cold["model_latency_ms"] else None,
        "warm_minus_cold_terminal_yield": warm["terminal_yield"] - cold["terminal_yield"],
        "full_sequence_cold_model_calls": full_cold_calls,
        "full_sequence_developmental_model_calls": full_dev_calls,
        "full_sequence_model_call_reduction": 1.0 - full_dev_calls / full_cold_calls if full_cold_calls else None,
        "full_sequence_cold_tokens": full_cold_tokens,
        "full_sequence_developmental_tokens": full_dev_tokens,
        "full_sequence_token_reduction": 1.0 - full_dev_tokens / full_cold_tokens if full_cold_tokens else None,
        "full_sequence_cold_cost": full_cold_cost,
        "full_sequence_developmental_cost": full_dev_cost,
        "full_sequence_cost_reduction": 1.0 - full_dev_cost / full_cold_cost if full_cold_cost else None,
        "full_sequence_cold_model_latency_ms": full_cold_latency,
        "full_sequence_developmental_model_latency_ms": full_dev_latency,
        "full_sequence_model_latency_reduction": 1.0 - full_dev_latency / full_cold_latency if full_cold_latency else None,
        "ablation_minus_warm_model_calls": ablation["model_calls"] - warm["model_calls"],
        "ablation_minus_warm_tokens": ablation["total_tokens"] - warm["total_tokens"],
    }

    restart_match = all(
        restart[k] == warm[k]
        for k in (
            "tasks",
            "verified_terminal_results",
            "terminal_yield",
            "verified_reuse_hits",
            "model_calls",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "model_latency_ms",
            "openrouter_cost",
        )
    )

    gates = {
        "pinned_sair_commit": provenance["commit"] == _SAIR.SAIR_COMMIT,
        "official_sample_200_complete": provenance["sample_problem_count"] == 200,
        "false_true_split_100_100": len(false_tasks) == 100 and len(true_tasks) == 100,
        "acquisition_split_fixed_25": len(acquisition_tasks) == 25,
        "fresh_split_fixed_75": len(fresh_tasks) == 75,
        "answers_not_in_model_prompt": all(
            "answer" not in row["prompt"].lower() for row in acquisition_attempts + cold_rows
        ),
        "at_least_one_model_acquired_capability_verified": bool(bank),
        "all_promoted_capabilities_verifier_backed": all(
            cap.verifier_evidence.get("terminal_candidate_ok") for cap in bank
        ),
        "restart_preserves_ids": [c.capability_id for c in bank] == [c.capability_id for c in restarted],
        "restart_matches_warm_substantive_metrics": restart_match,
        "warm_not_worse_terminal_yield": warm["terminal_yield"] >= cold["terminal_yield"],
        "warm_uses_fewer_fresh_model_calls": warm["model_calls"] < cold["model_calls"],
        "warm_uses_fewer_fresh_tokens": warm["total_tokens"] < cold["total_tokens"],
        "ablation_restores_cold_model_calls": ablation["model_calls"] == cold["model_calls"],
        "ablation_restores_cold_tokens": ablation["total_tokens"] == cold["total_tokens"],
        "ablation_restores_cold_terminal_yield": ablation["terminal_yield"] == cold["terminal_yield"],
    }

    report = {
        "protocol": "MATHGRAPH_OPENROUTER_SAIR_SAMPLE200_MODEL_ACQUIRED_REUSE_V4",
        "model": args.model,
        "provider": args.provider,
        "sair_provenance": provenance,
        "policy": {
            "answer_field_use": "select FALSE subset only; never included in model prompts",
            "acquisition_rule": "first 25 FALSE problems in official sample_200 order",
            "fresh_rule": "remaining 75 FALSE problems in official sample_200 order",
            "acquisition_round_cap": args.acquisition_rounds,
            "candidate_carrier_sizes": [2, 3],
            "promotion": "independent finite checker only",
            "fresh_comparison": "paired frozen cold OpenRouter response; warm/restart/ablation use identical fallback",
        },
        "acquisition_tasks": [_task_dict(p) for p in acquisition_tasks],
        "fresh_tasks": [_task_dict(p) for p in fresh_tasks],
        "acquisition_outcomes": acquisition_outcomes,
        "acquisition_attempts": acquisition_attempts,
        "acquisition_cost": acquisition,
        "promoted_capabilities": [cap.to_dict() for cap in bank],
        "fresh_cold_responses": cold_rows,
        "rows": rows,
        "aggregate": aggregate,
        "comparisons": comparisons,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "This is a bounded external-model experiment on the pinned public SAIR Stage 2 sample_200 "
            "FALSE distribution. Gemma generates acquisition artifacts; only independently verified "
            "size-2/3 finite countermodels are promoted. The 75 fresh FALSE tasks are not used during "
            "acquisition. Paired cold responses are frozen once and used as identical fallback, so "
            "fresh warm/cold comparisons are not confounded by separate model samples. The experiment "
            "does not establish TRUE implications, private-evaluation performance, weight-level learning, "
            "or transfer beyond this public bounded distribution."
        ),
    }

    (out / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "model": report["model"],
                "provider": report["provider"],
                "acquisition_task_count": len(acquisition_tasks),
                "fresh_task_count": len(fresh_tasks),
                "acquisition_verified_count": sum(
                    bool(x["verified_capability_acquired"]) for x in acquisition_outcomes
                ),
                "promoted_capability_count": len(bank),
                "acquisition_cost": acquisition,
                "aggregate": aggregate,
                "comparisons": comparisons,
                "gates": gates,
                "claim_boundary": report["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
