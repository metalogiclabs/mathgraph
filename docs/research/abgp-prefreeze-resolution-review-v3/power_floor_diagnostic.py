"""Independent finite-binomial check; no task generation or confirmatory access.

Run: python power_floor_diagnostic.py > power-floor-diagnostic.json
Requires NumPy and SciPy. This calculates ONE paired significance + observed-floor
component, NOT complete A/B/G/P PASS power. G is a max-dose-only special case.
"""
from __future__ import annotations
import json
import math
from fractions import Fraction
from itertools import product
import numpy as np
import scipy
from scipy.stats import binom


def component_power(n: int, q: Fraction, delta: Fraction, floor: Fraction,
                    alpha: Fraction = Fraction(1, 80)) -> float:
    if n < 1 or not (0 < delta <= q <= 1) or not (0 <= floor <= 1):
        raise ValueError("Require n>0, 0<delta<=q<=1 and 0<=floor<=1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0,1)")
    m = np.arange(n + 1)
    # Smallest win count whose one-sided null binomial upper tail is <= alpha.
    critical = binom.isf(float(alpha), m, 0.5).astype(np.int64) + 1
    # Check the critical point instead of relying on a quantile convention.
    assert np.all(binom.sf(critical - 1, m, 0.5) <= float(alpha) + 1e-14)
    eligible = critical > 0
    assert np.all(binom.sf(critical[eligible] - 2, m[eligible], 0.5) > float(alpha))
    a, b = floor.numerator, floor.denominator
    floor_wins = (m * b + n * a + 2 * b - 1) // (2 * b)
    k = np.maximum(critical, floor_wins)
    cond = float((q + delta) / (2 * q))
    return float(np.dot(binom.pmf(m, n, float(q)), binom.sf(k - 1, m, cond)))


def exact_small_reference(n: int, q: Fraction, delta: Fraction,
                          floor: Fraction, alpha: Fraction) -> Fraction:
    probabilities = {-1: (q - delta) / 2, 0: 1 - q, 1: (q + delta) / 2}
    result = Fraction(0)
    for outcomes in product((-1, 0, 1), repeat=n):
        wins, losses = outcomes.count(1), outcomes.count(-1)
        m = wins + losses
        p = sum(Fraction(math.comb(m, k), 2**m) for k in range(wins, m + 1))
        if p <= alpha and Fraction(wins - losses, n) >= floor:
            probability = Fraction(1)
            for value in outcomes:
                probability *= probabilities[value]
            result += probability
    return result


def run() -> dict:
    max_error = 0.0
    cases = 0
    for n in range(1, 7):
        for q in (Fraction(1, 2), Fraction(1)):
            for alpha in (Fraction(1, 4), Fraction(1, 80)):
                delta = Fraction(1, 4)
                actual = component_power(n, q, delta, delta, alpha)
                expected = float(exact_small_reference(n, q, delta, delta, alpha))
                error = abs(actual - expected)
                assert error < 1e-12, (n, q, alpha, actual, expected)
                max_error = max(max_error, error)
                cases += 1
    specs = {
        "A": (4096, Fraction(1, 20), (".05", ".10", ".25", ".50", ".75", "1"), 3),
        "B_component": (1015, Fraction(3, 20), (".15", ".30", ".50", ".75", "1"), 36),
        "P": (4096, Fraction(1, 20), (".05", ".10", ".25", ".50", ".75", "1"), 7),
        "G_max_dose_only": (421, Fraction(3, 20), (".15", ".30", ".50", ".75", "1"), 1),
    }
    arms = {}
    for name, (n, effect, grid, components) in specs.items():
        points = [{"q": float(Fraction(q)), "probability": component_power(n, Fraction(q), effect, effect)} for q in grid]
        minimum = min(p["probability"] for p in points)
        arms[name] = {
            "n_per_component": n, "true_effect": float(effect),
            "observed_floor": float(effect), "alpha": .0125,
            "grid": points, "minimum_on_listed_grid": minimum,
            "significance_and_effect_components": components,
            "union_bound_lower_bound_for_those_components": max(0., 1 - components * (1 - minimum)),
            "complete_arm_pass_power": None,
        }
    return {
        "schema": "abgp.independent-power-floor-diagnostic.v1",
        "status": "DIAGNOSTIC_ONLY_NOT_FULL_PASS_QUALIFICATION",
        "basis": "finite paired Bernoulli model evaluated numerically, not experimental outcomes",
        "numpy_version": np.__version__, "scipy_version": scipy.__version__,
        "small_exact_reference_cases": cases, "small_reference_max_absolute_error": max_error,
        "confirmatory_namespace_used": False,
        "scope": "minimum over explicit finite q grids; no continuum-envelope guarantee; no joint hard-gate power",
        "arms": arms,
    }

if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
