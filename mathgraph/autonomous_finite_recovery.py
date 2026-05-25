"""Native finite recovery adapter for autonomous ETP compounding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from mathgraph.magma_constructors import build_base_constructor_bank, build_random_constructor_bank, dedupe_constructors
from mathgraph.sat_cache import build_sat_cache


@dataclass(frozen=True)
class FiniteRecoveryConfig:
    max_n: int = 4
    constructor_limit: int | None = None
    random_seed: int = 1729
    include_base_constructors: bool = True
    include_prior_constructors: bool = True
    include_random_constructors: bool = False
    random_constructor_count: int = 0


@dataclass(frozen=True)
class FiniteRecoveryResult:
    constructors: list[Any]
    constructor_manifest: pd.DataFrame
    sat_cache: np.ndarray
    equation_count: int
    constructor_count: int


def build_finite_recovery_core(equations: list[str], config: FiniteRecoveryConfig) -> FiniteRecoveryResult:
    constructors: list[Any] = []
    if config.include_base_constructors or config.include_prior_constructors:
        constructors.extend(build_base_constructor_bank(max_n=config.max_n, seed=config.random_seed))
    if config.include_random_constructors and config.random_constructor_count:
        per_n = max(1, int(config.random_constructor_count) // max(1, int(config.max_n) - 1))
        constructors.extend(build_random_constructor_bank(max_n=config.max_n, count_per_n=per_n, seed=config.random_seed))
    constructors = dedupe_constructors(constructors)
    if config.constructor_limit is not None:
        constructors = constructors[: max(0, int(config.constructor_limit))]
    cache = build_sat_cache(constructors, equations)
    manifest = _manifest(constructors)
    return FiniteRecoveryResult(
        constructors=list(constructors),
        constructor_manifest=manifest,
        sat_cache=np.asarray(cache.sat, dtype=bool),
        equation_count=len(equations),
        constructor_count=len(constructors),
    )


def evaluate_false_pairs(false_pairs: list[tuple[int, int]], sat_cache: np.ndarray, constructors: list[Any]) -> pd.DataFrame:
    matrix = pair_recovery_matrix(false_pairs, sat_cache)
    rows: list[dict[str, Any]] = []
    for pair_idx, (eq1_id, eq2_id) in enumerate(false_pairs):
        hits = np.flatnonzero(matrix[pair_idx])
        best = int(hits[0]) if len(hits) else -1
        rows.append(
            {
                "pair_idx": pair_idx,
                "eq1_id": int(eq1_id),
                "eq2_id": int(eq2_id),
                "recovered": bool(len(hits)),
                "best_constructor_idx": best,
                "best_constructor_family": constructors[best].family if best >= 0 else "",
            }
        )
    return pd.DataFrame(rows)


def pair_recovery_matrix(false_pairs: list[tuple[int, int]], sat_cache: np.ndarray) -> np.ndarray:
    if not false_pairs:
        return np.zeros((0, int(sat_cache.shape[0])), dtype=bool)
    src = np.asarray([int(i) for i, _ in false_pairs], dtype=int)
    tgt = np.asarray([int(j) for _, j in false_pairs], dtype=int)
    return (sat_cache[:, src] & ~sat_cache[:, tgt]).T


def greedy_route(
    pair_recovery_matrix: np.ndarray,
    constructor_manifest: pd.DataFrame,
    budget: int,
    seed: int = 1729,
) -> tuple[list[int], np.ndarray, pd.DataFrame]:
    return _select_route(pair_recovery_matrix, constructor_manifest, budget, seed, initial_mask=None)


def residual_marginal_repair(
    pair_recovery_matrix: np.ndarray,
    initial_mask: np.ndarray,
    constructor_manifest: pd.DataFrame,
    budget: int,
    seed: int = 1729,
) -> tuple[list[int], np.ndarray, pd.DataFrame]:
    return _select_route(pair_recovery_matrix, constructor_manifest, budget, seed, initial_mask=initial_mask)


def route_metrics(pair_recovery_matrix: np.ndarray, indices: list[int]) -> dict[str, Any]:
    mask = _mask_for(pair_recovery_matrix, indices)
    recovered = int(mask.sum())
    total = int(pair_recovery_matrix.shape[0])
    return {
        "recoveries": recovered,
        "yield_rate": recovered / total if total else 0.0,
        "residuals": total - recovered,
        "mask": mask,
    }


def _select_route(
    matrix: np.ndarray,
    manifest: pd.DataFrame,
    budget: int,
    seed: int,
    initial_mask: np.ndarray | None,
) -> tuple[list[int], np.ndarray, pd.DataFrame]:
    selected: list[int] = []
    recovered = np.zeros(int(matrix.shape[0]), dtype=bool) if initial_mask is None else np.asarray(initial_mask, dtype=bool).copy()
    unavailable: set[int] = set()
    rows: list[dict[str, Any]] = []
    for step in range(max(0, int(budget))):
        best_idx = -1
        best_gain = -1
        for idx in range(int(matrix.shape[1])):
            if idx in unavailable:
                continue
            gain = int((matrix[:, idx] & ~recovered).sum())
            key = (gain, -idx)
            best_key = (best_gain, -best_idx if best_idx >= 0 else 0)
            if key > best_key:
                best_idx = idx
                best_gain = gain
        if best_idx < 0:
            break
        unavailable.add(best_idx)
        selected.append(best_idx)
        recovered |= matrix[:, best_idx]
        row = manifest.iloc[best_idx].to_dict() if len(manifest) > best_idx else {}
        rows.append(
            {
                "step": step,
                "constructor_idx": best_idx,
                "cid": row.get("cid", ""),
                "family": row.get("family", ""),
                "marginal_gain": int(best_gain),
                "recovered_after": int(recovered.sum()),
                "residuals_after": int(matrix.shape[0] - recovered.sum()),
                "advisory_only": True,
                "can_promote_truth": False,
            }
        )
        if best_gain <= 0 and len(selected) >= int(budget):
            break
    return selected, recovered, pd.DataFrame(rows)


def _mask_for(matrix: np.ndarray, indices: list[int]) -> np.ndarray:
    if not indices:
        return np.zeros(int(matrix.shape[0]), dtype=bool)
    return matrix[:, [int(i) for i in indices]].any(axis=1)


def _manifest(constructors: list[Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "constructor_idx": idx,
                "cid": magma.cid,
                "family": magma.family,
                "name": magma.name,
                "n": magma.n,
                "source": magma.source,
                "advisory_only": True,
                "can_promote_truth": False,
            }
            for idx, magma in enumerate(constructors)
        ]
    )
