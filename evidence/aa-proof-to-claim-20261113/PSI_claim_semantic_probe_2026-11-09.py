"""Finite, exact-rational representation controls for an AA claim bridge.

This is NOT a proof of the universal conjecture or of Lean statement fidelity.
It tests two different Boolean-cube encodings and catches a known normalization
mutation using exact arithmetic. No third-party code is imported.
"""

from fractions import Fraction
from itertools import product


def tuple_cube_values(coefficients):
    """Enumerate N=2 as tuples of Booleans, matching Fin 2 -> Bool."""
    a, b, c, d = coefficients
    table = {}
    for x, y in product((False, True), repeat=2):
        table[(x, y)] = a + b * int(x) + c * int(y) + d * int(x) * int(y)
    return table


def tuple_variance_influences(coefficients):
    table = tuple_cube_values(coefficients)
    mean = sum(table.values(), Fraction()) / 4
    var = sum(((value - mean) ** 2 for value in table.values()), Fraction()) / 4
    influences = []
    for i in range(2):
        total = Fraction()
        for bits, value in table.items():
            flipped = list(bits)
            flipped[i] = not flipped[i]
            total += (value - table[tuple(flipped)]) ** 2
        influences.append(total / 4)
    return var, tuple(influences)


def packed_variance_influences(coefficients):
    """Represent the same cube as integers 0..3; bit-flip by XOR."""
    a, b, c, d = coefficients

    def value(index):
        x, y = index & 1, (index >> 1) & 1
        return a + b * x + c * y + d * x * y

    mean = sum((value(i) for i in range(4)), Fraction()) / 4
    var = sum(((value(i) - mean) ** 2 for i in range(4)), Fraction()) / 4
    influences = tuple(
        sum(((value(x) - value(x ^ (1 << i))) ** 2 for x in range(4)), Fraction()) / 4
        for i in range(2)
    )
    return var, influences


def run():
    # Exact truth-table check: every 2-bit polynomial with four coefficients
    # chosen from this fixed rational grid, including unbounded functions.
    grid = tuple(Fraction(k, 4) for k in (-2, -1, 0, 1, 2))
    checked = 0
    for coefficients in product(grid, repeat=4):
        expected = tuple_variance_influences(coefficients)
        observed = packed_variance_influences(coefficients)
        assert observed == expected, (coefficients, expected, observed)
        checked += 1

    # One concrete interval-bounded degree-1 polynomial from the real conjecture.
    p = (Fraction(0), Fraction(1, 2), Fraction(1, 2), Fraction(0))
    variance, influences = packed_variance_influences(p)
    assert variance == Fraction(1, 8)
    assert influences == (Fraction(1, 4), Fraction(1, 4))
    assert max(influences) >= (variance / 1) ** 7

    # Semantic-negative control: an incorrect 2^N denominator (8 vs. 4)
    # changes the influence even though its source still has squared flips.
    wrong_normalization = influences[0] / 2
    assert wrong_normalization == Fraction(1, 8)
    assert wrong_normalization != influences[0]

    # Separate quantifier negative control: the historical conclusion is
    # EXISTS i, not FOR ALL i. The polynomial p=x0 varies, but x1 is inert.
    selective = (Fraction(0), Fraction(1), Fraction(0), Fraction(0))
    selective_variance, selective_influences = packed_variance_influences(selective)
    positive_threshold = selective_variance ** 7
    assert selective_variance == Fraction(1, 4)
    assert selective_influences == (Fraction(1), Fraction(0))
    assert any(inf >= positive_threshold for inf in selective_influences)
    assert not all(inf >= positive_threshold for inf in selective_influences)

    print(f"PASS {checked}/{checked} exact cube-encoding comparisons")
    print("PASS degree-one bounded witness: variance=1/8, influences=(1/4,1/4)")
    print("PASS denominator mutation distinguished: true=1/4, mutant=1/8")
    print("PASS quantifier mutation distinguished: exists=True, forall=False")


if __name__ == "__main__":
    run()
