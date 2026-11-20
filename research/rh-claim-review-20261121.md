# RH/Dirichlet-GRH actual-claim proof boundary — 2026-11-21

**Status:** bounded static audit WARRANTED; actual RH and GRH proof verification **UNKNOWN**.

## Exact source and evidence

- Claimant mirror: CocoSgt/riemann-hypothesis-lean @ 7cbf7a0c32fca1badf05931879a37c3f8a2b03b4 (mirror states byte-identical to Levent Alpöge's original 14-part archive).
- Toolchain: Lean v4.33.1, Mathlib 0df444a360eaa60ab8c11dca51a86af692955474.
- Our full source import scan: [run #44791340072](https://github.com/metalogiclabs/mathgraph/actions/runs/44791340072), source commit d707d963b9693d97e8efdfa6fdfa2ff20346fc56, [artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/44791340072/artifacts/14655943712). All **175,187 source files** reachable from Main through **753,569 internal import edges**.
- **This is an import graph, NOT the transitive term dependency closure of the RH theorem.** A theorem may import code it never uses.
- Independent full-proof [Comparator verification project](https://github.com/Deicyde/riemann-hypothesis/blob/main/verification/NOTES.md): hosted green CI checks source/archive identity and challenge statements, not the full proof; full proof compilation and independent judging were still in progress as of the retrieved notes.

## Actual proof route (source checked)

Main.riemannHypothesis -> rhOfAll -> allChi -> UpperTheory.FinalTheorems.everyCharacter.

In CharacterBoxes/MainConclusion.lean, everyCharacter is obtained by everyCharacter_of_row applied to UpperTheory.Gal.Int.galoisLocalGlobalStrong_recParameter. The latter is galoisRepresentations_of_thetaLift using UpperTheory.TP.K.tLiftK, then geometric realization and theta lifting.

The other essential branch of everyCharacter_of_row invokes every_character_of_literature_of_vWin with an input Galois row, local Langlands existence and vwin_of_row. That theorem supplies theta-integral agreement, local matching, analytical/published inputs, covolume bounds and window nonvanishing to every_character_of_theta_integrals_local_matching.

The target UpperTheory.EveryCharacter is a genuine global assertion about Mathlib Dirichlet L-functions for Re(s)>1/2. It is not obviously weakened or vacuous on its face.

## Three precise source-review targets — none is a demonstrated RH counterexample

1. **Meaning placeholder:** GlobalTheory.Published.UnusedSlot72 : Prop := True (LocalTypeDictionary/DiscreteSpectrumResidualClassification.lean) is carried as a field called siegelEisensteinSimplePole; a proof in EveryCharacterOfLiteratureOfVWin.lean uses trivial for that field. The slot is indeed formally vacuous. Audit whether a meaningful external mathematical obligation was omitted, whether its downstream consumers rely on it, and whether the actual RH proof needs any such obligation. This is a possible **named-slot-to-mathematical-meaning gap**, not proof unsoundness.

2. **Old vacuous branch versus new substantive branch:** UpperTheory.One.M.Sw : Prop := False and UpperTheory.One.M.TrivialCondition : Prop := True coexist in Foundations/UnitarySphericalFixing/SatakeParameters/SwOn.lean. Old.typeS (s : Sw) := s.elim and Old.nMv (s : Sw) := False.elim s are conditionally true from an uninhabited premise; they prove nothing unconditionally. New.typeS (_s : TrivialCondition) (H : IsRecT h rc) := H.choose_spec.choose_spec.type uses substantive H. The live third-place MNarrow.lean path calls New.typeS; GlobalArtinReciprocityTrivial.lean invokes narrowBig_alt trivial while separately providing RecTExists. **Cannot infer an unsound False elimination into RH from unused imported old theorems.** Check actual theorem-term closure before any promotion.

3. **Proof copying:** Formalism/HermitianCurvature/HermitianCurvatureProofs/CutCptCopy.lean has exactly two source-level addDecl calls (lines 78 and 82) to copy/substitute definitions and theorems under renamed constants. Source does not show new axiom declarations. Only an independent kernel replay of generated declarations can adequately qualify that boundary, particularly given relevant Lean v4.33.1 limitations.

The static scan counted two direct Prop := True aliases and two addDecl sites. It is **not** an exhaustive mathematical-vacuity audit or proof-term/axiom analysis.

## What is already warranted versus not

- **WARRANTED within exact Lean/Mathlib + exporter boundary:** a separately phrased classical Dirichlet-series/analytic-continuation RH proposition is equivalent to Mathlib's RH definition, and an exported 53,456-declaration proof closure passed independent con-ron verified-mode with exactly three axiom records (propext, Classical.choice, Quot.sound). [Run #44788722307](https://github.com/metalogiclabs/mathgraph/actions/runs/44788722307).
- **WARRANTED:** all source files are in the Main import graph, and the three review targets above exist at the pinned source identity.
- **UNKNOWN:** whether Alpöge's full RH/GRH proof compiles and passes the clean challenge Comparator with independent kernels, whether any vacuous branch is a *term-level* dependency of the headline result, and whether every named published-theorem slot preserves the externally intended mathematical obligation.

## Pre-build semantic falsification: Eisenstein pole erasure (2026-11-21)

**WARRANTED — exact source comparison, NOT a theorem proof:** The classical `GlobalTheory.Published.DoublingMethod` proposition in `Development/AbelianVarietyTheory/PublishedTheorems/TwistedTraceFormula/EisRegularAtOfEisPoleLE.lean` and the newer `ResidueKilled.DM` proposition in `Development/WeilBound/RepresentationTheoryGL/EisensteinResidues/AnisotropicGlobalForms/DmOfHyp.lean` match after renaming `DM`, normalizing equivalent notation and replacing precisely one clause:

```lean
-- Earlier DoublingMethod conjunct
(V.rank < b → EisPoleLE V (flat V a φ s₁) (((b : ℂ) - V.rank) / 2) 1)
-- Later ResidueKilled.DM conjunct
True
```

This is an actual **obligation weakening**, but its significance depends on the **consumer's required property**. The newer `dm_of_two` constructs the surviving statement from cusp-form rapid decay and Eisenstein continuation, with `trivial` for the removed conjunct. The later `UnitaryGroupThirdPlaceHypotheses.siegelEisensteinSimplePole` slot remains named after the pole result, but has type `UnusedSlot72 := True`.

**REJECTED within TWO INSPECTED CONSUMER ROUTES — hypothesis that the omitted pole condition is required by their proof bodies:** The old `normSq_theta_modGrowth` and new `normSq_theta_modGrowth_nc` tactic bodies are identical after whitespace normalization. The old `globalFormAt_frameLat` and new `globalFormAt_frameLat_nc` tactic bodies are identical after renaming the call to the previous supporting lemma. Their proofs actually discard the old pole conjunct when unpacking `DoublingMethod`, and use continuation/regularity and doubling identities. The dropped pole bound is **not consumed by these two source-verified routes**. This does not prove the bound unnecessary in every other theorem or external mathematical interpretation.

**NEGATIVE CONTROL — target character domain:** `Formalism.HC.PChar` at `.../PrimePairSizeCondition.lean` stores a primitive Dirichlet character and is inhabited (explicit `PChar.one`). `PChar.of` constructs a primitive representative of arbitrary Dirichlet characters, and `UpperTheory.Top.imprimitive` extends the nonvanishing conclusion using the Mathlib factorization and nonvanishing of Euler factors for Re(s)>1/2. No obvious vacuity arises from an empty character type or omission of imprimitive characters. This is a source check, not the independent complete proof replay.

**Residual:** audit other mathematical interfaces for **externally expected** conditions removed as `True`, `False`-guarded historical lemmas actually used in the theorem proof term, and novel estimate edge cases. Obtain independently accepted exact term closure for `UpperTheory.FinalTheorems.everyCharacter` before elevating any statement about RH itself. Classify the pole replacement as a **documented conditional simplification** for the two inspected consumers, with whole-theorem consequence still **UNKNOWN**.

## 2026-11-21 — falsification of zero-lift and imaginary-quadratic coverage hypotheses

**REJECTED — trivial output lift:** `UpperTheory.TP.IsLift`, defined in `Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/SchurStep.lean`, contains `aut : GlobalTheory.UnitaryBC.IsAutRepU U'`, an actual output automorphic-representation condition, and imposes archimedean weights plus local compatibility. The proof `tLift_of_k` explicitly obtains a nonzero lifted vector `hne`, transports it via `Θ`, and selects `U'` through `ProjEx`. Choosing `U' = ⊥` does not bypass this construction.

**REJECTED — hidden unrestricted CM-field assumption in immediate consumer:** `UpperTheory.TP.W.GoodK` includes `HasK E := ∃ x d, 0 < d ∧ x² = -d`, a genuine restriction: arbitrary CM fields need not contain an imaginary quadratic subfield. However, `UpperTheory.Gal.TP.TwoUpOK` expressly assumes that same property as `hK`, and its `twoUpOK_of_steps` passes `hK` to `TLiftK` explicitly. It is not silently assumed at this handoff. Whether later global reductions are mathematically adequate requires separate examination.

**UNKNOWN — deeper claim meaning:** source facts support an authentic strengthened theorem with restrictive premises; the source audit has not produced a concrete contradiction, loophole, or counterexample to the final RH claim. An independent theorem-term closure and separate kernel acceptance remain necessary.

## Cheapest decisive next experiment

Obtain the immutable full solution export from the ongoing independent build, verify its exact source and statement hashes against the Mathlib-only challenge, require acceptance by independent kernels and an axiom census, then compute the **actual term-level dependency closure** of UpperTheory.FinalTheorems.everyCharacter. Focus the mathematical review of its **used** slots and guards on the two candidate meaning boundaries above. Do not substitute an import scan for this experiment or claim RH solved before it passes.

All negative findings, former False-guarded routes and unknown boundaries are preserved here; this memo makes no claim against Alpöge's integrity.


## 2026-11-21 — Pre-build quantitative attack and negative controls (source + independent literature)

**Scope/identity**: the candidate proof remains UNKNOWN: source mirror `CocoSgt/riemann-hypothesis-lean@7cbf7a0c32fca1badf05931879a37c3f8a2b03b4`; this is an inspection of definitions, stated theorems and proof bodies, not an independently compiled theorem-term closure.

**WARRANTED (source inspection):** `UpperTheory.Top.VWin` at `src/Development/AutomorphicArithmetic/CharacterBoxes/ExistsPageN.lean` is `∀ ψ : PChar, VWinAt ψ 401`. `VWinAt` quantifies universally over admissible dyadic exponent functions; provides a window in which `VVle E t B` bounds Sha/cohomology terms for each `IsChiField` field. The source also contains `exists_pageN` for dyadic functions, `ldata_nonempty` for auxiliary Galois cohomology data, and `vvle_iff_shaInv` for choice-independent meaning. We therefore REJECT the provisional attack that the target is true only because these data types are empty. This does not certify all `IsChiField` instances; the source `fieldChi` and `isChiField` supply further conditional constructions.

**WARRANTED (source inspection):** `pair_exists` obtains primes from counted nonempty candidate sets; `pair_share` combines relative Stage1/Stage2 good-set estimates; `stage` uses `meanSqK`, `count_bad`, `bad_share`, and `box_of_S`. `count_bad_core` requires a global count of primitive L-functions with a zero in `Re(s)>399/400`, `|Im(s)|≤Q`, conductor≤Q; the submitted source proves this via `ZD.zero_density_box` assembled in `CountZAll.lean` with separate mollifier identity, detection, coefficient squares, character correlations and numerical constants. We found no immediate circular appeal to the desired half-plane GRH result; that does not establish independent validity of those lemmas.

**Independent external mathematical benchmark (favorable to source):** Huxley's 1976 *An Imperfect Hybrid Zero-Density Theorem* (Journal LMS, DOI https://doi.org/10.1112/jlms/s2-13.1.53) reports an unconditional aggregate zero-count estimate `O((Q²T)^((12/5)(1−σ)+ε))` for primitive Dirichlet L-functions. At `T=Q`, `σ=399/400` this yields `O(Q^(0.018+3ε))`; taking `ε=1/100` gives `0.048<0.25`, so the source's `O(Q^(1/4))` bound for the *number of distinct primitive characters each having a zero* is considerably weaker. The inference uses that the zero set is contained in the standard critical strip (nonzero functions have no zeros for Re(s)≥1, and the modulus-one edge is handled separately); choose a finite-parameter constant for small Q. This is independent support for the **mathematical assertion**, NOT certification of its Lean proof, all hypotheses, or any other step. Source: https://academic.oup.com/jlms/article-abstract/s2-13/1/53/828057 .

**REJECTED vacuity/circular candidates**:
- `CountZDetect.lean` assumes nontrivial primitive char (conductor>1), but `CountZFinal.lean` handles the modulus-one singleton separately with ≤1 count.
- `PChar.one` witnesses a nonempty primitive-character domain; `PChar.of` and `UpperTheory.Top.imprimitive` explicitly handle imprimitive characters via Euler factors.
- `UpperTheory.TP.TLiftK` assumes `W.GoodK`, with unramified CM extension and constraints at small inert primes. `TwoUpOK` *itself* includes corresponding unramified/`InertOK` antecedents, and `twoUpOK_of_steps` explicitly obtains `GoodK` before invoking the lift. Treating this theorem as unconditional for an arbitrary CM field would be a scope error, but this immediate source consumer does not make it. Remaining global base-change/descent still UNKNOWN until independently qualified.
- `TopWin.lean` explicitly reduces the Chebyshev window inequality to a nonvanishing statement through `FormBAt` and a Landau-style lemma, not a direct unsupported assumption `ZeroFreeAll`.

**Highest-leverage residual:** The 2/3-local `BoundAtTwoThreeFamilyFonAlt` and `VWin` interface/meaning, the genuinely novel counts `CountI/II/III/V` used to establish the final window, and the Galois/CM-descent route from restricted `TLiftK` to unrestricted `Row0b`. A falsifying example must satisfy all theorem antecedents; an import of a vacuous old theorem or a restriction *that is actually discharged* is not enough. No proof-breaking counterexample found in these inspected source boundaries. Claim full RH/GRH proof UNKNOWN pending pinned complete build, independent kernel check and theorem-term closure.


## 2026-11-21 — External solution export and certificate-scope audit

**Independent reported artifact (not yet MathGraph-replayed):** The independent [Deicyde verification notes](https://github.com/Deicyde/riemann-hypothesis/blob/main/verification/NOTES.md) now report Andrew Sutherland's full *solution export* of 61,570,595,788 bytes, SHA-256 `5ea74b912147c5c93cc2b6d70cc727cf908df2f62ac6a20480a3fa02f6be244e`. The checksum is a **reported boundary**, not an artifact hash independently recomputed by MathGraph. The Comparator judgment in those notes remained **in progress**.

**External checker qualification:** The notes document con-ron and con-leche each returning code 2 (decline, not reject) on a mutual inductive containing `FunctorialResolution.EmbeddedResolution.PrincipalizationCertificate` and `OrderCertificate`. Both systems' declines were reproduced on a smaller mutual-reflexive example; they must not be presented as evidence the RH claim is false. Lean paranoid and nanoda are planned in the revised Comparator configuration; check their eventual actual verdicts independently. The relevant declaration was directly inspected in `src/Development/ResolutionOfSingularities/EmbeddedResolution/IdealPrincipalization/PrincipalizationCertificate.lean` at the pinned mirror source.

**REJECTED candidate: unconditional 'principalization certificate' at multiplicity≥2 implies an invalid downstream guarantee.** The inductive constructors `PrincipalizationCertificate.large` and `OrderCertificate.large` require only `2 ≤ m` and `2 ≤ μ`, respectively, without geometric data. That is a genuine *conditional vacuity* of the certificate semantics at high multiplicity. However `OpenImmersionRestriction.orderOneCentersIsolated_of_principalizationCertificate` consumes the certificate to conclude `OrderOneCentersIsolated` and its proof passes the high-multiplicity constructors through `orderOneCentersIsolated_of_two_le`; the target property is explicitly a multiplicity-*one* isolation condition. Therefore no contradiction has been demonstrated from this source path. Do not interpret the certificate alone as generic principalization at arbitrary multiplicity.

**Status:** Independently validated mathematical statement for one published zero-density estimate (subject to usual finite-range/critical-strip qualifications); source-level VWin and CM lifting scope checks do not show a fatal defect; actual headline RH/GRH exported proof checking still **UNKNOWN**.



## 2026-11-21 — TARGETED GLOBAL DESCENT AUDIT: theta-lift restrictions, quadratic towers, and index-two patching

**Scope:** source mirror `CocoSgt/riemann-hypothesis-lean@7cbf7a0c32fca1badf05931879a37c3f8a2b03b4`. This is an independent *source-level hypothesis/accountability audit* plus bounded arithmetic tests, NOT an independent Lean/kernel check. Headline RH and GRH remain CANDIDATE (not WARRANTED). No mathematical counterexample was found at the inspected interfaces.

### Explicit chain (source-grounded)
1. `UpperTheory.TP.TLiftK` in `src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/HalfIndexLattices/TLiftK.lean` restricts the theta-lift to a `W.GoodK` package: CM extension, a purely imaginary quadratic generator, everywhere-unramified extension of rings of integers over the maximal real subfield, additive-character conditions, and constraints at nonsplit finite places. Its consumer `twoUpOK_of_steps` at `.../ThetaParseval/TwoUpOKOfSteps.lean` *explicitly* constructs `GoodK` from `BaseNG`, `HasK` and the `InertOK` predicate. The restriction is not lost there.
2. `TwoUpOK` in `.../ThetaParseval/AllCoreOf.lean` retains four nontrivial premises: everywhere-unramified CM extension, `HasK`, even degree of the maximal real subfield, and `InertOK`. `AllCoreQ` in `.../ThetaParseval/CoreAtQIffRowQ.lean` applies the even-rank theorem only after extracting premises from `GlobalTheory.Row9.FieldOK` plus explicit `InertOK`; odd ranks are a separate branch.
3. `GlobalTheory.Row9.FieldOK l E` at `src/Development/AbelianVarietyTheory/Definitions/GaloisGeometry/IsRegAlgTwistOfHalfIntegral.lean` includes imaginary quadratic generator, even real degree, everywhere unramified CM extension, complete splitting at primes dividing `l`, and *three pairwise `Apart` primes above `l`*. `joinUp_of'` in `.../CrystallineDescent/BadFinite.lean` does not silently assert this for arbitrary E: it constructs two real quadratic steps, then an auxiliary CM field through `Quad2Ex`, building `FieldOK` and `InertOK` before `joinGL_holds`.
4. The three-prime supply is not mere counting: `ThreeApart` in `.../InertiaQuadraticRamification/ThreeApartOf.lean` and its proof `threeApart_of double apartUp` starts from two `Apart` primes in the first quadratic step, splits one of those in a second step, lifts the other, then transports `Apart` through further CM extensions. `Step0` includes genuine local decomposition-group fixedness at finite forbidden primes. This is not vacuous at the immediate consumption site.
5. `Quad2Ex` is supplied by `UpperTheory.Gal.Int.Core.exists_quadratic_CM_ext_split_at` in `.../CrystallineDescent/ExistsQuadraticCMExtSplitAt.lean`: the constructed `Q=Y(√(-p))` uses congruence/square and prescribed-splitting constraints to give `Step2`; `Step2` explicitly contains `Step1`, `InertOK`, and the local `UsPl d` predicate. Individual number-theoretic lemmas here are not independently proved by this audit.
6. `PatchOne` at `.../CrystallineDescent/PatchOne.lean` takes an infinite set of quadratic extensions and attached, semisimple representations with a *fixed original* Satake datum, transports their groups to sign-character kernels, proves conjugation and intersection trace compatibility from common Frobenius data, and invokes `GlobalTheory.IndexTwoPatch.main`.
7. `GlobalTheory.IndexTwoPatch.main` is defined/proved in `src/PositivityTheory/AutomorphicForms/PublishedInputs/RealGaloisRepresentations/IwahoriSphericalTransfer/EqOneOrEqOfKer.lean` (blob `2d2a78b5f0ccc6a41008af1f2692a61c76ccc750`). Its nonvacuous prerequisites are infinite *injective* sign chars with open kernels, continuous semisimple reps on those kernels, trace conjugacy invariance, and equality on all intersections. It produces continuous semisimple global ρ whose traces agree for all members of a cofinite subset. Source checks: it explicitly constructs each index-two extension, excludes finitely many self-twist characters, and uses a twisted-intertwiner obstruction to propagate compatibility. The even more local theorem `GlobalTheory.IndexTwoExt.main` in `.../Proofs/GlobalInterpolation/ExistsExtensionRepIndexTwoOfTraceInvariant.lean` constructs and normalizes a commuting matrix square root, rather than postulating extension as a new axiom.
8. `stepDown_of` in `.../CrystallineDescent/JoinEndHolds.lean` uses the patched ρ and `IsoOne` to recover conditions at any requested place from an auxiliary quadratic extension *chosen outside the cofinite exceptional set*. Thus its output is not merely an arbitrary unrelated ρ with no local attribution. `RowCsd` then carries the result back to the unrestricted target. The later `Row0 → Row0b` projection in `.../TypeConditions/WeightsConjBis.lean` only forgets stronger local conditions; it does not introduce a new universal Galois representation from nothing.

### Independent bounded arithmetic witness; NOT Lean certification
For the specific number field `E = Q(i, √7, √5)` with maximal totally real subfield `F = Q(√7, √5)`, and prime `l=29`:
- `[F:Q]=4` is even, and `i² = -1` gives `ImQ E 1`.
- By the biquadratic discriminant formula, `disc Q(i,√7) = disc Q(i) * disc Q(√7) * disc Q(√−7) = (−4)*28*(−7) = 784 = 28²`; hence `Q(i,√7)/Q(√7)` is unramified at all finite primes. Unramifiedness persists under the base extension `F/Q(√7)`, giving `E/F` everywhere-unramified at finite primes.
- `i` lies in the relevant completions of `F` at every prime over 2,3,5,7: `−7≡1 mod8` at 2; `−5≡1 mod3` at 3; `−1≡4 mod5` at 5; and `−5≡2 mod7` (2 a square) at 7. Thus all primes over 2 and 3, and all primes where `F/Q` can ramify (2,5,7), split in `E/F`. Any nonsplit prime has residual absolute norm >3 and is not ramified in `F/Q`, satisfying the three clauses of source-defined `InertOK`.
- At 29: `6²≡7`, `11²≡5`, and `12²≡−1 (mod29)`. Thus 29 splits completely in `F` (4 distinct primes) and in `E/F`; choose 3 primes over distinct real primes to satisfy `Apart`. Hensel also gives `SqAt 1 29` as defined in `.../Definitions/GaloisGeometry/ApartAllEmpty.lean`.
- All numerical congruence and discriminant identities above were independently evaluated in Python/Sympy on 2026-11-21. The deductions via discriminants, local number fields and splitting are standard mathematics, **not translated into a Lean proof or independently checked against exact field instances**. This is evidence against vacuity of the *joint arithmetic premises*, not evidence the full RH theorem is correct.

### Decisions
**REJECTED at exact source boundaries:**
(A) `TLiftK` assumed for arbitrary CM fields; (B) no actual three-prime existence; (C) patching from completely unrelated incompatible representations; (D) vacuity of simultaneous `FieldOK+InertOK+SqAt` conditions in number theory.

**UNKNOWN:** mathematical fidelity and independent proof terms for deeply nested number-field local lemmas (`nonsplit_of_sqrt_conductor`, real quadratic tower existence, `IsSplitAt` correspondence), the Galois attachment `CoreUd`, `IndexTwoPatch.main` and its imported lemmas. The arithmetic example and source inspection do not qualify proof terms. Full independently accepted claim remains UNKNOWN, per [Deicyde verifier notes](https://github.com/Deicyde/riemann-hypothesis/blob/main/verification/NOTES.md).

**Next cheapest decisive experiment:** extract and independently compile/check the narrow `ExistsQuadraticCMExtSplitAt` theorem with its exact definitions and dependencies; or replay `GlobalTheory.IndexTwoPatch.main` and `PatchOne` in an independent kernel with explicit axiom and source hashes. Do not claim RH proof validated before the complete root theorem checks and statement meaning bridges pass.

## 2026-11-21 — Final Galois/local correspondence quantifier check

**Exact source:** claimant mirror `CocoSgt/riemann-hypothesis-lean@7cbf7a0c32fca1badf05931879a37c3f8a2b03b4`.

- `UpperTheory.GalStar.Row0b` at `Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/TypeConditions/WeightsConjBis.lean` quantifies over all CM number fields `E`, prime `l`, ranks `a≥1`, and cuspidal `π` satisfying `IsRegAlg` and `PolarizedPair`. It asserts an existential continuous **semisimple** Galois representation `r`, Hodge–Tate weights, and local compatibility conditions. The conditional restriction on `π` is mathematically substantive; it must be discharged by the downstream construction, not ignored.
- `Row0.row0b` consumes a full `Row0` and projects `Props` to `PropsB` by weakening the tame-place hypothesis from `IsQp` to `IsQpBig`. It does not manufacture an arbitrary new Galois representation or erase continuity/semisimplicity.
- `IsRecT h rc` at `Foundations/LocalLanglands/IsRecTOfIsRec.lean` is an existential local Artin map with explicit `LawsT` conditions (dimension, characters, Langlands multisegments, cuspidality, twists, central character, duality, injection, depth and type). `UpperTheory.Zero.LLC.recTExists` at `Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean` explicitly constructs `a` and `rc`, plus the stated laws. `MainConclusion.everyCharacter_of_row` passes this witness alongside `Row0b`, avoiding a vacuous reliance on an uninhabited local correspondence *at the stated source level*.
- The direct proof of `everyCharacter` is the composition `everyCharacter_of_row galoisLocalGlobalStrong_recParameter`; the statement `UpperTheory.EveryCharacter` is the genuine nonvanishing claim for **all** Dirichlet characters in `Re(s)>1/2` outside the pole.

**Decision: REJECTED (source-level) as a purported defect:** claim that `Row0b` merely asserts existence of an unrelated representation, or that the local correspondence premise is never furnished. **Still UNKNOWN:** whether any imported lemma's *actual compiled proof term* is sound, axiom-free within declared boundary, or mathematically specification-faithful. The next decisive work is a pinned independent check of `ExistsQuadraticCMExtSplitAt` and `IndexTwoPatch.main`, plus full `Main` proof-term dependency and axiom closure; the external verification notes have reported a solution export hash but not a successful final independent verdict.


## 2026-11-21 — Index-two patching finite-family countermodel

**Objective:** falsify the claim that pairwise trace compatibility of index-two kernel representations *alone* ensures global semisimple gluing; determine whether the actual theorem retains the needed extra hypotheses.

**WARRANTED countermodel of the deliberately weakened FINITE variant (NOT the claimant's theorem):** Let G=(Z/2Z)^2 and take its three distinct nontrivial sign characters eta1, eta2, eta3. Their index-two kernels H1, H2, H3 intersect pairwise in the identity subgroup, so any one-dimensional local character assignments agree on intersections. Assign the trivial representation to H1 and H2 and the nontrivial one to H3. Any global one-dimensional representation trivial on H1 and H2 would be trivial on G, contrary to its required restriction at H3. Thus pairwise compatibility and semisimplicity are insufficient for three patches.

**Executable exhaustive test, with green CI:** [model script](https://github.com/metalogiclabs/mathgraph/blob/e243ac996a9eeba592c7d6b18db69741112c07a2/research/rh-definition-bridge/index_two_patch_rank_one_model.py), [Actions run 44810760237 — SUCCESS](https://github.com/metalogiclabs/mathgraph/actions/runs/44810760237), job 136546396398, script commit e243ac996a9eeba592c7d6b18db69741112c07a2 and workflow commit 71945b5a4db1e79ea79f62d1a8887d757a72e81e. Combinatorial model only, not a Lean proof or proof of RH. Exact job counts:

| Group | Distinct sign characters | Pairwise-compatible assignments | Not globally gluable |
|---|---:|---:|---:|
| C2^2 | 2 | 12 | 0 |
| C2^2 | 3 | 8 | 4 |
| C2^3 | 2 | 168 | 0 |
| C2^3 | 3 | 336 | 56 |
| C2^3 | 4 | 280 | 0 |
| C2^3 | 5 | 168 | 0 |

Additional model test: the incompatible three-character seed on C2^3 admits no compatible fourth local character for any of the four unused sign characters. This illustrates how an infinite family may exclude finite gluing obstructions.

**Why this DOES NOT refute the actual theorem:** Source [GlobalTheory.IndexTwoPatch.main](https://github.com/CocoSgt/riemann-hypothesis-lean/blob/7cbf7a0c32fca1badf05931879a37c3f8a2b03b4/src/PositivityTheory/AutomorphicForms/PublishedInputs/RealGaloisRepresentations/IwahoriSphericalTransfer/EqOneOrEqOfKer.lean) explicitly requires an INFINITE index set, INJECTIVE quadratic characters with open kernels, and continuous semisimple local representations with conjugation-invariant and pairwise-compatible traces. It chooses an auxiliary character outside a finite self-twist obstruction set. [PatchOne](https://github.com/CocoSgt/riemann-hypothesis-lean/blob/7cbf7a0c32fca1badf05931879a37c3f8a2b03b4/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/CrystallineDescent/PatchOne.lean) constructs the infinite subtype from distinct quadratic subfields using SignChar.main, and separately passes IsoOne, OneTower and OneConj.

**Degree-one prime nonvacuity:** AttOne is an eventual-cofinite implication restricted to primes w whose absolute norm is a rational prime. This is not vacuous because the source [IsoOne](https://github.com/CocoSgt/riemann-hypothesis-lean/blob/7cbf7a0c32fca1badf05931879a37c3f8a2b03b4/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/CrystallineDescent/IsoOne.lean) explicitly consumes ChebotarevDegreeOne.dense to derive a dense set of such Frobenius elements. [OneTower](https://github.com/CocoSgt/riemann-hypothesis-lean/blob/7cbf7a0c32fca1badf05931879a37c3f8a2b03b4/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/CrystallineDescent/OneTower.lean) proves degree-one norms survive base extension and finite exception sets pull back.

**Decision:** REJECTED applying finite-family gluing counterexample to the actual INFINITE theorem. WARRANTED the finite-model result and negative controls in its declared computational boundary. UNKNOWN still: independent proof-term/kernel closure of the full higher-rank index-two theorem, quadratic CM existence and root RH/GRH claim.

