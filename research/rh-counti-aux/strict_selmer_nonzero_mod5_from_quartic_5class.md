# A live nonzero strict Selmer 5-torsion class in the pinned CountI family

## Result and epistemic boundary

**WARRANTED independently computed arithmetic data** (PARI/GP with
`bnfcertify=1` and log-pinned Galois matrices / local ideal classes)
and bounded exact-congruence tests, at a specific pinned source.
**CANDIDATE independent mathematical deduction** (standard global
class field theory + Hochschild–Serre + local group cohomology):
there is a **nonzero order-5 class in the exact source-defined**
`ShaU` for both q=347 and q=443, with e=3. This has not been
expressed as a Lean proof term or independently reviewed by a
number theorist, so do **not** promote to a formal warrant.
Even if fully confirmed, it is **NOT A COUNTEREXAMPLE TO CountI**:
the theorem permits finite nonzero lengths.

Claimant source:
`CocoSgt/riemann-hypothesis-lean@7cbf7a0c32fca1badf05931879a37c3f8a2b03b4`.

### Exact family under CountI and CorG

Let χ be the primitive trivial base character, l=5, e=3, t=4,
`Host.ex=2`, `Host.q1=q`, `Host.d=167`, where q=347 or 443.
Then `Host.N=16*q*167`, namely **927184** (q=347) or **1183696**
(q=443). Both prime q satisfy q mod8=3; d=167 is prime and
d mod16=7. The source's `Host.Big 4` holds:
`2*t+1=9<min(q,167)` and
the base list `[χ.N=1,ordC=1,pK=7,hStar=1,pOne=3]` is below both.
Let ψ be the quadratic Legendre-q Dirichlet character inflated to
`Host.N`. It is odd since q mod4=3, has order2, and is trivial
on `Host.H` by its square-mod-q condition.
Thus `ψ∈Host.X(c,e=3)` for `Coef 5` with `O=Z_5`.
`CaseI l=5,e=3` holds because `Bchiχ={3,7}`, hence l∉Bchi,
and l−1=4 does not divide 2e=6.

For `GD` choose the **separate auxiliary imaginary quadratic field**
`K_GD=Q(√−7)` (disc −7, class number one), not the real cyclic
quartic field below. Conditions `l≠2,e≥1,Even N`,
`l∤order ψ`, `comp_5(ψ)^2=1`, parity,
`finrank_Q K_GD=2`, `IsTotallyComplex K_GD`,
`5∤7·classNo(K_GD)`, and `gcd(7,N)=1` all hold.
The `GD.eta` noncontainment has an explicit cyclotomic exponent
a≡1 mod5, a≡1 modq and a≡3 mod7; since 3 is a nonsquare mod7, a
fixes the 5-cyclotomic and ψ data yet moves K_GD.
`GD.gen` holds since 4∤6.
Auxiliary CorG primes p=41,p'=43 are distinct and avoid
`30*N*7`. Its subgroup H can be chosen `ker ψ`, so ψ has exactly
that kernel and hence `ψ∈orb(c_5)H` by the pinned `mem_orb`.

