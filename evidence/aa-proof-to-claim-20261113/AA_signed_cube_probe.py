"""Exact finite control for the signed/Boolean cube normalization in AA PR #2.

Two genuinely different evaluations of the same 2-variable polynomial:
  p(b) on {0,1}², and f(s) = 2p((s+1)/2)-1 on {-1,1}².
This does NOT prove the universal Mathlib/Lean theorems in PR #2.
"""

from fractions import Fraction
from itertools import product


POINTS = tuple(product((False, True), repeat=2))


def boolean_values(coefficients):
    """Evaluate a + bx + cy + dxy directly on the Boolean cube."""
    a, b, c, d = coefficients
    return {
        bits: a + b * int(bits[0]) + c * int(bits[1])
        + d * int(bits[0]) * int(bits[1])
        for bits in POINTS
    }


def signed_values(coefficients):
    """Evaluate 2p((s+1)/2)-1 using ±1 coordinates independently."""
    a, b, c, d = coefficients
    result = {}
    for bits in POINTS:
        signed_x = Fraction(1 if bits[0] else -1)
        signed_y = Fraction(1 if bits[1] else -1)
        x = (signed_x + 1) / 2
        y = (signed_y + 1) / 2
        p = a + b * x + c * y + d * x * y
        result[bits] = 2 * p - 1
    return result


def variance(values):
    mean = sum(values.values(), Fraction()) / 4
    return sum(((value - mean) ** 2 for value in values.values()), Fraction()) / 4


def influences(values, *, half_difference=False):
    factors = Fraction(2 if half_difference else 1)
    result = []
    for i in range(2):
        influence = Fraction()
        for bits, value in values.items():
            flipped = list(bits)
            flipped[i] = not flipped[i]
            influence += ((value - values[tuple(flipped)]) / factors) ** 2
        result.append(influence / 4)
    return tuple(result)


def run():
    grid = tuple(Fraction(k, 4) for k in (-2, -1, 0, 1, 2))
    count = 0
    for coefficients in product(grid, repeat=4):
        unsigned = boolean_values(coefficients)
        signed = signed_values(coefficients)
        assert all(signed[x] == 2 * unsigned[x] - 1 for x in POINTS)
        assert variance(signed) == 4 * variance(unsigned), coefficients
        assert influences(signed, half_difference=True) == influences(unsigned), coefficients
        count += 1

    # Nontrivial bounded degree-one example, p(x,y) = (x+y)/2.
    selected = (Fraction(0), Fraction(1, 2), Fraction(1, 2), Fraction(0))
    unsigned = boolean_values(selected)
    signed = signed_values(selected)
    assert variance(unsigned) == Fraction(1, 8)
    assert variance(signed) == Fraction(1, 2)
    assert influences(unsigned) == (Fraction(1, 4), Fraction(1, 4))
    assert influences(signed, half_difference=True) == (Fraction(1, 4), Fraction(1, 4))

    # A missing /2 in the signed-cube influence is a factor-four error.
    mutation = influences(signed, half_difference=False)
    assert mutation == (Fraction(1), Fraction(1))
    assert mutation != influences(unsigned)

    print(f"PASS {count}/{count} signed-cube variance and influence transformations")
    print("PASS bounded degree-one example: variance 1/8 -> 1/2, influence 1/4 unchanged")
    print("PASS signed-cube half-difference mutation distinguished: 1/4 -> 1")


if __name__ == "__main__":
    run()
