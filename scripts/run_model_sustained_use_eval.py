#!/usr/bin/env python3
"""Replayable model-facing sustained-use benchmark.

Mathematical truth is decided only by MathGraph's deterministic finite magma
checker. The deterministic provider qualifies the harness in CI; replay mode
evaluates a frozen external-model transcript without executing model code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mathgraph.finite_magma_world import (
    check_finite_countermodel,
    normalize_table,
    table_satisfies_equation,
)


PROPERTY_EQUATIONS = {
    "commutative": "(x * y) = (y * x)",
    "associative": "((x * y) * z) = (x * (y * z))",
    "idempotent": "(x * x) = x",
    "left_projection": "(x * y) = x",
    "right_projection": "(x * y) = y",
    "left_absorption": "(x * (x * y)) = (x * y)",
    "right_absorption": "((x * y) * y) = (x * y)",
}

KNOWN_TABLES = {
    "left_projection_2": ((0, 0), (1, 1)),
    "right_projection_2": ((0, 1), (0, 1)),
    "constant_zero_2": ((0, 0), (0, 0)),
    "commutative_nonassociative_3": ((0, 0, 1), (0, 1, 2), (1, 2, 0)),
}

TRAIN_TASKS = (
    ("train_left_projection", "(x * y) = x", "(x * y) = (y * x)", "left_projection_2"),
    ("train_right_projection", "(x * y) = y", "(x * y) = (y * x)", "right_projection_2"),
    ("train_comm_nonassoc", "(x * y) = (y * x)", "((x * y) * z) = (x * (y * z))", "commutative_nonassociative_3"),
    ("train_comm_nonidem", "(x * y) = (y * x)", "(x * x) = x", "constant_zero_2"),
)

FRESH_TASKS = (
    ("fresh_assoc_not_comm", "((x * y) * z) = (x * (y * z))", "(x * y) = (y * x)", "left_projection_2"),
    ("fresh_assoc_not_left", "((x * y) * z) = (x * (y * z))", "(x * y) = x", "right_projection_2"),
    ("fresh_assoc_not_right", "((x * y) * z) = (x * (y * z))", "(x * y) = y", "left_projection_2"),
    ("fresh_assoc_not_idem", "((x * y) * z) = (x * (y * z))", "(x * x) = x", "constant_zero_2"),
    ("fresh_comm_not_left_absorb", "(x * y) = (y * x)", "(x * (x * y)) = (x * y)", "commutative_nonassociative_3"),
    ("fresh_comm_not_left", "(x * y) = (y * x)", "(x * y) = x", "constant_zero_2"),
    ("fresh_idem_not_comm", "(x * x) = x", "(x * y) = (y * x)", "left_projection_2"),
)


@dataclass(frozen=True)
class Task:
    task_id: str
    source: str
    target: str
    deterministic_table_name: str


@dataclass(frozen=True)
class Capability:
    capability_id: str
    table: tuple[tuple[int, ...], ...]
    source_task_id: str
    behavior_signature: dict[str, bool]
    verifier_evidence: dict[str, Any]

    def public_summary(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "carrier_size": len(self.table),
            "source_task_id": self.source_task_id,
            "behavior_signature": dict(self.behavior_signature),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.public_summary(),
            "table": [list(row) for row in self.table],
            "verifier_evidence": dict(self.verifier_evidence),
        }


class TranscriptProvider:
    def __init__(self, transcript_path: str | Path) -> None:
        self.name = "transcript_replay"
        self.rows: dict[tuple[str, str], dict[str, Any]] = {}
        for line in Path(transcript_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            self.rows[(str(row["mode"]), str(row["task_id"]))] = row

    def complete(self, mode: str, task: Task, bank: Sequence[Capability]) -> dict[str, Any]:
        key = (mode, task.task_id)
        if key not in self.rows:
            raise KeyError(f"transcript missing row {key}")
        return dict(self.rows[key])


class DeterministicHarnessProvider:
    name = "deterministic_harness"

    def complete(self, mode: str, task: Task, bank: Sequence[Capability]) -> dict[str, Any]:
        if mode in {"warm", "restart", "sham", "ablation"} and bank:
            wanted = _required_signature(task.source, task.target)
            for cap in bank:
                if all(bool(cap.behavior_signature.get(k)) == v for k, v in wanted.items()):
                    candidate = {"reuse_id": cap.capability_id}
                    return _provider_row(candidate, self.name)
        table = KNOWN_TABLES[task.deterministic_table_name]
        return _provider_row({"table": [list(row) for row in table]}, self.name)


def _provider_row(candidate: dict[str, Any], model: str) -> dict[str, Any]:
    raw = json.dumps(candidate, sort_keys=True)
    return {
        "candidate": candidate,
        "model": model,
        "raw": raw,
        "usage": {},
        "latency_ms": 0.0,
    }


def _tasks(rows: Sequence[tuple[str, str, str, str]]) -> list[Task]:
    return [Task(*row) for row in rows]


def _table_id(table: Sequence[Sequence[int]]) -> str:
    t = normalize_table(table)
    payload = json.dumps([list(row) for row in t], separators=(",", ":"))
    return "cap_" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def _signature(table: Sequence[Sequence[int]]) -> dict[str, bool]:
    t = normalize_table(table)
    return {name: bool(table_satisfies_equation(t, eq)) for name, eq in PROPERTY_EQUATIONS.items()}


def _required_signature(source: str, target: str) -> dict[str, bool]:
    reverse = {eq: name for name, eq in PROPERTY_EQUATIONS.items()}
    out: dict[str, bool] = {}
    if source in reverse:
        out[reverse[source]] = True
    if target in reverse:
        out[reverse[target]] = False
    return out


def _prompt(task: Task, mode: str, bank: Sequence[Capability]) -> str:
    lines = [
        "Propose a finite magma countermodel.",
        f"Source must hold globally: {task.source}",
        f"Target must fail somewhere: {task.target}",
        'Return JSON: {"table":[[...],...]} or {"reuse_id":"cap_..."} if a supplied capability applies.',
        "An independent checker decides correctness.",
    ]
    if bank:
        lines.append("Reusable verified capability summaries:")
        lines.extend(json.dumps(cap.public_summary(), sort_keys=True) for cap in bank)
    else:
        lines.append("No reusable capabilities are available.")
    lines.append(f"Condition: {mode}")
    return "\n".join(lines)


def _candidate(row: dict[str, Any]) -> dict[str, Any]:
    candidate = row.get("candidate")
    if isinstance(candidate, dict):
        return candidate
    raise ValueError("transcript row requires a candidate object")


def _resolve(candidate: dict[str, Any], bank: Sequence[Capability]) -> tuple[Any | None, str | None, str]:
    if "reuse_id" in candidate:
        cid = str(candidate["reuse_id"])
        for cap in bank:
            if cap.capability_id == cid:
                return cap.table, cid, "reuse"
        return None, cid, "unknown_reuse_id"
    if "table" in candidate:
        try:
            return normalize_table(candidate["table"]), None, "synthesized_table"
        except Exception:
            return None, None, "invalid_table"
    return None, None, "invalid_candidate"


def _evaluate(provider: Any, task: Task, mode: str, bank: Sequence[Capability]) -> dict[str, Any]:
    row = provider.complete(mode, task, bank)
    candidate = _candidate(row)
    table, reuse_id, kind = _resolve(candidate, bank)
    if table is None:
        verified = False
        verification = {"terminal_candidate_ok": False, "diagnostic": kind}
    else:
        checked = check_finite_countermodel(task.source, task.target, table)
        verified = bool(checked.terminal_candidate_ok)
        verification = checked.to_dict()
    usage = row.get("usage") or {}
    prompt = _prompt(task, mode, bank)
    raw = str(row.get("raw") or json.dumps(candidate, sort_keys=True))
    return {
        "task_id": task.task_id,
        "mode": mode,
        "model": str(row.get("model") or provider.name),
        "candidate_kind": kind,
        "reuse_id": reuse_id,
        "verified": verified,
        "verification": verification,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "latency_ms": row.get("latency_ms"),
        "prompt_bytes": len(prompt.encode()),
        "candidate_bytes": len(json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode()),
        "raw_response_bytes": len(raw.encode()),
    }


def _promote(provider: Any, tasks: Sequence[Task]) -> tuple[list[Capability], list[dict[str, Any]]]:
    bank: dict[str, Capability] = {}
    evidence_rows = []
    for task in tasks:
        row = provider.complete("train_cold", task, ())
        candidate = _candidate(row)
        table, reuse_id, kind = _resolve(candidate, ())
        if table is None or reuse_id is not None:
            evidence_rows.append({"task_id": task.task_id, "promoted": False, "candidate_kind": kind})
            continue
        checked = check_finite_countermodel(task.source, task.target, table)
        if not checked.terminal_candidate_ok:
            evidence_rows.append({"task_id": task.task_id, "promoted": False, "verification": checked.to_dict()})
            continue
        cid = _table_id(table)
        cap = Capability(
            capability_id=cid,
            table=normalize_table(table),
            source_task_id=task.task_id,
            behavior_signature=_signature(table),
            verifier_evidence={
                "terminal_candidate_ok": True,
                "source_equation": task.source,
                "target_equation": task.target,
                "witness_env": dict(checked.witness_env),
            },
        )
        bank.setdefault(cid, cap)
        evidence_rows.append({"task_id": task.task_id, "promoted": True, "capability_id": cid})
    return list(bank.values()), evidence_rows


def _restart(bank: Sequence[Capability], path: Path) -> list[Capability]:
    path.write_text(json.dumps([cap.to_dict() for cap in bank], indent=2, sort_keys=True) + "\n")
    rows = json.loads(path.read_text())
    return [
        Capability(
            capability_id=row["capability_id"],
            table=normalize_table(row["table"]),
            source_task_id=row["source_task_id"],
            behavior_signature={k: bool(v) for k, v in row["behavior_signature"].items()},
            verifier_evidence=dict(row["verifier_evidence"]),
        )
        for row in rows
    ]


def _sham(bank: Sequence[Capability]) -> list[Capability]:
    out = []
    for cap in bank:
        if cap.behavior_signature.get("left_projection") or cap.behavior_signature.get("right_projection"):
            fake = KNOWN_TABLES["constant_zero_2"]
        else:
            fake = KNOWN_TABLES["left_projection_2"]
        out.append(
            Capability(
                capability_id=cap.capability_id,
                table=normalize_table(fake),
                source_task_id=cap.source_task_id,
                behavior_signature=dict(cap.behavior_signature),
                verifier_evidence={"control": "SHAM_PAYLOAD", "authorized": False},
            )
        )
    return out


def _supporting_ids(task: Task, bank: Sequence[Capability]) -> set[str]:
    return {
        cap.capability_id
        for cap in bank
        if check_finite_countermodel(task.source, task.target, cap.table).terminal_candidate_ok
    }


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    def optional_sum(field: str) -> int | float | None:
        vals = [row[field] for row in rows if row.get(field) is not None]
        return sum(vals) if vals else None
    verified = sum(int(row["verified"]) for row in rows)
    reuse = sum(int(row["candidate_kind"] == "reuse") for row in rows)
    return {
        "tasks": len(rows),
        "verified_terminal_results": verified,
        "terminal_yield": verified / len(rows) if rows else 0.0,
        "reuse_hits": reuse,
        "reuse_rate": reuse / len(rows) if rows else 0.0,
        "verifier_calls": len(rows),
        "prompt_bytes": sum(row["prompt_bytes"] for row in rows),
        "candidate_bytes": sum(row["candidate_bytes"] for row in rows),
        "raw_response_bytes": sum(row["raw_response_bytes"] for row in rows),
        "input_tokens": optional_sum("input_tokens"),
        "output_tokens": optional_sum("output_tokens"),
        "total_tokens": optional_sum("total_tokens"),
        "latency_ms": optional_sum("latency_ms"),
    }


def run(provider: Any, out_dir: str | Path) -> dict[str, Any]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    bank, training = _promote(provider, _tasks(TRAIN_TASKS))
    restarted = _restart(bank, output / "capability_bank.json")
    sham = _sham(restarted)

    rows = {mode: [] for mode in ("cold", "warm", "restart", "sham", "ablation")}
    for task in _tasks(FRESH_TASKS):
        rows["cold"].append(_evaluate(provider, task, "cold", ()))
        rows["warm"].append(_evaluate(provider, task, "warm", restarted))
        rows["restart"].append(_evaluate(provider, task, "restart", restarted))
        rows["sham"].append(_evaluate(provider, task, "sham", sham))
        supporting = _supporting_ids(task, restarted)
        ablated = [cap for cap in restarted if cap.capability_id not in supporting]
        rows["ablation"].append(_evaluate(provider, task, "ablation", ablated))

    agg = {mode: _aggregate(items) for mode, items in rows.items()}
    cold, warm = agg["cold"], agg["warm"]
    token_claim = cold["total_tokens"] is not None and warm["total_tokens"] is not None
    comparisons = {
        "warm_minus_cold_terminal_yield": warm["terminal_yield"] - cold["terminal_yield"],
        "warm_candidate_byte_reduction": 1.0 - warm["candidate_bytes"] / cold["candidate_bytes"] if cold["candidate_bytes"] else None,
        "warm_total_token_reduction": 1.0 - warm["total_tokens"] / cold["total_tokens"] if token_claim and cold["total_tokens"] else None,
        "token_claim_available": token_claim,
        "warm_reuse_hits": warm["reuse_hits"],
        "sham_terminal_yield": agg["sham"]["terminal_yield"],
        "ablation_reuse_hits": agg["ablation"]["reuse_hits"],
    }
    gates = {
        "verified_training_promotes_capability": bool(bank),
        "promoted_memory_is_verifier_backed": all(cap.verifier_evidence.get("terminal_candidate_ok") for cap in bank),
        "restart_preserves_ids": [cap.capability_id for cap in restarted] == [cap.capability_id for cap in bank],
        "warm_preserves_cold_terminal_yield": warm["terminal_yield"] == cold["terminal_yield"],
        "warm_has_reuse": warm["reuse_hits"] > 0,
        "restart_matches_warm_yield": agg["restart"]["terminal_yield"] == warm["terminal_yield"],
        "restart_matches_warm_reuse": agg["restart"]["reuse_hits"] == warm["reuse_hits"],
        "warm_candidate_payload_not_larger": warm["candidate_bytes"] <= cold["candidate_bytes"],
        "sham_not_better_than_warm": agg["sham"]["terminal_yield"] <= warm["terminal_yield"],
        "ablation_not_more_reuse_than_warm": agg["ablation"]["reuse_hits"] <= warm["reuse_hits"],
    }
    report = {
        "protocol": "MATHGRAPH_MODEL_SUSTAINED_USE_V1",
        "provider": provider.name,
        "provider_is_external_model": provider.name == "transcript_replay",
        "training": training,
        "promoted_capabilities": [cap.to_dict() for cap in bank],
        "rows": rows,
        "aggregate": agg,
        "comparisons": comparisons,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "deterministic_harness qualifies the protocol only and is not an LLM result. "
            "External-model claims require a frozen transcript with model identity; token claims "
            "require provider-reported usage. Every mathematical terminal result is rechecked by "
            "MathGraph's independent finite magma checker."
        ),
    }
    (output / "model_sustained_use_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("deterministic", "transcript"), default="deterministic")
    parser.add_argument("--transcript")
    parser.add_argument("--out-dir", default="/tmp/open_math_model_sustained_use_v1/model_pilot")
    args = parser.parse_args()

    if args.provider == "transcript":
        if not args.transcript:
            parser.error("--transcript is required with --provider transcript")
        provider: Any = TranscriptProvider(args.transcript)
    else:
        provider = DeterministicHarnessProvider()

    report = run(provider, args.out_dir)
    print(json.dumps({
        "provider": report["provider"],
        "provider_is_external_model": report["provider_is_external_model"],
        "verdict": report["verdict"],
        "promoted_capability_count": len(report["promoted_capabilities"]),
        "aggregate": report["aggregate"],
        "comparisons": report["comparisons"],
        "claim_boundary": report["claim_boundary"],
    }, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
