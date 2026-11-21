# CountI first leaf — independent mod-5 strict Selmer reduction

**Status:** CANDIDATE external mathematical calculation, arithmetic class-number
certificate WARRANTED; **not** a Lean proof, not a falsification of CountI, CorG,
VWin or RH. Exact claimant pin:
`CocoSgt/riemann-hypothesis-lean@7cbf7a0c32fca1badf05931879a37c3f8a2b03b4`.

## Exact object and fixed case

- `UpperTheory.V.HV.Vlen Ω c e ψ := Chr.V' l N e (Chr.dirG ℚ Ω ψ)`
  in `.../HeightAndVanishing/DirichletPrimeToLPartMulLPowerPart.lean`
  (blob `1feb420e376868ca41d85fb09bc4f8c7ee66778e`).
- `Chr.V' l N e ψ := Module.length O (ShaU (rho l e ψ) (l*N) ⊤)`,
  `rho l e ψ := twist₂ l (ψ⁻¹ * chiO ^ (-(e:ℤ)))`
  in `.../CharacterLevelBounds/ShaFamMono.lean`
  (blob `f1b517fa7cddda3e25b5a7ba89c1e57096bbf59e`).
- `QO l O := O ⊗[ℤ_[l]] (ℚ_[l]/ℤ_[l])`,
  `twist₂ := scalRep`; `ShaU` is `LocSel` over `shaFam`,
  where `shaFam` contains every inertia subgroup and also decomposition
  subgroups at primes dividing its numeric argument. [Exact source](https://github.com/CocoSgt/riemann-hypothesis-lean/blob/7cbf7a0c32fca1badf05931879a37c3f8a2b03b4/src/Development/AutomorphicArithmetic/AutomorphicVarieties/GaloisLibrary/SelmerTransport/ConjStableShaFam.lean), blob `578402a7b2aea9f24d31473aab4486dd43055fb2`.
- Take `l=5`, `e=1`, `N=67024=16·59·71`, the quadratic odd
  Dirichlet character `ψ(a)=(a|59)` and the standard `O=ℤ_5`
  coefficient case. Hence the full 5-primary Galois module is
  `A=(ℚ_5/ℤ_5)(θ)` with `θ=ψ⁻¹ χ_cyc,5⁻¹`.
  The strict local family is indexed by `5N`, i.e. prime support
  `{2,5,59,71}`. The global module's *actual* ramification support is
  only `{5,59}` (cyclotomic times quadratic).

## Arithmetic certificate (independently run)

Let `F=ℚ(ζ_5,√(-59))` (a degree-eight abelian extension). Its splitting
field contains `ker(θ mod 5)`. Exact polynomial in [GP script](degree8_class_group.gp):
`x^8+2x^7+239x^6+358x^5+21186x^4+20890x^3+824410x^2+396600x+11915405`.
The script computes

- `[F:ℚ]=8`
- `disc(F)=189333765625=5^6·59^4`
- `Cl(F)≅ℤ/12ℤ`; in particular `Cl(F)[5]=0`
- `bnfcertify(bnfinit(P,1))=1` (unconditional class-group certificate)

[CI run #44844750688 PASS](https://github.com/metalogiclabs/mathgraph/actions/runs/44844750688), job `136661598067`; raw logs independently inspected.

## Independent mathematical reduction (standard class field theory)

Let `x` be any element of order at most five in the *source-defined*
`ShaU(A,5N)`. The exact sequence
`0→A[5]→A -5→ A→0` lifts `x` to some `y ∈ H¹(G_ℚ,A[5])`.
The residual module is `A[5]=𝔽_5(θ̄)`.

**Claim to independently formalize:** the restriction of `y` to `G_F`
is unramified at every finite place. Reason:
1. At every rational `p≠5,59`, `A` is unramified and hence
   `A^{I_p}=A` is 5-divisible. The local long exact cohomology
   sequence makes `H¹(I_p,A[5])→H¹(I_p,A)` injective. The source's
   `ShaU` inertia condition `x|_{I_p}=0` therefore forces
   `y|_{I_p}=0`. This includes 2 and 71 even though they divide `5N`.
2. At `p=5`, the mod-5 cyclotomic factor is nontrivial on inertia
   (surjects onto `𝔽_5ˣ`); the quadratic `ψ` is unramified. At
   `p=59`, `ψ` is ramified of order two while the cyclotomic
   factor is unramified. Thus in both cases `θ̄|_{I_p}≠1`;
   in particular `A^{D_p}=0` (some `θ(g)-1` is a 5-adic unit).
   The source's decomposition-group condition `x|_{D_p}=0`
   and the local long exact sequence imply `y|_{D_p}=0).
3. Therefore `y|_{G_F}` is a continuous unramified
   `𝔽_5`-valued H¹-class, hence factors through
   `Cl(F)` by global class field theory. Since `5 ∤ |Cl(F)|=12`,
   its restriction vanishes.
4. Inflation–restriction is injective
   `H¹(G_ℚ,𝔽_5(θ̄)) → H¹(G_F,𝔽_5)`,
   because `Gal(F/ℚ)` has order 8 prime to 5. Thus `y=0`
   and `x=0`.
5. Since the source coefficient is discrete 5-primary torsion,
   every continuous H¹-class is annihilated by some power of 5
   (continuous cocycles have finite image). Absence of order-five
   elements then gives `ShaU(A,5N)=0`, so `Vlen=0`, `Vn=0`
   **for this fixed `ℤ_5` coefficient and `ψ` only**.

This is a standard-theorem argument with a certified exact number field,
not an executed Lean proof of the last four implications or a direct
enumeration of the source's `H¹`. Promote to WARRANTED exact-source
arithmetic only once the local/global cohomology identifications and the
`O=ℤ_5` coefficient interpretation are checked. No generalization
to all `Coef`, all `l,e,ψ`, or to higher Selmer layers is claimed.

## Evaluation of the alleged problem

The sharp test in this case **does not falsify CountI or CorG**:
the predicted `Vlen` is zero under standard class-field-theoretic
identifications, comfortably satisfying their positive upper bounds.
It *does* reduce an actual nonvacuous source-cohomology case to
a small finite class-group certificate with an explicit proof obligation.
This is more consequential than checking only residue-character booleans.

**Next decisive experiment:** mechanize just the finite-group
inflation–restriction and local restriction lemmas in Lean with the
exact `ShaU` signature, binding the output to the PARI-certified
class number. If that succeeds, test the first conductor with
`5∣h(ℚ(ζ_5,√(-q)))` to obtain nontrivial 5-class input and
seek an exact `Vlen>0` case. No reason yet to infer contradiction.
