#!/usr/bin/env python3
"""Arithmetic control for why hTP cannot be deleted from a CM descent lemma.

Proposed fields (mathematical interpretation):
 Y = Q(i, sqrt(5)); Q = Y(sqrt(-1007)) = Q(i, sqrt(5), sqrt(1007));
 Q+ = Q(sqrt(5), sqrt(1007)).
Finite computations confirm the congruence and p=19 residue behavior. The
local-field inference (a ramified quadratic over Q_19 composed with the
unramified Q_19(i)) is mathematical reasoning, NOT certified by this code.
"""


def prime(n: int) -> bool:
    return n >= 2 and all(n % k for k in range(2, int(n**0.5) + 1))


def legendre(a: int, odd_prime: int) -> int:
    z = pow(a % odd_prime, (odd_prime - 1) // 2, odd_prime)
    return 0 if z == 0 else 1 if z == 1 else -1


def main() -> None:
    p1, p2, q, c = 19, 53, 5, 6
    p = p1 * p2
    assert prime(p1) and prime(p2) and p1 < p2
    assert c > 0 and c % 2 == 0 and c % 3 == 0
    assert (-p - 1) % (8 * c) == 0  # exact source divisibility
    assert p % p1 == 0 and (p // p1) % p1 != 0
    assert legendre(q, p1) == 1  # sqrt(5) belongs to Q_19 by Hensel
    assert 9**2 % p1 == q
    assert legendre(-1, p1) == -1  # Q_19(i)/Q_19 unramified quadratic
    assert c % p1 != 0
    print(f"p1={p1} p2={p2} p={p} q={q} c={c}")
    print(f"p_plus_one={p+1} modulus_8c={8*c}")
    print(f"legendre_5_mod19={legendre(q,p1)} legendre_minus1_mod19={legendre(-1,p1)}")
    print("PASS: congruence and local residue prerequisites for necessity of hTP")

    # POSITIVE (source-aligned) control for E=Q(i), Y=Q(i,sqrt(5)).
    # In the biquadratic splitting field, the selected Frobenius characters
    # for twoPrimes(s.trans c) and twoPrimes(s.symm) have signatures
    #   p1 : (-1 | p1)=-1, (5 | p1)=-1   [moves i and sqrt(5)]
    #   p2 : (-1 | p2)=+1, (5 | p2)=-1   [fixes i, moves sqrt(5)]
    # It is therefore possible to satisfy both local Frobenius types AND the
    # p1*p2 ≡ -1 (mod 8*c) condition. This is NOT a proof of PrimeWith,
    # the arbitrary-field Chebotarev theorem, or the universal hTP predicate.
    a, b = 23, 73
    m = a * b
    assert prime(a) and prime(b) and a < b
    assert (m + 1) % (8 * c) == 0
    assert legendre(-1, a) == -1 and legendre(q, a) == -1
    assert legendre(-1, b) == 1 and legendre(q, b) == -1
    assert (-m) % 8 == 1 and (-m) % 3 == 1
    print(f"frobenius_positive_p1={a} p2={b} product={m} quotient={(m + 1) // (8 * c)}")
    print("PASS: source-aligned positive Frobenius prime-pair residue control")


if __name__ == "__main__":
    main()
