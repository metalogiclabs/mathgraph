from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from math import comb, exp, lgamma, log, log1p
from typing import Any, Mapping

from .manifest import ABGPAnalysisPlan


def _binomial_probability(n: int, k: int, p: float) -> float:
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    log_probability = (
        lgamma(n + 1.0)
        - lgamma(k + 1.0)
        - lgamma(n - k + 1.0)
        + k * log(p)
        + (n - k) * log1p(-p)
    )
    if log_probability < -745.0:
        return 0.0
    return exp(log_probability)


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    max_iterations = 300
    epsilon = 3.0e-14
    fp_min = 1.0e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fp_min:
        d = fp_min
    d = 1.0 / d
    h = d
    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fp_min:
            d = fp_min
        c = 1.0 + aa / c
        if abs(c) < fp_min:
            c = fp_min
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fp_min:
            d = fp_min
        c = 1.0 + aa / c
        if abs(c) < fp_min:
            c = fp_min
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            return h
    raise ArithmeticError("incomplete-beta continued fraction did not converge")


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = exp(
        lgamma(a + b)
        - lgamma(a)
        - lgamma(b)
        + a * log(x)
        + b * log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        value = front * _beta_continued_fraction(a, b, x) / a
    else:
        value = 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b
    return min(1.0, max(0.0, value))


def _binomial_upper_tail_probability(n: int, minimum: int, p: float) -> float:
    if minimum <= 0:
        return 1.0
    if minimum > n:
        return 0.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    return _regularized_beta(p, float(minimum), float(n - minimum + 1))


@lru_cache(maxsize=None)
def _null_critical_wins(discordant: int, alpha: float) -> int | None:
    if discordant <= 0:
        return None
    if _binomial_upper_tail_probability(discordant, discordant, 0.5) > alpha:
        return None
    low = 0
    high = discordant
    while low < high:
        middle = (low + high) // 2
        if _binomial_upper_tail_probability(discordant, middle, 0.5) <= alpha:
            high = middle
        else:
            low = middle + 1
    return low


def _binomial_upper_tail(n: int, minimum: int, p: float) -> float:
    return _binomial_upper_tail_probability(n, minimum, p)


def paired_exact_power(
    n: int,
    p10: Fraction,
    p01: Fraction,
    alpha: Fraction,
) -> float:
    if n <= 0:
        raise ValueError("n must be positive")
    if p10 < 0 or p01 < 0 or p10 + p01 > 1:
        raise ValueError("discordance probabilities must be non-negative and sum to <= 1")
    if alpha <= 0 or alpha >= 1:
        raise ValueError("alpha must lie strictly between zero and one")

    q = float(p10 + p01)
    if q == 0.0:
        return 0.0
    win_given_discordant = float(p10 / (p10 + p01))
    alpha_f = float(alpha)
    power = 0.0
    for discordant in range(n + 1):
        probability_discordant = _binomial_probability(n, discordant, q)
        if probability_discordant == 0.0:
            continue
        critical = _null_critical_wins(discordant, alpha_f)
        if critical is None:
            continue
        conditional_rejection = _binomial_upper_tail(
            discordant,
            critical,
            win_given_discordant,
        )
        power += probability_discordant * conditional_rejection
    return min(1.0, max(0.0, power))


def b_direction_iut_union_bound_power(
    worlds_per_direction: int,
    discordance_rate: Fraction,
    effect: Fraction,
    alpha: Fraction,
    *,
    component_count: int = 36,
) -> dict[str, float | int]:
    """Dependence-agnostic lower bound for B's all-components IUT power.

    The B claim requires every direction-by-control component to reject. We do
    not assume independence among those components. If each has power p, the
    union bound gives P(all reject) >= 1 - m(1-p), where m is the number of
    required components (12 directions x 3 primary controls = 36).
    """

    if worlds_per_direction <= 0:
        raise ValueError("worlds_per_direction must be positive")
    if component_count <= 0:
        raise ValueError("component_count must be positive")
    q = Fraction(discordance_rate)
    delta = Fraction(effect)
    if q <= 0 or q > 1 or delta <= 0 or delta > q:
        raise ValueError("require 0 < effect <= discordance rate <= 1")
    component_power = paired_exact_power(
        worlds_per_direction,
        (q + delta) / 2,
        (q - delta) / 2,
        alpha,
    )
    lower = max(0.0, 1.0 - component_count * (1.0 - component_power))
    return {
        "component_count": component_count,
        "minimum_component_power": component_power,
        "arm_power_lower_bound": lower,
    }


def g_world_blocked_conservative_power(
    n_worlds: int,
    max_dose_discordance_rate: Fraction,
    max_dose_effect: Fraction,
    alpha: Fraction,
) -> float:
    """Worst-case power for world-blocked G with lower doses given zero signal."""

    q = Fraction(max_dose_discordance_rate)
    delta = Fraction(max_dose_effect)
    if q <= 0 or q > 1 or delta <= 0 or delta > q:
        raise ValueError("require 0 < effect <= discordance rate <= 1")
    return paired_exact_power(
        n_worlds,
        (q + delta) / 2,
        (q - delta) / 2,
        alpha,
    )


def _signed_null_distribution(counts: Mapping[int, int]) -> dict[int, int]:
    distribution: dict[int, int] = {0: 1}
    for weight in sorted(counts):
        count = int(counts[weight])
        if weight <= 0 or count < 0:
            raise ValueError("weights must be positive and counts non-negative")
        for _ in range(count):
            nxt: dict[int, int] = {}
            for statistic, ways in distribution.items():
                nxt[statistic + weight] = nxt.get(statistic + weight, 0) + ways
                nxt[statistic - weight] = nxt.get(statistic - weight, 0) + ways
            distribution = nxt
    return distribution


def _signed_alternative_distribution(
    counts: Mapping[int, int], plus_probability: float
) -> dict[int, float]:
    if not (0.0 <= plus_probability <= 1.0):
        raise ValueError("plus_probability must be in [0,1]")
    distribution: dict[int, float] = {0: 1.0}
    minus_probability = 1.0 - plus_probability
    for weight in sorted(counts):
        for _ in range(int(counts[weight])):
            nxt: dict[int, float] = {}
            for statistic, probability in distribution.items():
                nxt[statistic + weight] = nxt.get(statistic + weight, 0.0) + probability * plus_probability
                nxt[statistic - weight] = nxt.get(statistic - weight, 0.0) + probability * minus_probability
            distribution = nxt
    return distribution


def g_conditional_power(
    n_worlds: int,
    max_dose_discordance_rate: float,
    max_dose_effect: float,
    alpha: float,
) -> float:
    """Legacy conditional power for the old world-by-dose randomization."""

    if n_worlds <= 0:
        raise ValueError("n_worlds must be positive")
    q = float(max_dose_discordance_rate)
    delta = float(max_dose_effect)
    if not (0.0 < q <= 1.0) or not (0.0 < delta <= q):
        raise ValueError("require 0 < effect <= discordance rate <= 1")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie strictly between zero and one")

    doses = (0.10, 0.25, 0.50, 1.00)
    weights = (2, 5, 10, 20)
    counts = {
        weight: max(1, int(round(n_worlds * q * dose)))
        for dose, weight in zip(doses, weights)
    }
    plus_probability = (1.0 + delta / q) / 2.0
    null = _signed_null_distribution(counts)
    total_null = 2 ** sum(counts.values())
    running = 0
    critical: int | None = None
    for statistic in sorted(null, reverse=True):
        running += null[statistic]
        if running / total_null <= alpha:
            critical = statistic
        else:
            break
    if critical is None:
        return 0.0
    alternative = _signed_alternative_distribution(counts, plus_probability)
    return min(
        1.0,
        max(0.0, sum(probability for statistic, probability in alternative.items() if statistic >= critical)),
    )


def _paired_arm_audit(
    n: int,
    effect: float,
    discordance_rates: list[float],
    alpha: float,
    minimum_power: float,
) -> dict[str, Any]:
    points: list[dict[str, float]] = []
    for q in discordance_rates:
        if q < effect:
            raise ValueError("paired nuisance discordance must be >= effect floor")
        p10 = Fraction(str((q + effect) / 2.0))
        p01 = Fraction(str((q - effect) / 2.0))
        power = paired_exact_power(n, p10, p01, Fraction(str(alpha)))
        points.append(
            {
                "discordance_rate": q,
                "p10": float(p10),
                "p01": float(p01),
                "power": power,
            }
        )
    minimum = min(point["power"] for point in points)
    return {
        "n": n,
        "effect_floor": effect,
        "points": points,
        "minimum_observed_power": minimum,
        "qualified": minimum >= minimum_power,
    }


def qualification_power_audit(plan: ABGPAnalysisPlan) -> dict[str, Any]:
    qualification = plan.raw.get("qualification")
    if not isinstance(qualification, Mapping):
        raise ValueError("analysis plan lacks qualification power specification")
    minimum_power = float(qualification["minimum_power"])
    alpha = float(qualification["holm_component_alpha_floor"])
    paired = qualification["paired_nuisance_envelope"]
    g_spec = qualification["g_nuisance_envelope"]

    a = _paired_arm_audit(
        int(plan.arms["A"]["n"]),
        float(plan.arms["A"]["effect_floor"]),
        [float(x) for x in paired["A"]["discordance_rates"]],
        alpha,
        minimum_power,
    )

    b_points: list[dict[str, float]] = []
    for q in paired["B"]["discordance_rates"]:
        result = b_direction_iut_union_bound_power(
            int(plan.arms["B"]["worlds_per_direction"]),
            Fraction(str(q)),
            Fraction(str(plan.arms["B"]["effect_floor_each_control"])),
            Fraction(str(alpha)),
            component_count=36,
        )
        b_points.append(
            {
                "discordance_rate": float(q),
                "minimum_component_power": float(result["minimum_component_power"]),
                "arm_power_lower_bound": float(result["arm_power_lower_bound"]),
            }
        )
    b_min = min(point["arm_power_lower_bound"] for point in b_points)
    b = {
        "n": int(plan.arms["B"]["worlds_per_direction"]) * 12,
        "worlds_per_direction": int(plan.arms["B"]["worlds_per_direction"]),
        "component_count": 36,
        "effect_floor": float(plan.arms["B"]["effect_floor_each_control"]),
        "power_model": "direction_iut_union_bound_36_components",
        "points": b_points,
        "minimum_observed_power": b_min,
        "qualified": b_min >= minimum_power,
    }

    p = _paired_arm_audit(
        int(plan.arms["P"]["n"]),
        float(plan.arms["P"]["effect_floor"]),
        [float(x) for x in paired["P"]["discordance_rates"]],
        alpha,
        minimum_power,
    )

    g_points: list[dict[str, float]] = []
    for q in g_spec["max_dose_discordance_rates"]:
        power = g_world_blocked_conservative_power(
            int(plan.arms["G"]["n_worlds"]),
            Fraction(str(q)),
            Fraction(str(g_spec["max_dose_effect_floor"])),
            Fraction(str(alpha)),
        )
        g_points.append({"max_dose_discordance_rate": float(q), "power": power})
    g_min = min(point["power"] for point in g_points)
    g = {
        "n": int(plan.arms["G"]["n_worlds"]),
        "effect_floor": float(g_spec["max_dose_effect_floor"]),
        "power_model": "world_blocked_max_dose_only_worst_case",
        "points": g_points,
        "minimum_observed_power": g_min,
        "qualified": g_min >= minimum_power,
    }

    arms = {"A": a, "B": b, "G": g, "P": p}
    return {
        "minimum_required_power": minimum_power,
        "component_alpha": alpha,
        "arms": arms,
        "qualified": all(value["qualified"] for value in arms.values()),
    }
