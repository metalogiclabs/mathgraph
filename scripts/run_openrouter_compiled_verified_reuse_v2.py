#!/usr/bin/env python3
"""Compiled verified-reuse evaluation around one frozen OpenRouter cold transcript.

This is a paired system comparison. OpenRouter is called only for the cold
baseline. Every other condition reuses the exact same frozen model responses as
its fallback, eliminating cross-condition model sampling noise.

A verified capability controller checks the authorized bank *before* paying for
a model call. If a stored artifact independently satisfies the fresh task, the
controller returns that artifact directly and the model-call cost for that task
is zero. If not, the system falls through to the frozen cold response and is
charged the exact provider-reported tokens/latency from that response.

Conditions:
- COLD: model response for every task.
- WARM: authorized verified bank, then cold fallback.
- RESTART: serialized/reloaded authorized bank, then cold fallback.
- SHAM: same bank shape/IDs with corrupted payloads, independently rechecked,
  then cold fallback.
- ABLATION: remove every authorized capability that solves the current task,
  then cold fallback.

This isolates the causal value of compiled verified reuse from LLM randomness.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
FINITE_PATH = REPO_ROOT / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("_finite_compiled_reuse_v2", FINITE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load finite checker from {FINITE_PATH}")
_FINITE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FINITE
_SPEC.loader.exec_module(_FINITE)
check_finite_countermodel = _FINITE.check_finite_countermodel
normalize_table = _FINITE.normalize_table


@dataclass(frozen=True)
class Capability:
    capability_id: str
    table: tuple[tuple[int, ...], ...]
    verifier_evidence: dict[str, Any]


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"non-object row in {path}")
            rows.append(obj)
    return rows


def _load_bank(path: Path) -> list[Capability]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        Capability(
            capability_id=str(row["capability_id"]),
            table=normalize_table(row["table"]),
            verifier_evidence=dict(row.get("verifier_evidence") or {}),
        )
        for row in rows
    ]


def _restart(bank: Sequence[Capability], path: Path) -> list[Capability]:
    path.write_text(
        json.dumps(
            [
                {
                    "capability_id": cap.capability_id,
                    "table": [list(row) for row in cap.table],
                    "verifier_evidence": cap.verifier_evidence,
                }
                for cap in bank
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return _load_bank(path)


def _sham(bank: Sequence[Capability]) -> list[Capability]:
    left_projection = ((0, 0), (1, 1))
    constant_zero = ((0, 0), (0, 0))
    out = []
    for i, cap in enumerate(bank):
        fake = constant_zero if i % 2 == 0 else left_projection
        out.append(
            Capability(
                capability_id=cap.capability_id,
                table=fake,
                verifier_evidence={
                    "control": "SHAM_PAYLOAD",
                    "authorized": False,
                },
            )
        )
    return out


def _task_from_request(row: dict[str, Any]) -> tuple[str, str, str]:
    task = row["task"]
    return str(row["task_id"]), str(task["source"]), str(task["target"])


def _verify(source: str, target: str, table: Sequence[Sequence[int]]) -> dict[str, Any]:
    return check_finite_countermodel(source, target, table).to_dict()


def _resolve_model_candidate(
    response: dict[str, Any],
    source: str,
    target: str,
) -> tuple[bool, dict[str, Any], tuple[tuple[int, ...], ...] | None]:
    candidate = response.get("candidate") or {}
    table = candidate.get("table") if isinstance(candidate, dict) else None
    if table is None:
        return False, {
            "terminal_candidate_ok": False,
            "diagnostic": "cold model response did not contain a concrete table",
        }, None
    try:
        normalized = normalize_table(table)
    except Exception as exc:
        return False, {
            "terminal_candidate_ok": False,
            "diagnostic": f"invalid model table: {exc}",
        }, None
    checked = _verify(source, target, normalized)
    return bool(checked["terminal_candidate_ok"]), checked, normalized


def _supporting(
    bank: Sequence[Capability],
    source: str,
    target: str,
) -> list[tuple[Capability, dict[str, Any], int]]:
    out = []
    for index, cap in enumerate(bank, start=1):
        checked = _verify(source, target, cap.table)
        if checked["terminal_candidate_ok"]:
            out.append((cap, checked, index))
    return out


def _usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "latency_ms": float(response.get("latency_ms") or 0.0),
        "openrouter_cost": float(
            ((response.get("openrouter_usage") or {}).get("cost")) or 0.0
        ),
    }


def _evaluate_condition(
    *,
    name: str,
    tasks: Sequence[dict[str, Any]],
    responses: dict[str, dict[str, Any]],
    bank: Sequence[Capability] | None,
    ablate_support: bool = False,
) -> list[dict[str, Any]]:
    rows = []
    for request in tasks:
        task_id, source, target = _task_from_request(request)
        response = responses[task_id]
        local_bank = list(bank or ())
        if ablate_support:
            supporting_ids = {
                cap.capability_id
                for cap, _checked, _index in _supporting(local_bank, source, target)
            }
            local_bank = [
                cap for cap in local_bank if cap.capability_id not in supporting_ids
            ]

        started = time.perf_counter()
        supports = _supporting(local_bank, source, target)
        controller_ms = (time.perf_counter() - started) * 1000.0

        if supports:
            cap, checked, verifier_calls = supports[0]
            rows.append(
                {
                    "task_id": task_id,
                    "condition": name,
                    "terminal_verified": True,
                    "route": "VERIFIED_REUSE",
                    "capability_id": cap.capability_id,
                    "controller_verifier_calls": verifier_calls,
                    "model_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "model_latency_ms": 0.0,
                    "controller_latency_ms": controller_ms,
                    "openrouter_cost": 0.0,
                    "verification": checked,
                }
            )
            continue

        ok, checked, _table = _resolve_model_candidate(response, source, target)
        u = _usage(response)
        rows.append(
            {
                "task_id": task_id,
                "condition": name,
                "terminal_verified": ok,
                "route": "OPENROUTER_FALLBACK",
                "capability_id": None,
                "controller_verifier_calls": len(local_bank),
                "model_calls": 1,
                **u,
                "model_latency_ms": u.pop("latency_ms"),
                "controller_latency_ms": controller_ms,
                "verification": checked,
            }
        )
    return rows


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    verified = sum(bool(row["terminal_verified"]) for row in rows)
    return {
        "tasks": n,
        "verified_terminal_results": verified,
        "terminal_yield": verified / n if n else 0.0,
        "verified_reuse_hits": sum(row["route"] == "VERIFIED_REUSE" for row in rows),
        "model_calls": sum(int(row["model_calls"]) for row in rows),
        "input_tokens": sum(int(row["input_tokens"]) for row in rows),
        "output_tokens": sum(int(row["output_tokens"]) for row in rows),
        "total_tokens": sum(int(row["total_tokens"]) for row in rows),
        "model_latency_ms": sum(float(row["model_latency_ms"]) for row in rows),
        "controller_latency_ms": sum(float(row["controller_latency_ms"]) for row in rows),
        "controller_verifier_calls": sum(int(row["controller_verifier_calls"]) for row in rows),
        "openrouter_cost": sum(float(row["openrouter_cost"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--capability-bank", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    requests = [
        row
        for row in _jsonl(Path(args.requests))
        if str(row.get("mode")) == "cold"
    ]
    if len(requests) != 7:
        raise RuntimeError(f"expected 7 cold requests, got {len(requests)}")

    response_rows = _jsonl(Path(args.responses))
    responses = {
        str(row["task_id"]): row
        for row in response_rows
        if str(row.get("mode")) == "cold"
    }
    if set(responses) != {str(row["task_id"]) for row in requests}:
        raise RuntimeError("cold response/task mismatch")

    bank = _load_bank(Path(args.capability_bank))
    if not bank:
        raise RuntimeError("empty capability bank")
    if not all(cap.verifier_evidence.get("terminal_candidate_ok") for cap in bank):
        raise RuntimeError("bank contains capability without verifier-backed promotion evidence")

    restarted = _restart(bank, out / "restarted_bank.json")
    sham = _sham(bank)

    rows = {
        "cold": _evaluate_condition(
            name="cold",
            tasks=requests,
            responses=responses,
            bank=(),
        ),
        "warm": _evaluate_condition(
            name="warm",
            tasks=requests,
            responses=responses,
            bank=bank,
        ),
        "restart": _evaluate_condition(
            name="restart",
            tasks=requests,
            responses=responses,
            bank=restarted,
        ),
        "sham": _evaluate_condition(
            name="sham",
            tasks=requests,
            responses=responses,
            bank=sham,
        ),
        "ablation": _evaluate_condition(
            name="ablation",
            tasks=requests,
            responses=responses,
            bank=bank,
            ablate_support=True,
        ),
    }
    aggregate = {name: _aggregate(items) for name, items in rows.items()}

    cold = aggregate["cold"]
    warm = aggregate["warm"]
    restart = aggregate["restart"]
    sham_agg = aggregate["sham"]
    ablation = aggregate["ablation"]

    comparisons = {
        "warm_model_call_reduction": (
            1.0 - warm["model_calls"] / cold["model_calls"]
            if cold["model_calls"]
            else None
        ),
        "warm_token_reduction": (
            1.0 - warm["total_tokens"] / cold["total_tokens"]
            if cold["total_tokens"]
            else None
        ),
        "warm_openrouter_cost_reduction": (
            1.0 - warm["openrouter_cost"] / cold["openrouter_cost"]
            if cold["openrouter_cost"]
            else None
        ),
        "warm_model_latency_reduction": (
            1.0 - warm["model_latency_ms"] / cold["model_latency_ms"]
            if cold["model_latency_ms"]
            else None
        ),
        "warm_minus_cold_terminal_yield": (
            warm["terminal_yield"] - cold["terminal_yield"]
        ),
        "sham_minus_warm_tokens": sham_agg["total_tokens"] - warm["total_tokens"],
        "ablation_minus_warm_tokens": ablation["total_tokens"] - warm["total_tokens"],
    }

    gates = {
        "provider_usage_present": cold["total_tokens"] > 0,
        "authorized_bank_verifier_backed": all(
            cap.verifier_evidence.get("terminal_candidate_ok") for cap in bank
        ),
        "restart_preserves_ids": [cap.capability_id for cap in bank]
        == [cap.capability_id for cap in restarted],
        "restart_matches_warm": restart == warm,
        "warm_not_worse_terminal_yield": warm["terminal_yield"] >= cold["terminal_yield"],
        "warm_uses_fewer_model_calls": warm["model_calls"] < cold["model_calls"],
        "warm_uses_fewer_tokens": warm["total_tokens"] < cold["total_tokens"],
        "warm_costs_less_openrouter": warm["openrouter_cost"] < cold["openrouter_cost"],
        "sham_not_better_than_warm_yield": sham_agg["terminal_yield"] <= warm["terminal_yield"],
        "ablation_restores_model_calls": ablation["model_calls"] == cold["model_calls"],
        "ablation_restores_tokens": ablation["total_tokens"] == cold["total_tokens"],
        "ablation_restores_terminal_yield": ablation["terminal_yield"] == cold["terminal_yield"],
    }

    models = sorted({str(row.get("model")) for row in responses.values()})
    providers = sorted({str(row.get("provider")) for row in responses.values()})

    report = {
        "protocol": "MATHGRAPH_OPENROUTER_COMPILED_VERIFIED_REUSE_V2",
        "comparison_design": "paired frozen cold transcript with deterministic verified-reuse controller",
        "models": models,
        "providers": providers,
        "rows": rows,
        "aggregate": aggregate,
        "comparisons": comparisons,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "This is a bounded system-level external-model experiment on seven fixed finite-magma "
            "tasks. OpenRouter supplies the frozen cold candidate for each task. Warm/restart/sham/"
            "ablation are paired counterfactual system evaluations using those exact same model "
            "responses as fallback, so model sampling is not a confound. The authorized bank was "
            "independently verified before this V2 evaluation. Avoided tokens/cost/latency mean "
            "the controller did not need to invoke the model for a task because an already-verified "
            "artifact independently solved it. This is not evidence of weight-level learning by "
            "Gemma and does not generalize beyond this bounded fixture."
        ),
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
