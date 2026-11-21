#!/usr/bin/env python3
"""Bounded actual-antecedent stress test for pinned RH CountV / CountVs.

Based on:
  HeightAndVanishing/DirichletPrimeToLPartMulLPowerPart.lean:
    Host, Host.Big, Host.H, Host.X, CaseV, R1, c2, th0, th1
  HeightAndVanishing/Counts.lean:
    CountV := CountShape (CaseV ∧ R1 ≤ 2^c2)
    CountVs := CountShape (CaseV ∧ 2^c2 < R1)
  AutomorphicVarieties/StmtFields.lean: pK, hStar, pOne, Bchi.

This checks a real sequence of DIRICHLET CHARACTER constraints (not an
arbitrary mock boolean predicate). It DOES NOT compute the actual 3-adic
Selmer-group length Vlen, verify a Lean proof, or refute CountV.

Construction:
  χ=PChar.one (conductor 1), q1=11, d=23, e=1, t=2, l=3
  ex=k-2, N=2^k*11*23, k≥12
  ψ_k=even primitive Dirichlet character mod 2^k of order 2^(k-2)
      times quadratic Legendre character mod 11 (odd)
      times the trivial char mod 23.
The even 2-adic component sends generator 5 of (Z/2^k)^×/{±1} to ζ.
All group characters are represented exactly by exponents of ζ; this
works equally in complex roots of unity and in finite extensions of Z_3
once such a root is chosen. Coef existence is supplied in the claimant
by exists_coef. For χ=1: ordC=1, pK=7, hStar=classNo(Q(sqrt(-7)))=1,
pOne=3; this last class-number fact is external classical arithmetic,
not proved by this script. Bchi={3,7}.
"""
from math import gcd, isqrt

def isprime(n):
    return n > 1 and all(n % i for i in range(2, isqrt(n) + 1))

def crt(residues, moduli):
    n = 1
    for m in moduli: n *= m
    return sum(a * (n // m) * pow(n // m, -1, m)
               for a, m in zip(residues, moduli)) % n

def v2(n):
    assert n > 0
    out = 0
    while n % 2 == 0:
        out += 1
        n //= 2
    return out

def check(k):
    q1, d, ell, e, t = 11, 23, 3, 1, 2
    assert isprime(q1) and q1 % 8 == 3
    assert isprime(d) and d % 16 == 7
    assert gcd(q1 * d, 1) == 1   # PrimePair χ.N q1 d
    assert 2 * t + 1 < q1 and 2 * t + 1 < d
    # For χ=1: q=1, ordC=1, pK=7, hStar=1, pOne=3.
    assert all(v < min(q1, d) for v in [1, 1, 7, 1, 3])
    assert k >= 4  # ex=k-2 ≥2
    mod2 = 1 << k
    order = 1 << (k - 2)
    N = mod2 * q1 * d
    assert N == (1 << k) * 253  # Host.N exactly, with χ.N=1
    # 5 generates the +1 mod 4 units modulo 2^k.
    discrete_log = {pow(5, i, mod2): i for i in range(order)}
    assert len(discrete_log) == order
    assert pow(5, order, mod2) == 1
    assert pow(5, order // 2, mod2) == 1 + mod2 // 2
    def phase2(a):
        a %= mod2
        assert a % 2
        if a % 4 == 3: a = (-a) % mod2
        return discrete_log[a]
    def phase(a):
        assert gcd(a, N) == 1
        # Values in the cyclic group <ζ> of order 2^(k-2).
        symbol11 = pow(a % q1, (q1 - 1)//2, q1)
        assert symbol11 in (1, q1-1)
        return (phase2(a) + (order//2 if symbol11 == q1-1 else 0)) % order

    squares11 = sorted({a*a % q1 for a in range(1, q1)})
    squares23 = sorted({a*a % d for a in range(1, d)})
    assert len(squares11) == 5 and len(squares23) == 11
    H = [crt((u2, u11, u23), (mod2, q1, d))
         for u2 in (1, mod2-1)
         for u11 in squares11
         for u23 in squares23]
    assert len(H) == len(set(H)) == 110
    assert all(phase(a) == 0 for a in H)  # Host.IsChar
    assert phase(N - 1) == order // 2     # PsiEven e=1; odd ψ
    assert phase(crt((5, 1, 1), (mod2, q1, d))) == 1  # order ψ
    assert phase2(1 + mod2//2) == order//2  # 2-part has exact conductor 2^k
    # For ell=3, th0 ell ψ=ψ (order is power of 2); comp 2 removes
    # the entire even 2-component, leaving a Legendre-11 char of order 2.
    f0 = 2  # order of 3 in (Z/4Z)^×, since order(th1 3 ψ)=2
    n0 = v2(ell ** f0 - 1)
    assert n0 == 3
    R1 = 16 * 1 * (ell * 1) ** 2 * 4 ** n0
    assert R1 == 9216
    c2 = k  # exact conductor of comp 2 ψ is 2^k
    case = "CountV" if R1 <= 2 ** c2 else "CountVs"
    assert ell == 3 and e == 1 # CaseV: 3∈Bchi for every χ; e=1
    assert case == ("CountV" if k >= 14 else "CountVs")
    print(f"k={k} N={N} |H|={len(H)} char_order={order} "
          f"c2={c2} R1={R1} 2^c2={2**c2} case={case}")
    return case

def main():
    cases=[check(k) for k in range(12, 19)]
    assert cases==["CountVs","CountVs"]+["CountV"]*5
    print("PASS: exact arithmetic Host/character case split, k=12..18")
    print("BOUNDARY: NOT an evaluation of Vlen, Selmer cohomology, or Lean's theorem")

if __name__=="__main__":
    main()