The full finite character/CRT audit is [qualified source](../rh-definition-bridge/counti_actual_gd_quadratic_contract.py),
[GitHub Actions #44845733586 PASS](https://github.com/metalogiclabs/mathgraph/actions/runs/44845733586),
job 136664848644: q347 has Host.H 28718 elements and η residue
witness **8676**; q443 has Host.H 36686 and η witness **6646**.
Exact Lean `GD`/field/`Coef` instantiations not compiled.

## Real cyclic quartic field and computational certification

For each q define the totally real cyclic quartic field

```text
L_q = Q(y),   y^4 − 5q y^2 + 5q^2 = 0.
```

Identify it with the fixed field of complex conjugation in
`Q(ζ_5,√−q)` using
`y = √−q(ζ_5−ζ_5^{-1})`; then
`y²=q(3+ζ_5+ζ_5^{-1})`. Its Galois group is cyclic C4.
The automorphism σ that fixes √−q and maps ζ5→ζ5² acts as

```text
σ(y) = y³/q − 3y.
```

**Exact independently certified PARI/GP**:

| q | `Cl(L_q)` | `disc L_q` | `bnfcertify` | `σ` on `Cl(L_q)[5]` |
|---|---|---:|---:|---:|
| 347 | C5 | 15051125 | 1 | multiplication by 2 |
| 443 | C5 | 24531125 | 1 | multiplication by 2 |

The action was **computed** with
`bnrgaloismatrix(bnrinit(B,1), x³/q−3x)` on the certified ordinary
class group. For **both** values of q, PARI/GP found exactly one prime
of `L_q` over each of the rational primes `2,5,q,167`;
`bnfisprincipal` returned **class exponent [0]** for
every such prime ideal. Thus the Hilbert class field `H_q/L_q`
has group C5 and **splits at all primes over 2,5,q,167**.
Its extension is unramified at *every* finite place of `L_q`
by Hilbert class field theory.

Evidence:
- [independent source program](cyclic_quartic_5class_eigenspaces.gp)
- [search over 24 q values](cyclic_quartic_5class_scan.gp), exactly q=347 and443 have 5|class number
- [GitHub Actions #44845791212 — SUCCESS](https://github.com/metalogiclabs/mathgraph/actions/runs/44845791212),
  job **136665050065**, explicitly verified Galois action and
  `bnfisprincipal` for all four rational bad primes, each q;
  [earlier scanned class groups](https://github.com/metalogiclabs/mathgraph/actions/runs/44845264971).

## Cohomological argument for nonzero `ShaU` 5-torsion

Take the source's `O=Z_5`,
`M=Q_5/Z_5`, with 1-dimensional continuous Galois action

```text
θ = ψ⁻¹ · χ_cyc,5⁻³
```

where ψ is Legendre mod q and χ_cyc,5 is the 5-adic cyclotomic
character. The exact source's `Chr.rho 5 3 (Chr.dirG ψ)` has this
action, `M[5]≅F_5(θ mod5)`.

1. θ mod5 is **trivial under global complex conjugation**, since
   ψ(−1)=−1 and ω_5(−1)=−1 with exponent −3. Thus θ factors through
   `Gal(L_q/Q)=C4`. On the chosen generator σ, ψ(σ)=1,
   `ω_5(σ)=2 mod5`, so
   `θ(σ)=2⁻³=2 mod5`. This **exactly equals** the certified action
   of σ on `Cl(L_q)[5]≅F_5`.
2. Hilbert class field theory gives
   `Gal(H_q/L_q)=Cl(L_q)≅C5`. The conjugation action of C4 on
   this group is multiplication by2. Consequently a nonzero
   `C4`-equivariant map
   `Gal(H_q/L_q)→F_5(θ)` exists.
   Hochschild–Serre / inflation–restriction for
   `1→G_{L_q}→G_Q→C4→1` gives a nonzero
   `α∈H¹(G_Q,F_5(θ))`: the obstruction groups
   `H¹(C4,F_5(θ))` and `H²(C4,F_5(θ))` vanish because 4 is
   invertible modulo5.
3. The global character θ has an inertia element at p=5 whose
   action differs from 1 by a 5-adic unit. Hence
   `M^{G_Q}=0`; the long exact sequence
   `0→M[5]→M —5→ M→0` makes the natural map
   `H¹(G_Q,M[5])→H¹(G_Q,M)` injective. Thus the image of α
   is still **nonzero** and has order exactly 5.
4. For each rational prime p not in `{5,q}`, the extension
   `H_q/Q` is unramified, so α restricts trivially on inertia.
   At p=5 and p=q, local inertia in
   `Gal(H_q/Q)` has order dividing 4 (because `H_q/L_q`
   is unramified), so `H¹(I_p,F_5(θ))=0`:
   the class is also inertia-trivial at those primes.
   Thus the image of α in H¹(G_Q,M) restricts to zero at *every*
   finite inertia subgroup.
5. The exact source-defined `shaFam ℚ Ω (5*N)` additionally
   requires local triviality on **decomposition groups** at the
   primes `p∣5*N`, namely `2,5,q,167`. The independent class
   group computation shows all primes over these p have *zero*
   class in `Cl(L_q)`, so `H_q/L_q` splits completely at them.
   Each local decomposition group in `Gal(H_q/Q)` therefore
   injects into C4, of order dividing4; thus
   `H¹(D_p,F_5(θ))=0`. The image of α satisfies these
   additional strict conditions.
6. Therefore the image of α is a nonzero element of
   `ShaU (Chr.rho 5 3 (Chr.dirG ψ)) (5*N) ⊤`.
   In particular its `Z_5`-length is at least one,
   if finite. This is an order-five Selmer class satisfying *the
   source's full local support contract*, not merely class-group
   torsion or the weaker unramified cohomology.

**Admissibility and exactness caveat:** The proof above uses standard
global class field theory, the Galois action on ideal class groups,
finite group cohomology with |C4| invertible modulo5, and the exact
source definitions, but is written **in ordinary mathematics**. The
candidate needs independent arithmetic review and/or direct Lean
terms proving the `ShaU` inclusion before promotion to a formally
WARRANTED nonzero-`Vlen` claim. The GP numerical outputs themselves
and `bnfcertify` are independently qualified.

## Why this is not a contradiction, and next decisive test

`CountI` predicts **finiteness and a polynomial upper bound**, not
vanishing. A single nonzero order-five class does not refute either.
It is precisely a useful **positive lower-bound probe** on the
previously untested actual Selmer measure. To challenge `CountI`,
derive an exact upper bound for these parameters and compute the
entire (not just 5-torsion) `ShaU` length, or construct an infinite
family for which the demanded exponent C cannot exist; any
`Vlen=⊤` example satisfying the full source premises would be
decisive.

Do **not** confuse:
- `K_GD=Q(√−7)`, used to satisfy `GD`, with `L_q`, the cyclic
  quartic cut out by residual θ.
- Actual locally-trivial `ShaU` with unrestricted class-group
  torsion. Here the latter **does** meet local strict conditions,
  as independently checked prime ideals demonstrate.
- Certified arithmetic and hand proof with direct Lean kernel
  verification of the nonzero-`ShaU` assertion.
