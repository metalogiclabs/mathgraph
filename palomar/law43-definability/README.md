# Palomar candidate: swapped-arguments term definability

This directory prepares a Palomar-shaped submission candidate associated with **Metalogic Labs / MathGraph**.

## Mathematical result

For a two-variable magma law `L` whose right-hand side is obtained by swapping variables `0` and `1` in the left-hand side, every magma satisfying `L` admits a **term-defined commutative derived binary operation**.

The derived operation is explicit: evaluate `L.lhs` after substituting the two arguments for variables `0` and `1`.

This is a structural universal-algebra result rather than a single implication edge. It explains why commutativity is term-definable from an entire family of swapped-argument laws.

## Verified source

The Lean theorem was contributed upstream to the Equational Theories Project and merged as:

- repository: `teorth/equational_theories`
- PR: `#1461` — `Prove Law43 term definability from swapped arguments`
- theorem: `Equation43_termDefinableFrom_swapped_args`
- merge commit: `54edcda2f320cef0a241f8109fa164f901a69b87`
- proof contributor: `heathsanchez`

The merged proof constructs the derived operation, proves commutativity using the swap identity and substitution/evaluation compatibility, and supplies the term-definability witness.

## Why this is the lead Palomar candidate

1. It is already machine-checked Lean mathematics in a live research project.
2. It is general: one theorem covers a family of laws rather than a benchmark instance.
3. It has a compact mathematical statement with an explicit construction.
4. It connects directly to MathGraph's focus on extracting reusable structural consequences from verified results.

## Submission discipline

This branch is **preparation only** until provenance and submission-policy checks are complete.

The final package should contain a self-contained, auditable statement surface rather than hiding the claim behind an import. It should also credit the Equational Theories Project and upstream context precisely, and should not claim novelty beyond what can be substantiated.

Planned files:

- `Challenge.lean` — minimal definitions and theorem statement only
- `Solution.lean` — proof with no `sorry`
- `comparator.json` — exact declarations to compare
- `formalization.yaml` — provenance, credits, AI-assistance disclosure, upstream PR
- `lean-toolchain`, `lakefile.lean`, `lake-manifest.json` — pinned replay environment
- CI — Lean build and Palomar-style structural checks

## Parallel original candidate

MathGraph's Stage-2 closure/grammar obstruction work remains the stronger *original* candidate if it can be distilled into a compact Lean theorem pairing a bounded non-reachability result with a positive representation-expansion result. That path should continue in parallel; this Law 43 package is the fastest high-quality route into Palomar's submission format.
