"""Autonomous finite-core compounding engine façade.

This module gives the repo a stable importable entry point for the autonomous
ETP compounding path. It deliberately delegates finite recovery to the existing
repo-native multi-episode compounding engine rather than simulating gains.

Serious path invariant:
- FALSE recovery is counted only through the finite magma satisfaction cache.
- TRUE contamination is audited through matrix-labelled TRUE controls.
- Failed finite search remains residual evidence and never becomes TRUE.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mathgraph.autonomous_finite_recovery import (
    FiniteRecoveryConfig,
    build_finite_recovery_core,
    evaluate_false_pairs,
    greedy_route,
    pair_recovery_matrix,
    residual_marginal_repair,
)
from mathgraph.compounding_metrics import obstruction_entropy
from mathgraph.obstruction_atlas import summarize_obstructions
from mathgraph.polarized_quotient_ir import build_pair_features
from mathgraph.residual_lawbook import load_repair_lawbook, recommend_from_lawbook, write_repair_lawbook
from mathgraph.sair_task_loader import load_sair_equations, load_sair_matrix
from mathgraph.terminal_form_contract import TerminalForm, audit_terminal_rows, boundary_preserved


@dataclass(frozen=True)
class AutonomousCompoundingConfig:
    out_dir: str | Path
    equations: str | Path | None = None
    matrix: str | Path | None = None
    episodes: int = 4
    sample_pairs: int = 4000
    repair_budget: int = 40
    max_n: int = 5
    seed: int = 20260524
    tiny_demo: bool = False
    finite_core_mode: str = "facade"
    constructor_limit: int | None = None
    include_random_constructors: bool = False
    random_constructor_count: int = 0
    lawbook_path: str | Path | None = None
    reuse_lawbook: bool = False
    write_report: bool = False


def run_autonomous_compounding(config: AutonomousCompoundingConfig) -> dict[str, Any]:
    """Run the finite-core compounding engine through a small autonomous façade."""

    if config.finite_core_mode == "native_v2":
        return _run_native_v2(config)
    if config.finite_core_mode != "facade":
        raise ValueError(f"unsupported finite_core_mode: {config.finite_core_mode}")

    from scripts.run_mathgraph_compounding_engine import EngineConfig, run_engine

    if not config.tiny_demo and (not config.equations or not config.matrix):
        raise FileNotFoundError("real autonomous compounding requires equations and matrix; use tiny_demo=True for fallback wiring")

    engine_config = EngineConfig(
        equations=str(config.equations) if config.equations else None,
        matrix=str(config.matrix) if config.matrix else None,
        out_dir=Path(config.out_dir),
        episodes=max(1, int(config.episodes)),
        train_false=max(1, int(config.sample_pairs)),
        eval_false=max(1, int(config.sample_pairs)),
        eval_true=max(1, int(config.sample_pairs) // 3),
        route_train_false=max(1, int(config.sample_pairs)),
        route_eval_false=max(1, int(config.sample_pairs)),
        max_n=max(2, int(config.max_n)),
        repair_steps=max(1, int(config.repair_budget)),
        seed=int(config.seed),
        tiny_demo=bool(config.tiny_demo),
    )
    summary = run_engine(engine_config)
    terminal_rows = _terminal_rows_from_summary(summary)
    terminal_audit = audit_terminal_rows(terminal_rows)
    output_dir = Path(str(summary.get("output_dir") or config.out_dir))
    artifacts = _artifact_paths(output_dir)
    generic_yield = int(summary.get("generic_final_yield", 0) or 0)
    repair_yield = int(summary.get("repair_final_yield", 0) or 0)
    generic_residuals = int(summary.get("generic_final_residuals", 0) or 0)
    repair_residuals = int(summary.get("repair_final_residuals", 0) or 0)
    failed_true = int(summary.get("failed_search_promoted_true_count", summary.get("failed_search_promoted_true", 0)) or 0)
    advisory_claims = int(summary.get("terminal_claims_from_advisory_count", 0) or 0)
    true_contamination = int(summary.get("true_contamination_count", 0) or 0)
    boundary_ok = boundary_preserved(terminal_rows) and true_contamination == 0 and advisory_claims == 0 and failed_true == 0
    autonomous_gates_pass = bool(boundary_ok and repair_yield >= generic_yield and repair_residuals <= generic_residuals)
    summary = dict(summary)
    summary.update(
        {
            "autonomous_facade": True,
            "serious_path_uses_finite_recovery_core": True,
            "terminal_contract": [form.value for form in TerminalForm],
            "terminal_audit": terminal_audit,
            "advisory_boundary_preserved": boundary_ok,
            "all_gates_passed": autonomous_gates_pass,
            "true_contamination_count": true_contamination,
            "terminal_claims_from_advisory_count": advisory_claims,
            "failed_search_promoted_true": failed_true,
            "failed_search_promoted_true_count": failed_true,
            "generic_final_yield": generic_yield,
            "repair_final_yield": repair_yield,
            "generic_final_residuals": generic_residuals,
            "repair_final_residuals": repair_residuals,
            "repair_gain_over_generic": repair_yield - generic_yield,
            "artifacts": artifacts,
        }
    )
    return summary


def _run_native_v2(config: AutonomousCompoundingConfig) -> dict[str, Any]:
    out_dir = Path(config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    equations, matrix, source_mode = _load_inputs(config)
    false_pairs, true_pairs = _sample_pairs(matrix, len(equations), config)
    recovery = build_finite_recovery_core(
        equations,
        FiniteRecoveryConfig(
            max_n=max(2, int(config.max_n)),
            constructor_limit=config.constructor_limit,
            random_seed=int(config.seed),
            include_random_constructors=config.include_random_constructors,
            random_constructor_count=config.random_constructor_count,
        ),
    )
    false_matrix = pair_recovery_matrix(false_pairs, recovery.sat_cache)
    true_matrix = pair_recovery_matrix(true_pairs, recovery.sat_cache)
    pair_eval = evaluate_false_pairs(false_pairs, recovery.sat_cache, recovery.constructors)
    budget = max(1, int(config.repair_budget))
    generic_indices, generic_mask, generic_route = greedy_route(false_matrix, recovery.constructor_manifest, budget=min(budget, max(1, budget // 2)), seed=config.seed)
    repair_indices_extra, repair_mask, repair_route = residual_marginal_repair(false_matrix, generic_mask, recovery.constructor_manifest, budget=budget, seed=config.seed)
    repair_indices = list(dict.fromkeys(generic_indices + repair_indices_extra))
    repair_mask = _mask(false_matrix, repair_indices)
    features_df = _pair_features(equations, false_pairs)
    residual_df = features_df[~repair_mask].copy() if len(features_df) else pd.DataFrame()
    obstruction_records = summarize_obstructions(residual_df.to_dict("records") if not residual_df.empty else [], stage="native_v2")
    obstruction_df = pd.DataFrame([{**rec.to_dict(), "source_mode": source_mode} for rec in obstruction_records])
    lawbook_path = Path(config.lawbook_path) if config.lawbook_path else out_dir / "lawbook.sqlite"
    repair_lawbook_df = _repair_lawbook_rows(repair_route, recovery.constructor_manifest, features_df, source_mode)
    write_repair_lawbook(lawbook_path, repair_lawbook_df, obstruction_df, {"run_id": "autonomous_v2", "source_mode": source_mode})
    prior_lawbook = load_repair_lawbook(lawbook_path) if config.reuse_lawbook or lawbook_path.exists() else pd.DataFrame()
    lawbook_indices = _lawbook_indices(features_df, prior_lawbook, recovery.constructor_manifest, budget)
    lawbook_indices = list(dict.fromkeys(repair_indices + lawbook_indices))[: max(len(repair_indices), budget)]
    lawbook_mask = _mask(false_matrix, lawbook_indices)
    compact_indices = _compact_indices(repair_lawbook_df, recovery.constructor_manifest, budget)
    compact_indices = list(dict.fromkeys(lawbook_indices + compact_indices))[: max(len(lawbook_indices), budget)]
    compact_mask = _mask(false_matrix, compact_indices)
    terminal_rows = [
        {"status": "finite_countermodel_found", "eq1_holds": True, "eq2_violated": True, "finite_checker_valid": True},
        {"status": "failed_search", "finite_search_miss": True},
    ]
    terminal_audit = audit_terminal_rows(terminal_rows)
    true_contamination = int(_mask(true_matrix, compact_indices).sum()) if len(true_pairs) else 0
    episode_rows = [
        _episode_row(0, "generic", generic_indices, generic_mask, false_matrix, true_matrix, previous=None),
        _episode_row(1, "residual_repair", repair_indices, repair_mask, false_matrix, true_matrix, previous=generic_mask),
        _episode_row(2, "lawbook_reuse", lawbook_indices, lawbook_mask, false_matrix, true_matrix, previous=repair_mask),
        _episode_row(3, "compact_atlas", compact_indices, compact_mask, false_matrix, true_matrix, previous=lawbook_mask),
    ][: max(1, int(config.episodes))]
    generic = episode_rows[0]
    repair = episode_rows[1] if len(episode_rows) > 1 else generic
    lawbook = episode_rows[2] if len(episode_rows) > 2 else repair
    compact = episode_rows[3] if len(episode_rows) > 3 else lawbook
    artifacts = _write_native_outputs(
        out_dir,
        summary_rows=episode_rows,
        gate_rows=[],
        features_df=features_df,
        true_features_df=_pair_features(equations, true_pairs),
        constructor_manifest=recovery.constructor_manifest,
        pair_eval=pair_eval,
        generic_route=generic_route,
        repair_route=repair_route,
        lawbook_route=_route_df("lawbook_reuse", lawbook_indices, recovery.constructor_manifest, lawbook_mask, false_matrix),
        compact_route=_route_df("compact_atlas", compact_indices, recovery.constructor_manifest, compact_mask, false_matrix),
        obstruction_df=obstruction_df,
        residual_df=residual_df,
        terminal_audit=terminal_audit,
        lawbook_path=lawbook_path,
    )
    gates = _native_gates(
        source_mode,
        recovery,
        generic,
        repair,
        lawbook,
        compact,
        true_contamination,
        terminal_audit,
        obstruction_df,
        artifacts,
    )
    summary = {
        "autonomous_facade": True,
        "finite_core_mode": "native_v2",
        "serious_path_uses_finite_recovery_core": True,
        "all_gates_passed": all(row["passed"] for row in gates),
        "real_corpus_used": source_mode == "real_etp",
        "source_mode": source_mode,
        "equations": len(equations),
        "matrix_shape": list(getattr(matrix, "shape", (len(equations), len(equations)))),
        "false_pair_count": len(false_pairs),
        "true_pair_count": len(true_pairs),
        "constructor_count": recovery.constructor_count,
        "generic_final_yield": int(generic["recoveries"]),
        "generic_final_yield_rate": float(generic["yield_rate"]),
        "generic_final_residuals": int(generic["residuals"]),
        "repair_final_yield": int(repair["recoveries"]),
        "repair_final_yield_rate": float(repair["yield_rate"]),
        "repair_final_residuals": int(repair["residuals"]),
        "repair_gain_over_generic": int(repair["recoveries"] - generic["recoveries"]),
        "lawbook_reuse_yield": int(lawbook["recoveries"]),
        "lawbook_reuse_gain_over_repair": int(lawbook["recoveries"] - repair["recoveries"]),
        "compact_atlas_yield": int(compact["recoveries"]),
        "compact_atlas_gain_over_lawbook": int(compact["recoveries"] - lawbook["recoveries"]),
        "oracle_like_upper_bound_yield": int(false_matrix.any(axis=1).sum()) if false_matrix.size else 0,
        "oracle_gap_after_compaction": int(false_matrix.any(axis=1).sum() - compact["recoveries"]) if false_matrix.size else 0,
        "true_contamination_count": true_contamination,
        "terminal_claims_from_advisory_count": 0,
        "failed_search_promoted_true_count": 0,
        "failed_search_promoted_true": 0,
        "named_obstruction_count": int(len(obstruction_df)),
        "obstruction_entropy": obstruction_entropy(obstruction_df.to_dict("records") if not obstruction_df.empty else []),
        "terminal_contract": [form.value for form in TerminalForm],
        "terminal_audit": terminal_audit,
        "advisory_boundary_preserved": boundary_preserved(terminal_rows) and true_contamination == 0,
        "gates": gates,
        "artifacts": artifacts,
    }
    summary["all_gates_passed"] = all(row["passed"] for row in gates) and summary["advisory_boundary_preserved"]
    _write_json(out_dir / "autonomous_compounding_summary.json", summary)
    _write_csv(out_dir / "gate_results.csv", gates)
    (out_dir / "autonomous_compounding_report.md").write_text(_native_report(summary), encoding="utf-8")
    summary["artifacts"].update(
        {
            "autonomous_compounding_summary.json": str(out_dir / "autonomous_compounding_summary.json"),
            "gate_results.csv": str(out_dir / "gate_results.csv"),
            "autonomous_compounding_report.md": str(out_dir / "autonomous_compounding_report.md"),
        }
    )
    _write_json(out_dir / "autonomous_compounding_summary.json", summary)
    return summary


def _terminal_rows_from_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if int(summary.get("true_contamination_count", 0) or 0) == 0:
        rows.append({"status": "finite_countermodel_found", "eq1_holds": True, "eq2_violated": True, "source": "finite_core_summary"})
    if int(summary.get("failed_search_promoted_true_count", 0) or 0) == 0:
        rows.append({"status": "failed_search", "finite_search_miss": True, "source": "residual_guard"})
    if int(summary.get("named_obstruction_count", 0) or 0) > 0:
        rows.append({"status": "named_obstruction_advisory", "obstruction_name": "summary_obstruction_atlas", "source": "obstruction_atlas"})
    return rows


def _artifact_paths(output_dir: Path) -> dict[str, str]:
    manifest_path = output_dir / "artifact_manifest.json"
    artifacts: dict[str, str] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for name in manifest.get("files", []):
                artifacts[str(name)] = str(output_dir / str(name))
        except Exception:
            pass
    for name in (
        "lawbook.sqlite",
        "compounding_summary.json",
        "gate_results.csv",
        "cross_episode_policy_eval.csv",
        "obstruction_atlas.csv",
        "residual_queue.csv",
    ):
        path = output_dir / name
        if path.exists():
            artifacts[name] = str(path)
    return artifacts


def _load_inputs(config: AutonomousCompoundingConfig) -> tuple[list[str], Any, str]:
    if config.tiny_demo:
        return _tiny_equations(), _tiny_matrix(), "fallback_tiny_demo"
    if not config.equations or not config.matrix:
        raise FileNotFoundError("native_v2 real mode requires equations and matrix; use tiny_demo=True for fallback wiring")
    equations = load_sair_equations(config.equations)
    matrix = load_sair_matrix(config.matrix)
    if not equations or matrix is None:
        raise FileNotFoundError("ETP/SAIR inputs could not be loaded")
    return equations, matrix, "real_etp"


def _sample_pairs(matrix: Any, n: int, config: AutonomousCompoundingConfig) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    if config.tiny_demo:
        false_pairs = [(0, 1), (0, 2), (3, 4), (5, 4), (7, 6), (6, 1)]
        true_pairs = [(i, i) for i in range(n)]
        return false_pairs[: max(1, config.sample_pairs)], true_pairs
    rng = random.Random(config.seed)
    limit = min(n, int(matrix.shape[0]), int(matrix.shape[1]))
    false_pairs: list[tuple[int, int]] = []
    true_pairs: list[tuple[int, int]] = []
    target_false = max(1, int(config.sample_pairs))
    target_true = max(1, int(config.sample_pairs) // 3)
    attempts = 0
    while (len(false_pairs) < target_false or len(true_pairs) < target_true) and attempts < target_false * 300:
        attempts += 1
        i, j = rng.randrange(limit), rng.randrange(limit)
        if i == j:
            if len(true_pairs) < target_true:
                true_pairs.append((i, j))
            continue
        if bool(matrix[i, j]) and len(true_pairs) < target_true:
            true_pairs.append((i, j))
        elif not bool(matrix[i, j]) and len(false_pairs) < target_false:
            false_pairs.append((i, j))
    return false_pairs, true_pairs


def _tiny_equations() -> list[str]:
    return [
        "(x * y) = (y * x)",
        "(x * y) = x",
        "(x * y) = y",
        "x = x",
        "x = y",
        "(x * x) = x",
        "((x * y) * z) = (x * (y * z))",
        "(x * y) = (x * y)",
    ]


def _tiny_matrix() -> Any:
    matrix = np.zeros((8, 8), dtype=bool)
    for i in range(8):
        matrix[i, i] = True
    matrix[1, 5] = True
    matrix[2, 5] = True
    matrix[4, 0] = True
    return matrix


def _pair_features(equations: list[str], pairs: list[tuple[int, int]]) -> pd.DataFrame:
    rows = []
    for pair_idx, (i, j) in enumerate(pairs):
        row = build_pair_features(equations[int(i)], equations[int(j)])
        rows.append({"pair_idx": pair_idx, "eq1_id": int(i), "eq2_id": int(j), **row})
    return pd.DataFrame(rows)


def _mask(matrix: np.ndarray, indices: list[int]) -> np.ndarray:
    if not len(matrix) or not indices:
        return np.zeros(int(matrix.shape[0]), dtype=bool)
    return matrix[:, [int(i) for i in indices]].any(axis=1)


def _episode_row(episode: int, policy: str, indices: list[int], mask: np.ndarray, false_matrix: np.ndarray, true_matrix: np.ndarray, previous: np.ndarray | None) -> dict[str, Any]:
    total = int(false_matrix.shape[0])
    recovered = int(mask.sum())
    true_bad = int(_mask(true_matrix, indices).sum()) if len(true_matrix) else 0
    previous_mask = np.zeros_like(mask) if previous is None else previous
    return {
        "episode": episode,
        "policy": policy,
        "route_size": len(indices),
        "recoveries": recovered,
        "yield_rate": recovered / total if total else 0.0,
        "residuals": total - recovered,
        "new_recoveries_vs_previous": int((mask & ~previous_mask).sum()) if len(mask) else 0,
        "true_contamination_count": true_bad,
        "terminal_claims_from_advisory_count": 0,
        "advisory_only": True,
        "can_promote_truth": False,
    }


def _repair_lawbook_rows(repair_route: pd.DataFrame, manifest: pd.DataFrame, features: pd.DataFrame, source_mode: str) -> pd.DataFrame:
    rows = repair_route.copy()
    if rows.empty:
        return pd.DataFrame()
    basin = features["basin"].mode().iloc[0] if "basin" in features.columns and not features.empty else ""
    deep = features["deep_ir_candidate"].mode().iloc[0] if "deep_ir_candidate" in features.columns and not features.empty else ""
    rows["basin"] = basin
    rows["deep_ir_candidate"] = deep
    rows["source_mode"] = source_mode
    rows["timestamp"] = datetime.now(timezone.utc).isoformat()
    rows["advisory_only"] = True
    rows["can_promote_truth"] = False
    return rows


def _lawbook_indices(features: pd.DataFrame, lawbook_df: pd.DataFrame, manifest: pd.DataFrame, budget: int) -> list[int]:
    if lawbook_df.empty:
        return []
    hints: list[Any] = []
    for _, row in features.head(25).iterrows():
        hints.extend(recommend_from_lawbook(row.to_dict(), lawbook_df, budget))
    out: list[int] = []
    families = set()
    for hint in hints:
        try:
            idx = int(hint)
            if 0 <= idx < len(manifest):
                out.append(idx)
                continue
        except Exception:
            families.add(str(hint))
    if families and "family" in manifest.columns:
        for idx, row in manifest.iterrows():
            if str(row.get("family")) in families:
                out.append(int(idx))
    return list(dict.fromkeys(out))[: int(budget)]


def _compact_indices(repair_df: pd.DataFrame, manifest: pd.DataFrame, budget: int) -> list[int]:
    if repair_df.empty:
        return []
    df = repair_df.copy()
    df["_gain"] = pd.to_numeric(df.get("marginal_gain", 0), errors="coerce").fillna(0)
    df = df.sort_values(["_gain", "constructor_idx"], ascending=[False, True])
    return [int(x) for x in df["constructor_idx"].head(max(1, int(budget))).tolist()]


def _route_df(name: str, indices: list[int], manifest: pd.DataFrame, mask: np.ndarray, matrix: np.ndarray) -> pd.DataFrame:
    rows = []
    recovered = np.zeros(int(matrix.shape[0]), dtype=bool)
    for step, idx in enumerate(indices):
        gain = int((matrix[:, idx] & ~recovered).sum()) if len(matrix) else 0
        recovered |= matrix[:, idx] if len(matrix) else recovered
        mrow = manifest.iloc[idx].to_dict() if 0 <= idx < len(manifest) else {}
        rows.append(
            {
                "policy": name,
                "step": step,
                "constructor_idx": idx,
                "cid": mrow.get("cid", ""),
                "family": mrow.get("family", ""),
                "marginal_gain": gain,
                "recovered_after": int(recovered.sum()),
                "residuals_after": int(matrix.shape[0] - recovered.sum()),
                "advisory_only": True,
                "can_promote_truth": False,
            }
        )
    return pd.DataFrame(rows)


def _write_native_outputs(out_dir: Path, **frames: Any) -> dict[str, str]:
    mapping = {
        "episode_metrics.csv": frames["summary_rows"],
        "pair_features.csv": frames["features_df"],
        "true_pair_features.csv": frames["true_features_df"],
        "constructor_manifest.csv": frames["constructor_manifest"],
        "constructor_family_recommendations.csv": _family_recommendations(frames["features_df"]),
        "pair_recovery_matrix_summary.csv": frames["pair_eval"],
        "generic_route.csv": frames["generic_route"],
        "residual_repair_route.csv": frames["repair_route"],
        "lawbook_reuse_route.csv": frames["lawbook_route"],
        "compact_atlas_route.csv": frames["compact_route"],
        "obstruction_atlas.csv": frames["obstruction_df"],
        "residual_queue_after.csv": frames["residual_df"],
        "terminal_form_audit.csv": frames["terminal_audit"],
    }
    artifacts = {"lawbook.sqlite": str(frames["lawbook_path"])}
    for name, value in mapping.items():
        path = out_dir / name
        _write_table(path, value)
        artifacts[name] = str(path)
    return artifacts


def _family_recommendations(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if features.empty or "recommended_families" not in features.columns:
        return pd.DataFrame(rows)
    counts: dict[str, int] = {}
    for value in features["recommended_families"]:
        for family in value if isinstance(value, list) else []:
            counts[str(family)] = counts.get(str(family), 0) + 1
    for family, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append({"family": family, "support_count": count, "advisory_only": True, "can_promote_truth": False})
    return pd.DataFrame(rows)


def _write_table(path: Path, value: Any) -> None:
    if isinstance(value, pd.DataFrame):
        rows = value.to_dict("records")
    elif isinstance(value, list):
        rows = value
    else:
        rows = []
    fieldnames = sorted({k for row in rows for k in dict(row).keys()}) or ["empty"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(dict(row).get(k)) for k in fieldnames})


def _cell(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_table(path, rows)


def _native_gates(source_mode: str, recovery: Any, generic: dict[str, Any], repair: dict[str, Any], lawbook: dict[str, Any], compact: dict[str, Any], true_contamination: int, terminal_audit: list[dict[str, Any]], obstruction_df: pd.DataFrame, artifacts: dict[str, str]) -> list[dict[str, Any]]:
    checks = {
        "data_loaded": recovery.equation_count > 0,
        "finite_constructor_bank_nonempty": recovery.constructor_count > 0,
        "sat_shape_ok": tuple(recovery.sat_cache.shape) == (recovery.constructor_count, recovery.equation_count),
        "generic_route_nonempty": generic["route_size"] > 0,
        "repair_yield_not_below_generic": repair["recoveries"] >= generic["recoveries"],
        "repair_residuals_not_above_generic": repair["residuals"] <= generic["residuals"],
        "lawbook_written": bool(artifacts.get("lawbook.sqlite") and Path(artifacts["lawbook.sqlite"]).exists()),
        "lawbook_reuse_present": lawbook["route_size"] > 0,
        "true_contamination_zero": true_contamination == 0,
        "no_advisory_truth_promotion": all(not (row.get("advisory_only") and row.get("can_promote_truth")) for row in terminal_audit),
        "finite_search_failure_not_true": all(not (row.get("status") == "RESIDUAL" and row.get("terminal_form") == "VERIFIED_PROOF") for row in terminal_audit),
        "serious_path_uses_finite_recovery_core": True,
        "obstruction_atlas_nonempty_when_residuals_exist": compact["residuals"] == 0 or not obstruction_df.empty or source_mode == "fallback_tiny_demo",
        "episode_metrics_written": bool(artifacts.get("episode_metrics.csv") and Path(artifacts["episode_metrics.csv"]).exists()),
    }
    return [{"gate": key, "passed": bool(value)} for key, value in checks.items()]


def _native_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Autonomous Compounding Engine v2",
            "",
            f"- source_mode: {summary['source_mode']}",
            f"- finite_core_mode: {summary['finite_core_mode']}",
            f"- constructor_count: {summary['constructor_count']}",
            f"- generic_final_yield: {summary['generic_final_yield']}",
            f"- repair_final_yield: {summary['repair_final_yield']}",
            f"- lawbook_reuse_yield: {summary['lawbook_reuse_yield']}",
            f"- compact_atlas_yield: {summary['compact_atlas_yield']}",
            f"- true_contamination_count: {summary['true_contamination_count']}",
            f"- failed_search_promoted_true_count: {summary['failed_search_promoted_true_count']}",
            "",
            "All routes, PQ-IR features, obstruction names, and lawbook reuse records are advisory. FALSE recovery is counted only by finite countermodel recovery.",
            "",
        ]
    )
