from __future__ import annotations

from collections import Counter
from fractions import Fraction
from itertools import product
from math import comb
from typing import Any, Mapping, Sequence


_ARM_ORDER = ("A", "B", "G", "P")


def reference_mcnemar(wins: int, losses: int) -> Fraction:
    if wins < 0 or losses < 0:
        raise ValueError("discordant counts must be non-negative")
    n = wins + losses
    if n == 0:
        return Fraction(1, 1)
    return Fraction(sum(comb(n, k) for k in range(wins, n + 1)), 2**n)


def reference_holm(raw_pvalues: Mapping[str, Fraction], alpha: Fraction) -> dict[str, Any]:
    if set(raw_pvalues) != set(_ARM_ORDER):
        raise ValueError("Holm family must contain exactly A, B, G, P")
    if not (Fraction(0, 1) < alpha < Fraction(1, 1)):
        raise ValueError("alpha must be between zero and one")
    order_index = {arm: i for i, arm in enumerate(_ARM_ORDER)}
    ordered = sorted(_ARM_ORDER, key=lambda arm: (raw_pvalues[arm], order_index[arm]))
    adjusted: dict[str, Fraction] = {}
    rejected: dict[str, bool] = {arm: False for arm in _ARM_ORDER}
    running = Fraction(0, 1)
    still_rejecting = True
    m = len(ordered)
    for i, arm in enumerate(ordered):
        p = min(Fraction(1, 1), max(Fraction(0, 1), raw_pvalues[arm]))
        candidate = min(Fraction(1, 1), (m - i) * p)
        running = max(running, candidate)
        adjusted[arm] = running
        threshold = alpha / (m - i)
        if still_rejecting and p <= threshold:
            rejected[arm] = True
        else:
            still_rejecting = False
    return {
        "order": ordered,
        "adjusted_pvalues": {arm: adjusted[arm] for arm in _ARM_ORDER},
        "rejected": rejected,
        "alpha": alpha,
    }


def reference_g_randomization(weights: Sequence[int], observed: int) -> Fraction:
    if any(int(weight) <= 0 for weight in weights):
        raise ValueError("weights must be positive")
    if not weights:
        return Fraction(1, 1)
    favorable = 0
    total = 0
    for signs in product((-1, 1), repeat=len(weights)):
        total += 1
        statistic = sum(int(weight) * sign for weight, sign in zip(weights, signs))
        favorable += statistic >= observed
    return Fraction(favorable, total)


def reference_g_world_blocked(world_scores: Sequence[int], observed: int) -> Fraction:
    """Independent brute-force reference: one sign flip per complete world block."""
    if not world_scores:
        return Fraction(1, 1)
    favorable = 0
    total = 0
    for signs in product((-1, 1), repeat=len(world_scores)):
        total += 1
        statistic = sum(int(score) * sign for score, sign in zip(world_scores, signs))
        favorable += statistic >= observed
    return Fraction(favorable, total)


def run_statistical_reference_audit() -> dict[str, Any]:
    from .analysis import (
        exact_mcnemar_one_sided,
        g_exact_randomization_pvalue,
        g_world_blocked_randomization_pvalue,
        holm_bonferroni,
    )

    max_abs_error = 0.0
    mcnemar_cases = 0
    for wins in range(0, 9):
        for losses in range(0, 9 - wins):
            pairs = [(0, 1)] * wins + [(1, 0)] * losses
            actual = exact_mcnemar_one_sided(pairs)
            expected = float(reference_mcnemar(wins, losses))
            max_abs_error = max(max_abs_error, abs(actual - expected))
            mcnemar_cases += 1

    holm_grid = (
        Fraction(0, 1),
        Fraction(1, 100),
        Fraction(1, 80),
        Fraction(1, 20),
        Fraction(1, 1),
    )
    holm_cases = 0
    for values in product(holm_grid, repeat=4):
        raw = dict(zip(_ARM_ORDER, values))
        expected = reference_holm(raw, Fraction(1, 20))
        actual = holm_bonferroni({arm: float(value) for arm, value in raw.items()}, 0.05)
        if actual["order"] != expected["order"]:
            return {
                "status": "FAIL",
                "reason": "HOLM_ORDER_MISMATCH",
                "mcnemar_cases": mcnemar_cases,
                "holm_cases": holm_cases,
                "g_cases": 0,
                "g_world_blocked_cases": 0,
                "max_abs_error": max_abs_error,
            }
        for arm in _ARM_ORDER:
            max_abs_error = max(
                max_abs_error,
                abs(actual["adjusted_pvalues"][arm] - float(expected["adjusted_pvalues"][arm])),
            )
            if actual["rejected"][arm] != expected["rejected"][arm]:
                return {
                    "status": "FAIL",
                    "reason": "HOLM_DECISION_MISMATCH",
                    "mcnemar_cases": mcnemar_cases,
                    "holm_cases": holm_cases,
                    "g_cases": 0,
                    "g_world_blocked_cases": 0,
                    "max_abs_error": max_abs_error,
                }
        holm_cases += 1

    g_cases = 0
    for weights in ((2,), (2, 5), (2, 2, 5), (2, 5, 10, 20)):
        counts = Counter(weights)
        for observed in range(-sum(weights), sum(weights) + 1):
            actual = g_exact_randomization_pvalue(counts, observed)
            expected = float(reference_g_randomization(weights, observed))
            max_abs_error = max(max_abs_error, abs(actual - expected))
            g_cases += 1

    g_world_blocked_cases = 0
    for scores in ((2,), (2, 5), (7, -3, 4), (37, 37, 37, 37)):
        bound = sum(abs(int(score)) for score in scores)
        for observed in range(-bound, bound + 1):
            actual = g_world_blocked_randomization_pvalue(scores, observed)
            expected = float(reference_g_world_blocked(scores, observed))
            max_abs_error = max(max_abs_error, abs(actual - expected))
            g_world_blocked_cases += 1

    return {
        "status": "PASS" if max_abs_error <= 1e-15 else "FAIL",
        "mcnemar_cases": mcnemar_cases,
        "holm_cases": holm_cases,
        "g_cases": g_cases,
        "g_world_blocked_cases": g_world_blocked_cases,
        "max_abs_error": max_abs_error,
    }
