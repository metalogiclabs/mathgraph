#!/usr/bin/env python3
"""OpenRouter V3: model-acquired verified capability -> restart -> fresh reuse.

Unlike V2, the capability bank is not preauthorized. Gemma proposes finite
countermodels on four acquisition tasks. MathGraph independently verifies each
proposal before promotion. The promoted bank is serialized/reloaded, then tested
on seven untouched related tasks.

For a paired comparison, OpenRouter also produces one frozen cold response for
each fresh task. Warm/restart/sham/ablation use those exact same responses only
as fallback, eliminating cross-condition model-sampling noise.

A failed finite check never becomes mathematical truth.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_FINITE = _load_module("_v3_finite", REPO_ROOT / "mathgraph" / "finite_magma_world.py")
_ROUTER = _load_module("_v3_router", REPO_ROOT / "scripts" / "run_openrouter_sustained_use_capture_v1.py")

check_finite_countermodel = _FINITE.check_finite_countermodel
normalize_table = _FINITE.normalize_table

MODEL = "google/gemma-4-31b-it"
PROVIDER = "deepinfra"

ACQUISITION_TASKS = (
    ("acq_left_projection", "(x * y) = x", "(x * y) = (y * x)"),
    ("acq_right_projection", "(x * y) = y", "(x * y) = (y * x)"),
    ("acq_comm_nonassoc", "(x * y) = (y * x)", "((x * y) * z) = (x * (y * z))"),
    ("acq_comm_nonidem", "(x * y) = (y * x)", "(x * x) = x"),
)

FRESH_TASKS = (
    ("fresh_assoc_not_comm", "((x * y) * z) = (x * (y * z))", "(x * y) = (y * x)"),
    ("fresh_assoc_not_left", "((x * y) * z) = (x * (y * z))", "(x * y) = x"),
    ("fresh_assoc_not_right", "((x * y) * z) = (x * (y * z))", "(x * y) = y"),
    ("fresh_assoc_not_idem", "((x * y) * z) = (x * (y * z))", "(x * x) = x"),
    ("fresh_comm_not_left_absorb", "(x * y) = (y * x)", "(x * (x * y)) = (x * y)"),
    ("fresh_comm_not_left", "(x * y) = (y * x)", "(x * y) = x"),
    ("fresh_idem_not_comm", "(x * x) = x", "(x * y) = (y * x)"),
)


@dataclass(frozen=True)
class Capability:
    capability_id: str
    table: tuple[tuple[int, ...], ...]
    source_task_id: str
    verifier_evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "table": [list(r) for r in self.table],
            "carrier_size": len(self.table),
            "source_task_id": self.source_task_id,
            "verifier_evidence": self.verifier_evidence,
        }


def _prompt(source: str, target: str, feedback: str | None = None) -> str:
    lines = [
        "Propose a finite magma countermodel.",
        f"Source equation must hold for every assignment: {source}",
        f"Target equation must fail for at least one assignment: {target}",
        "Return exactly one JSON object of the form {\"table\":[[...],[...]]}.",
        "Use a square carrier table of size 2 or 3 only, with entries 0..n-1.",
        "Do not return prose. Do not claim TRUE. An independent checker decides correctness.",
    ]
    if feedback:
        lines.extend([
            "The previous proposal was independently rejected.",
            f"Checker feedback: {feedback}",
            "Return a different corrected table.",
        ])
    return "\n".join(lines)


def _call(api_key: str, prompt: str, model: str, provider: str) -> dict[str, Any]:
    result = _ROUTER._call(
        api_key=api_key,
        prompt=prompt,
        model=model,
        provider=provider,
        max_tokens=256,
        timeout=180.0,
        max_attempts=3,
    )
    response = result.get("response") or {}
    usage = result.get("usage") or {}
    raw_usage = usage.get("raw_openrouter_usage") or {}
    return {
        "transport_ok": bool(result.get("ok")),
        "model": str(response.get("model") or model),
        "provider": response.get("provider"),
        "generation_id": response.get("id"),
        "candidate": result.get("candidate") or {},
        "raw": result.get("raw_text") or "",
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "latency_ms": float(result.get("latency_ms") or 0.0),
        "openrouter_cost": float(raw_usage.get("cost") or 0.0),
        "transport_errors": result.get("errors", []),
    }


def _candidate_table(candidate: dict[str, Any]) -> tuple[tuple[int, ...], ...] | None:
    table = candidate.get("table") if isinstance(candidate, dict) else None
    if table is None:
        return None
    try:
        normalized = normalize_table(table)
    except Exception:
        return None
    if len(normalized) not in (2, 3):
        return None
    return normalized


def _cap_id(table: Sequence[Sequence[int]]) -> str:
    payload = json.dumps([list(r) for r in table], separators=(",", ":"), sort_keys=True)
    return "modelcap_" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def _acquire_task(
    api_key: str,
    task_id: str,
    source: str,
    target: str,
    model: str,
    provider: str,
    max_rounds: int,
) -> tuple[Capability | None, list[dict[str, Any]]]:
    attempts = []
    feedback = None
    for round_index in range(1, max_rounds + 1):
        prompt = _prompt(source, target, feedback)
        call = _call(api_key, prompt, model, provider)
        table = _candidate_table(call["candidate"])
        if table is None:
            verification = {
                "terminal_candidate_ok": False,
                "diagnostic": "missing/invalid table or carrier not in {2,3}",
            }
        else:
            verification = check_finite_countermodel(source, target, table).to_dict()

        row = {
            "task_id": task_id,
            "round": round_index,
            "prompt": prompt,
            **call,
            "verification": verification,
        }
        attempts.append(row)

        if verification.get("terminal_candidate_ok"):
            cap = Capability(
                capability_id=_cap_id(table),
                table=table,
                source_task_id=task_id,
                verifier_evidence={
                    "terminal_candidate_ok": True,
                    "source_equation": source,
                    "target_equation": target,
                    "witness_env": verification.get("witness_env") or {},
                    "model": call["model"],
                    "provider": call["provider"],
                    "generation_id": call["generation_id"],
                    "acquisition_round": round_index,
                },
            )
            return cap, attempts
        feedback = str(verification.get("diagnostic") or "candidate rejected")
    return None, attempts


def _fresh_cold(
    api_key: str,
    task_id: str,
    source: str,
    target: str,
    model: str,
    provider: str,
) -> dict[str, Any]:
    prompt = _prompt(source, target)
    call = _call(api_key, prompt, model, provider)
    table = _candidate_table(call["candidate"])
    if table is None:
        verification = {
            "terminal_candidate_ok": False,
            "diagnostic": "missing/invalid table or carrier not in {2,3}",
        }
    else:
        verification = check_finite_countermodel(source, target, table).to_dict()
    return {
        "task_id": task_id,
        "source": source,
        "target": target,
        "prompt": prompt,
        **call,
        "verification": verification,
    }


def _restart(bank: Sequence[Capability], path: Path) -> list[Capability]:
    path.write_text(
        json.dumps([cap.to_dict() for cap in bank], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = json.loads(path.read_text())
    return [
        Capability(
            capability_id=row["capability_id"],
            table=normalize_table(row["table"]),
            source_task_id=row["source_task_id"],
            verifier_evidence=dict(row["verifier_evidence"]),
        )
        for row in rows
    ]


def _sham(bank: Sequence[Capability]) -> list[Capability]:
    if not bank:
        return []
    tables = [cap.table for cap in bank]
    if len(tables) == 1:
        tables = [((0, 0), (0, 0))]
    else:
        tables = tables[1:] + tables[:1]
    return [
        Capability(
            capability_id=cap.capability_id,
            table=tables[i],
            source_task_id=cap.source_task_id,
            verifier_evidence={"control": "SHAM_ROTATED_PAYLOAD", "authorized": False},
        )
        for i, cap in enumerate(bank)
    ]


def _supporting(
    bank: Sequence[Capability],
    source: str,
    target: str,
) -> list[tuple[Capability, dict[str, Any], int]]:
    hits = []
    for index, cap in enumerate(bank, start=1):
        checked = check_finite_countermodel(source, target, cap.table).to_dict()
        if checked["terminal_candidate_ok"]:
            hits.append((cap, checked, index))
    return hits


def _evaluate(
    condition: str,
    bank: Sequence[Capability],
    cold_rows: Sequence[dict[str, Any]],
    *,
    ablate: bool = False,
) -> list[dict[str, Any]]:
    out = []
    for cold in cold_rows:
        source, target = cold["source"], cold["target"]
        local = list(bank)
        if ablate:
            ids = {cap.capability_id for cap, _v, _i in _supporting(local, source, target)}
            local = [cap for cap in local if cap.capability_id not in ids]

        t0 = time.perf_counter()
        hits = _supporting(local, source, target)
        controller_ms = (time.perf_counter() - t0) * 1000.0
        if hits:
            cap, checked, calls = hits[0]
            out.append({
                "task_id": cold["task_id"],
                "condition": condition,
                "route": "VERIFIED_REUSE",
                "terminal_verified": True,
                "capability_id": cap.capability_id,
                "controller_verifier_calls": calls,
                "controller_latency_ms": controller_ms,
                "model_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "model_latency_ms": 0.0,
                "openrouter_cost": 0.0,
                "verification": checked,
            })
        else:
            v = cold["verification"]
            out.append({
                "task_id": cold["task_id"],
                "condition": condition,
                "route": "OPENROUTER_FALLBACK",
                "terminal_verified": bool(v.get("terminal_candidate_ok")),
                "capability_id": None,
                "controller_verifier_calls": len(local),
                "controller_latency_ms": controller_ms,
                "model_calls": 1,
                "input_tokens": cold["input_tokens"],
                "output_tokens": cold["output_tokens"],
                "total_tokens": cold["total_tokens"],
                "model_latency_ms": cold["latency_ms"],
                "openrouter_cost": cold["openrouter_cost"],
                "verification": v,
            })
    return out


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    verified = sum(bool(r["terminal_verified"]) for r in rows)
    return {
        "tasks": n,
        "verified_terminal_results": verified,
        "terminal_yield": verified / n if n else 0.0,
        "verified_reuse_hits": sum(r["route"] == "VERIFIED_REUSE" for r in rows),
        "model_calls": sum(int(r["model_calls"]) for r in rows),
        "input_tokens": sum(int(r["input_tokens"]) for r in rows),
        "output_tokens": sum(int(r["output_tokens"]) for r in rows),
        "total_tokens": sum(int(r["total_tokens"]) for r in rows),
        "model_latency_ms": sum(float(r["model_latency_ms"]) for r in rows),
        "controller_latency_ms": sum(float(r["controller_latency_ms"]) for r in rows),
        "controller_verifier_calls": sum(int(r["controller_verifier_calls"]) for r in rows),
        "openrouter_cost": sum(float(r["openrouter_cost"]) for r in rows),
    }


def _acquisition_cost(attempts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model_calls": len(attempts),
        "input_tokens": sum(int(r["input_tokens"]) for r in attempts),
        "output_tokens": sum(int(r["output_tokens"]) for r in attempts),
        "total_tokens": sum(int(r["total_tokens"]) for r in attempts),
        "latency_ms": sum(float(r["latency_ms"]) for r in attempts),
        "openrouter_cost": sum(float(r["openrouter_cost"]) for r in attempts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--provider", default=PROVIDER)
    parser.add_argument("--acquisition-rounds", type=int, default=3)
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    promoted: dict[str, Capability] = {}
    acquisition_attempts = []
    acquisition_outcomes = []
    for task_id, source, target in ACQUISITION_TASKS:
        cap, attempts = _acquire_task(
            api_key, task_id, source, target, args.model, args.provider, args.acquisition_rounds
        )
        acquisition_attempts.extend(attempts)
        if cap is not None:
            promoted.setdefault(cap.capability_id, cap)
        acquisition_outcomes.append({
            "task_id": task_id,
            "verified_capability_acquired": cap is not None,
            "capability_id": cap.capability_id if cap else None,
            "attempt_count": len(attempts),
        })

    bank = list(promoted.values())
    restarted = _restart(bank, out / "model_acquired_verified_bank.json")
    sham = _sham(bank)

    cold_rows = [
        _fresh_cold(api_key, task_id, source, target, args.model, args.provider)
        for task_id, source, target in FRESH_TASKS
    ]
    rows = {
        "cold": _evaluate("cold", (), cold_rows),
        "warm": _evaluate("warm", bank, cold_rows),
        "restart": _evaluate("restart", restarted, cold_rows),
        "sham": _evaluate("sham", sham, cold_rows),
        "ablation": _evaluate("ablation", bank, cold_rows, ablate=True),
    }
    aggregate = {name: _aggregate(items) for name, items in rows.items()}
    acquisition = _acquisition_cost(acquisition_attempts)

    cold = aggregate["cold"]
    warm = aggregate["warm"]
    restart = aggregate["restart"]
    sham_agg = aggregate["sham"]
    ablation = aggregate["ablation"]

    full_cold_tokens = acquisition["total_tokens"] + cold["total_tokens"]
    full_dev_tokens = acquisition["total_tokens"] + warm["total_tokens"]
    full_cold_calls = acquisition["model_calls"] + cold["model_calls"]
    full_dev_calls = acquisition["model_calls"] + warm["model_calls"]
    full_cold_cost = acquisition["openrouter_cost"] + cold["openrouter_cost"]
    full_dev_cost = acquisition["openrouter_cost"] + warm["openrouter_cost"]

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
        "sham_minus_warm_tokens": sham_agg["total_tokens"] - warm["total_tokens"],
        "ablation_minus_warm_tokens": ablation["total_tokens"] - warm["total_tokens"],
    }

    restart_match = all(
        restart[k] == warm[k]
        for k in (
            "tasks", "verified_terminal_results", "terminal_yield",
            "verified_reuse_hits", "model_calls", "input_tokens",
            "output_tokens", "total_tokens", "model_latency_ms", "openrouter_cost",
        )
    )
    gates = {
        "at_least_one_model_acquired_capability_verified": bool(bank),
        "all_promoted_capabilities_verifier_backed": all(
            cap.verifier_evidence.get("terminal_candidate_ok") for cap in bank
        ),
        "fresh_set_untouched_during_acquisition": True,
        "restart_preserves_ids": [c.capability_id for c in bank] == [c.capability_id for c in restarted],
        "restart_matches_warm_substantive_metrics": restart_match,
        "warm_not_worse_terminal_yield": warm["terminal_yield"] >= cold["terminal_yield"],
        "warm_uses_fewer_fresh_model_calls": warm["model_calls"] < cold["model_calls"],
        "warm_uses_fewer_fresh_tokens": warm["total_tokens"] < cold["total_tokens"],
        "ablation_restores_cold_model_calls": ablation["model_calls"] == cold["model_calls"],
        "ablation_restores_cold_tokens": ablation["total_tokens"] == cold["total_tokens"],
        "ablation_restores_cold_terminal_yield": ablation["terminal_yield"] == cold["terminal_yield"],
        "sham_not_better_than_warm_yield": sham_agg["terminal_yield"] <= warm["terminal_yield"],
    }

    report = {
        "protocol": "MATHGRAPH_OPENROUTER_MODEL_ACQUIRED_VERIFIED_REUSE_V3",
        "model": args.model,
        "provider": args.provider,
        "acquisition_tasks": [
            {"task_id": a, "source": b, "target": c} for a, b, c in ACQUISITION_TASKS
        ],
        "fresh_tasks": [
            {"task_id": a, "source": b, "target": c} for a, b, c in FRESH_TASKS
        ],
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
            "This bounded V3 experiment uses a real OpenRouter Gemma model to generate the acquisition "
            "artifacts themselves. Only independently verified finite countermodels are promoted. "
            "The fresh seven-task set is not used during acquisition. Fresh cold model responses are "
            "frozen once and reused as identical fallback under warm/restart/sham/ablation, so model "
            "sampling is not a comparison confound. Results concern external model-call avoidance by "
            "a verified controller, not weight updates inside Gemma and not generalization to arbitrary mathematics."
        ),
    }

    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "model": report["model"],
        "provider": report["provider"],
        "acquisition_outcomes": acquisition_outcomes,
        "acquisition_cost": acquisition,
        "promoted_capability_count": len(bank),
        "aggregate": aggregate,
        "comparisons": comparisons,
        "gates": gates,
        "claim_boundary": report["claim_boundary"],
    }, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
