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

## Cheapest decisive next experiment

Obtain the immutable full solution export from the ongoing independent build, verify its exact source and statement hashes against the Mathlib-only challenge, require acceptance by independent kernels and an axiom census, then compute the **actual term-level dependency closure** of UpperTheory.FinalTheorems.everyCharacter. Focus the mathematical review of its **used** slots and guards on the two candidate meaning boundaries above. Do not substitute an import scan for this experiment or claim RH solved before it passes.

All negative findings, former False-guarded routes and unknown boundaries are preserved here; this memo makes no claim against Alpöge's integrity.
