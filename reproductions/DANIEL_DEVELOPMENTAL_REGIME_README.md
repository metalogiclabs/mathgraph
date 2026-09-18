# Verified developmental regime change — Daniel packet

This is the shortest path through the experiment. The point is not to claim new partition mathematics. The point is to isolate, exactly, a transition in which verifier-certified failure changes the object language available to later construction.

## The question

Let a regime `P` identify states that the current representation cannot distinguish. Its extensional Boolean object language is

`L(P) = 2^(W/P)`.

A verifier can expose an obstruction: two states lie in the same current block but a verified target requires different values. We ask whether that obstruction can determine a conservative new regime `P1` such that

`L(P0) ⊊ L(P1)`,

and whether a later protected target can therefore become formable that was not formable before.

The key distinction is **formability**, not search speed: if a target is not constant on the blocks of `P0`, there is no term for it in `L(P0)`.

## Why there are several versions

The lineage is part of the evidence rather than something to hide.

### V1 — typed regime growth

V1 established strict object-language growth, but the extension candidate (`ExposeDependency`) and targets were hand-authored. That left a staging objection.

### V2 — exhaustive target-independent coordinate selection

V2 removed hand-picked targets by exhausting all 256 Boolean targets and all 65,280 distinct ordered two-episode pairs. But it still supplied the coordinate grammar `Expose(S)`.

An adversarial expansion of that grammar then falsified V2's strongest minimality reading: among the 228 targets classified as needing both raw coordinates, 60 can instead factor through a single derived Boolean channel of `(x,y)`. Thus raw-coordinate minimality was only relative to the supplied coordinate grammar.

That failure is scientifically useful: it says the representation should be identified by the distinctions/quotient it induces, not by the literal feature names used to encode it.

### V3 — coordinate-free quotient refinement

V3 is the surviving Daniel-facing experiment.

The developmental constructor receives only:

1. an 8-state opaque universe;
2. the current parent partition `P0`;
3. verifier conflict edges between states that `P0` identifies but the target separates.

It receives no `x`, `y`, `Expose(x)`, or `Expose(y)` vocabulary.

It exhausts all 225 partitions refining `P0` and selects the unique coarsest refinement separating every verified conflict.

Across all 256 Boolean targets it synthesizes 64 distinct quotient regimes. The result is checked under all 1,152 automorphisms of the base partition: 294,912 exact equivariance checks.

Across all 65,280 distinct ordered two-episode target pairs, 2,324 have strict downstream formability growth:

`f2 ∉ L(P0)` but `f2 ∈ L(P1)`.

Reconstructing the parent regime restores non-formability in every such case.

The executable counts independently agree with closed-form combinatorics.

Run:

```bash
python reproductions/daniel_coordinate_free_refinement_v3/reproduce.py
```

Mathematics:

`reproductions/daniel_coordinate_free_refinement_v3/MATHEMATICAL_NOTE.md`

## Exact claim

In this finite model, a verifier obstruction determines a unique coarsest quotient refinement without named coordinate-extension candidates; retaining that refinement strictly enlarges the extensional object language available to later construction, and parent-regime replay restores the previous non-formability boundary.

## Exact boundary

`RefinePartition(parent, conflicts)` is still supplied by the developmental meta-language. Therefore this does **not** establish invention of partition refinement, arbitrary type-former invention, open-ended ontology growth, or novel category theory. The underlying mathematics is standard finite quotient/partition refinement.

The boundary has nevertheless moved downward across the experiments:

`named repair -> generic coordinate schema -> derived-feature counterexample -> coordinate-free quotient instance synthesis`.

The next honest question is whether the generic refinement operation itself can arise from a weaker frozen meta-language under a similarly exact obstruction and causal test.

## Mathematical question

Structured Continuation Calculus describes continuations relative to a fixed signature. Here the verified obstruction induces a conservative regime transition

`P0 -> P1`

that changes the extensional continuation/object language from `L(P0)` to the strictly richer `L(P1)`.

What is the natural mathematical structure when these verified regime changes are themselves composable transitions — especially when later constructor languages are indexed by the quotient produced by earlier transitions?

The intended question is deliberately not “is this new category theory?” It is whether this finite witness isolates the right object to formalize one level above continuations inside a fixed regime.