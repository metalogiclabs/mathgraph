"""Pure deterministic ranking semantics for advisory discovery candidates."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


_POLICY_WEIGHTS = {
    "harvest": {
        "certificate": 2.0,
        "obstruction": 0.8,
        "compression": 1.0,
        "projection": 0.6,
        "reuse": 1.6,
        "novelty": 0.4,
        "cost": 1.2,
        "duplicate": 1.0,
        "overfit": 0.8,
        "foreign": 1.0,
    },
    "frontier": {
        "certificate": 0.8,
        "obstruction": 1.8,
        "compression": 1.8,
        "projection": 1.0,
        "reuse": 0.8,
        "novelty": 1.5,
        "cost": 0.8,
        "duplicate": 0.7,
        "overfit": 0.9,
        "foreign": 0.8,
    },
    "architectonic": {
        "certificate": 0.6,
        "obstruction": 1.0,
        "compression": 1.7,
        "projection": 2.0,
        "reuse": 1.5,
        "novelty": 1.2,
        "cost": 0.6,
        "duplicate": 0.8,
        "overfit": 0.8,
        "foreign": 0.7,
    },
    "balanced": {
        "certificate": 1.2,
        "obstruction": 1.2,
        "compression": 1.3,
        "projection": 1.1,
        "reuse": 1.1,
        "novelty": 0.9,
        "cost": 0.9,
        "duplicate": 0.8,
        "overfit": 0.8,
        "foreign": 0.8,
    },
}


@dataclass(frozen=True)
class RankedCandidate:
    """A candidate's deterministic rank data and original sequence position."""

    candidate_id: str
    score: float
    probability: float
    source_index: int


def default_weights(mode: str) -> dict[str, float]:
    """Return an independent copy of the weights for a named taste mode."""

    try:
        return dict(_POLICY_WEIGHTS[mode])
    except KeyError as exc:
        raise ValueError(f"Unknown taste policy mode: {mode}") from exc


def _value(candidate: Mapping[str, object], field: str) -> float:
    return float(candidate.get(field, 0.0))


def score_candidate(candidate: Mapping[str, object], weights: Mapping[str, float]) -> float:
    """Calculate the existing DiscoveryScheduler v0 taste score."""

    projection_value = _value(candidate, "expected_projection_gain") + _value(
        candidate, "expected_bridge_value"
    )
    reuse_value = _value(candidate, "expected_reuse") + _value(
        candidate, "expected_constructor_reuse"
    )
    return (
        weights["certificate"] * _value(candidate, "expected_certificate_value")
        + weights["obstruction"] * _value(candidate, "expected_obstruction_value")
        + weights["compression"] * _value(candidate, "expected_residual_compression")
        + weights["projection"] * projection_value
        + weights["reuse"] * reuse_value
        + weights["novelty"] * _value(candidate, "novelty_score")
        - weights["cost"] * _value(candidate, "verification_cost")
        - weights["duplicate"] * _value(candidate, "duplicate_risk")
        - weights["overfit"] * _value(candidate, "overfit_risk")
        - weights["foreign"] * _value(candidate, "foreign_moisture_risk")
    )


def softmax(scores: Sequence[float], beta: float) -> list[float]:
    """Return numerically stable softmax probabilities in input order."""

    if not scores:
        return []
    scaled = [float(beta) * score for score in scores]
    shift = max(scaled)
    exps = [math.exp(value - shift) for value in scaled]
    total = sum(exps)
    if total <= 0:
        return [1.0 / len(scores) for _ in scores]
    return [value / total for value in exps]


def rank_candidates(
    candidates: Sequence[Mapping[str, object]],
    *,
    weights: Mapping[str, float],
    beta: float,
) -> list[RankedCandidate]:
    """Score and rank candidates with the scheduler's deterministic tie order."""

    scores = [score_candidate(candidate, weights) for candidate in candidates]
    probabilities = softmax(scores, beta=beta)
    ranked = [
        RankedCandidate(
            candidate_id=str(candidate.get("candidate_id", "")),
            score=score,
            probability=probability,
            source_index=index,
        )
        for index, (candidate, score, probability) in enumerate(
            zip(candidates, scores, probabilities)
        )
    ]
    ranked.sort(
        key=lambda row: (-row.probability, -row.score, row.candidate_id, row.source_index)
    )
    return ranked


__all__ = [
    "RankedCandidate",
    "default_weights",
    "rank_candidates",
    "score_candidate",
    "softmax",
]
