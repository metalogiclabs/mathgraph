# Exact CountI live instance — class-group obstruction and strict Selmer reduction

**Scope:** Independent mathematical argument applied to the exact *definition* of the
claimant's strict Selmer group, not an independent Lean proof of `CountI`,
`CorG`, `VWin`, or RH. The number-field class group is independently
certified by PARI/GP. All uses of global class-field theory and the continuous
cohomology exact sequence below are identified; a term-level Lean replay of
this argument has **not** been run.

## Exact target and field

Claim source: `CocoSgt/riemann-hypothesis-lean@7cbf7a0c32fca1badf05931879a37c3f8a2b03b4`.

- `HeightAndVanishing/Counts.lean`, blob `0d9f87aacf2d53abe43d894c1d822f071599ee57`;
  `GD` and `CorG` quantify over actual `K`, characters and `Vlen`.
- `HeightAndVanishing/DirichletPrimeToLPartMulLPowerPart.lean`,
  blob `1feb420e376868ca41d85fb09bc4f8c7ee66778e`:
  `Vlen Ω c 1 ψ := Chr.V' 5 N 1 (Chr.dirG ℚ Ω ψ)`.
- `CharacterLevelBounds/ShaFamMono.lean`,
  blob `f1b517fa7cddda3e25b5a7ba89c1e57096bbf59e`:
  `Chr.V' l N e ψ` is `Module.length O (ShaU (rho l e ψ) (l*N) ⊤)`;
  `rho l e ψ = twist₂ l (ψ⁻¹ * chiO^(-e))`.
- `GaloisLibrary/SelmerTransport/ConjStableShaFam.lean`,
  blob `578402a7b2aea9f24d31473aab4486dd43055fb2`:
  `shaFam ℚ Ω n` contains *all finite inertia groups* and additionally all
  decomposition groups at primes dividing `n`.
  `ShaU` is the intersection of kernels of restriction in degree-one
  continuous cohomology.

For `χ=PChar.one`, Host `ex=2,q1=59,d=71,N=67024`,
`t=2,e=1,l=5`, let
`ψ` be the quadratic Legendre character modulo 59 inflated to level N.
The arithmetic `Host.X`, `CaseI` and `GD(K=Q(√-7),l=5)` gates
have an independent bounded positive test [CountI/GD witness script](../rh-definition-bridge/counti_actual_gd_quadratic_contract.py).

Put `F=Q(ζ_5, √-59)`. Since the quadratic subfield of `Q(ζ_5)` is
`Q(√5)`, the two extensions are linearly disjoint and `[F:Q]=8`.
`F` is totally complex. A primitive integral generator has
minimal polynomial

```text
x^8+2x^7+239x^6+358x^5+21186x^4+20890x^3+824410x^2+396600x+11915405
```

Independently computed using PARI/GP `nfinit(P)`, `bnfinit(P,1)` and
`bnfcertify` on [script](degree8_class_group.gp) at
[Actions run #44844750688, SUCCESS](https://github.com/metalogiclabs/mathgraph/actions/runs/44844750688),
job `136661598067`:

```text
FIELD_DEGREE=8
DISCRIMINANT=189333765625
CLASS_NUMBER=12
CLASS_GROUP_INVARIANTS=[12]
CERTIFIED=1
FIVE_CLASS_GROUP=TRIVIAL
```

Thus `Cl(F)[5]=0` **unconditionally** within this independent
PARI/GP computational certificate. It is NOT an equality by definition
between class group and `ShaU`.

## Standard-cohomology deduction: the actual strict Selmer group vanishes

Let `O` be any finite torsion-free DVR coefficient ring over `Z_5`
as permitted by `Coef 5`. Let
`M = O⊗_{Z5}(Q5/Z5)`, equipped with scalar action
`θ = ψ⁻¹ χ_cyc,5⁻¹` of `G_Q`. `M` is a discrete 5-primary
divisible module, `M[5]=O/5O` is finite, and the residual action
`θ mod5` factors through `Gal(F/Q)`.

Consider **the source-defined** `S = ShaU(θ,5N,⊤)`, a subgroup of
`H¹(G_Q,M)`. By its `shaFam` definition, any `c∈S` restricts to
zero in `H¹(I_p,M)` for **every finite rational prime p**, including
primes dividing 5N.

**Claim, using classical Galois cohomology and class-field theory:
`S=0` for this exact character.**

1. Every class in `H¹(G_Q,M)` has finite 5-primary order: a continuous
   cocycle from the profinite group `G_Q` to discrete `M` has finite
   image, and every element of `M` is killed by a 5-power. Hence if
   `S≠0`, `S[5]≠0`.
2. Let `c∈S[5]`. The long exact sequence from
   `0→M[5]→M —5→ M→0` gives an element
   `d∈H¹(G_Q,M[5])` mapping to `c`.
3. For each rational prime `p`, the kernel of
   `H¹(I_p,M[5])→H¹(I_p,M)` is a quotient of
   `H⁰(I_p,M)/5H⁰(I_p,M)`. This quotient vanishes:
   - For `p∉{5,59}`, both θ factors are unramified and
     `M^{I_p}=M` is 5-divisible.
   - For `p=5`, ψ is unramified, while inertia in
     `Q(ζ_5)/Q` acts through a unit with reduction modulo 5 not equal
     to 1. Therefore `M^{I_5}=0`.
   - For `p=59`, the quadratic ψ is ramified and sends an inertia
     element to `−1`; the cyclotomic 5-adic factor is unramified
     there. Since `−2∈O^×`, `M^{I_{59}}=0`.
   Consequently `d` restricts to zero on `H¹(I_p,M[5])` at all
   rational primes p; in other words d is unramified everywhere.
4. Restrict d to `G_F`. Its `G_F`-action on `M[5]` is trivial,
   so `d|_{G_F}` is a continuous homomorphism
   `G_F→O/5O`. It is unramified at every finite prime of F,
   hence class-field theory makes it factor through `Cl(F)`.
   But `|Cl(F)|=12`, coprime to 5, so `d|_{G_F}=0`.
   (F is totally imaginary, so no neglected infinite-place ramification.)
5. In the inflation–restriction sequence for
   `1→G_F→G_Q→Gal(F/Q)→1`, the kernel of
   `H¹(G_Q,M)→H¹(G_F,M)` lies in
   `H¹(Gal(F/Q), M^{G_F})`, which is zero because the
   group has order 8, prime to 5, and `M^{G_F}` is 5-primary.
   Thus `c=0`, contradiction to nonzero `S[5]`.
   Therefore `S=0`.

**Consequence if the above standard identification of source's `ShaU`
with these continuous cohomology groups is independently confirmed:**

`Vlen Ω c 1 ψ=0`, for any `Coef 5` containing ±1,
and `Vn Ω c 1 ψ=0`. Thus the actual `CountI` inequality in this
explicit `l=5`, `ψ` test is satisfied with zero left-hand side.

This is a **positive verification control**, not a counterexample.
It is much stronger than a simple congruence witness, but an expert
independent mathematical proof review or a Lean formalization is
still necessary to promote this derived Selmer-vanishing claim to
the same verification status as the PARI/GP class number.

## What this does not prove

- Does not settle `CountI` for all `l`, all primes q,d, all ψ, or
  all fields satisfying `GD`.
- Does not bound the `l`-primary class groups in the infinite family
  `Q(ζ_l,√-q)`; those can be very large.
- Does not establish `CountV` or `VWin` or exhibit a false mathematical
  consequence from the actual claimed RH proof.
- Does not make a computational class-group certificate into an independently
  kernel-checked *theorem term* of the original source.
