# Claim Ledger V1 — Minimal Sufficient Interface / Verified Continuation

Purpose: freeze only mathematically supported claims. Every statement is tagged as PROVED-IN-LEAN, FINITE-EXHAUSTIVE, EMPIRICAL, CONJECTURE, or FALSIFIED. Narrative language must translate these claims, not outrun them.

## Core definitions

Let `X` be a state space, `D` a protected semantic codomain, `Γ : X → D` a protected semantic requirement, and `R : X → Z` an interface / representation.

`R` is **Γ-sufficient** iff there exists `h : Z → D` such that `Γ = h ∘ R`.

Equivalently, in ordinary extensional function semantics, `ker R ⊆ ker Γ`.

The canonical quotient is `QΓ := X / ker Γ`.

For set-valued / relational correctness, use an acceptability relation `A(x) ⊆ C`. A block `B` is existentially viable iff `⋂_{x∈B} A(x) ≠ ∅`.

## Ledger

| ID | Claim | Status | Assumptions / boundary | Evidence / target |
|---|---|---|---|---|
| C1 | `R` is Γ-sufficient iff `Γ` factors through `R`. | THEOREM TARGET | Extensional single-valued `Γ`. | Prove in Lean. |
| C2 | `Γ = h ∘ R` implies `ker R ⊆ ker Γ`. | THEOREM TARGET | None beyond function extensionality. | Prove in Lean. |
| C3 | `ker R ⊆ ker Γ` implies existence of a well-defined `h` on the image/quotient of `R`. | THEOREM TARGET | Need exact formulation for non-surjective `R`; define `h` on range or choose representatives classically. | Prove in Lean carefully. |
| C4 | `X / ker Γ` is the unique coarsest informationally Γ-sufficient interface, up to isomorphism / relabelling. | THEOREM TARGET + FINITE-EXHAUSTIVE | Extensional single-valued `Γ`; ordering is refinement of induced equivalence relations. | V41/V43 finite census; formal Lean proof next. |
| C5 | Every strictly coarser-than-`ker Γ` interface has a concrete protected-semantic witness pair that it merges incorrectly. | THEOREM TARGET + FINITE-EXHAUSTIVE | Same assumptions as C4. | V43. |
| C6 | If `Γ_old = h ∘ Γ_new`, then `ker Γ_new ⊆ ker Γ_old`. | THEOREM TARGET + FINITE-EXHAUSTIVE | Cumulative/factorizing requirements. | V43. |
| C7 | Arbitrary capability expansion does NOT imply monotone refinement of the optimal-choice quotient. | FALSIFIED STRONG CLAIM / FINITE-EXHAUSTIVE COUNTEREXAMPLE | Protected semantics = current optimal action only. | V44: finer, coarser, equal, incomparable all occur. |
| C8 | A separator family reconstructs `ker Γ` exactly iff it is sound on Γ-equivalent pairs and complete on Γ-inequivalent pairs. | THEOREM TARGET + FINITE-EXHAUSTIVE | Separator family represented by predicates / maps whose joint kernel is used. | V45. |
| C9 | Counterexample to a quotient licenses arbitrary splitting. | FALSIFIED | None. | V45: unsound-complete separators overfit. |
| C10 | Existential set-valued correctness always has a unique coarsest sufficient interface. | FALSIFIED | Correctness only requires one common admissible action per block. | V46: 6/27 worlds have multiple incomparable coarsest interfaces. |
| C11 | Preserving full acceptable-action profile `A(x)` restores a canonical kernel quotient. | THEOREM TARGET + FINITE-EXHAUSTIVE | Protected semantics is the extensional map `x ↦ A(x)`. | V47/V48. |
| C12 | Under cumulative sound probes, the entire feasible family of sufficient interfaces shrinks monotonically. | THEOREM TARGET + FINITE-EXHAUSTIVE | New probes are added conjunctively; old constraints retained. | V48. |
| C13 | With a complete protected probe family for the target continuation profile, all probe orders converge to the same canonical endpoint. | THEOREM TARGET + FINITE-EXHAUSTIVE | Fixed target protected semantics; cumulative probes. | V48: 343 worlds × 6 orders. |
| C14 | Full protected semantics are necessary for canonical convergence. | FALSIFIED | None. | V49: 343/343 worlds admit a strict-subset probe basis. |
| C15 | A sufficient separator basis is enough to pin the target interface; any superset remains sufficient. | THEOREM TARGET + FINITE-EXHAUSTIVE | Fixed target interface; conjunction of probes. | V49. |
| C16 | The minimum separator basis is unique. | FALSIFIED | None. | V49: 96/343 worlds have multiple minimum bases. |
| C17 | Different learning paths / bases may converge extensionally to the same protected interface. | FINITE-EXHAUSTIVE, THEOREM-SHAPED | Fixed target protected semantics and sufficient accumulated evidence. | V48/V49. |
| C18 | Coarsest informationally sufficient = cheapest computationally sufficient. | NOT GENERALLY TRUE | Requires an explicit cost `c` monotone under refinement. | Must state assumption or use optimization over `c`. |
| C19 | `R* ∈ argmin c(R)` subject to Γ-sufficiency is the correct cost-sensitive formulation. | DEFINITION / OPTIMIZATION FORMULATION | Explicit admissible representation class and cost. | No universal uniqueness claim. |
| C20 | In ARC diagnostic experiments, verified future consequence can outperform local selector heuristics for ambiguous actions. | EMPIRICAL | Specific V31 carrier / source episodes. | V31: 34/35 correct unique separators; 59/60 correct in min-error set. |
| C21 | ARC V32b/V33 show the frozen V23+V26 continuation language is insufficient on most selected held-out diagnostics. | EMPIRICAL / BOUNDED | Bounded carrier and selected tasks only. | V32b/V33. |
| C22 | The abstraction ladder cell→context→object→relation is universally inevitable. | CONJECTURE, TOO STRONG AS STATED | ARC evidence only supports residual-forced lifts in selected diagnostics. | Keep out of theorem core. |
| C23 | Intelligence in general equals minimal sufficient interface discovery. | INTERPRETIVE CONJECTURE | Not a theorem about intelligence. | Philosophical interpretation only. |

## Safe core statement

For fixed extensional protected semantics `Γ`, the canonical informationally minimal sufficient interface is the kernel quotient of `Γ`. Verified evidence can expose that a candidate interface is insufficient; sound and complete separators recover the required protected distinction structure. Under relational / set-valued correctness, canonical uniqueness can fail unless a stronger extensional protected semantics is specified. Cost minimality requires an explicit cost functional.

## Forbidden narrative shortcuts

Do not write any of the following without the listed premise:

- “More capability always requires finer perception.” — false without cumulative/factorizing protected requirements.
- “There is always one minimal sufficient representation.” — false for existential set-valued correctness.
- “A counterexample tells us exactly what distinction to add.” — false; it only proves the current interface is insufficient.
- “Knowing all futures is necessary.” — false; a sufficient separator basis may be much smaller.
- “Coarsest means cheapest.” — only with an appropriate monotone cost assumption.
- “All intelligent agents converge to the same concepts.” — unsupported; only extensional protected structure may converge under fixed semantics.
