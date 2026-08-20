# Daniel reproduction — strict typed regime growth

This is the small reproduction to read **after** the earlier closure-depth toy.

The earlier toy showed that retaining a verified capability can change later bounded search reachability. This reproduction moves the impossibility boundary one level deeper: the protected second-generation object is **not well-formed in the old constructor language at all**.

Read [`MATHEMATICAL_NOTE.md`](MATHEMATICAL_NOTE.md) first. Then run the executable certificate:

```bash
python reproductions/daniel_typed_regime_growth_v1/reproduce.py
```

No packages, models, APIs, datasets, or network access are required after cloning.

## Headline result

The frozen old regime `M0` has only unary predicates `A -> Bool`. Every old term factors through the projection `(x,a) -> a`.

Episode 1 exposes a certified violation of that factorization. The experiment exhausts all 8 possible unary truth-table primitives on the finite `A` domain; none can repair the obstruction. The admitted extension `ExposeDependency` conservatively adds a new sort

```text
D = X × A -> Bool
```

plus `x=0 : D` and `lift : U -> D`.

The protected episode-2 target is fixed by commitment before episode-1 selection. Under `M0` there are exactly **zero D-typed terms**, so the target is not merely hard to find: it is outside `Form(M0)` by typing. Under `M1 = M0 + ExposeDependency`, the unchanged size-ordered synthesizer constructs a composed `O2` term with the target semantics.

Ablating `O1` restores zero D-typed terms. Every unary-only sham extension still fails. The old unary semantic closure remains exactly unchanged.

A successful run ends with JSON containing:

```text
"verdict": "PASS_STRICT_TYPED_REGIME_GROWTH_V1"
"cold_constructible": false
"warm_constructible": true
"ablated_constructible": false
"all_unary_shams_constructible": false
"same_old_fragment": true
```

and all 12 gates set to `true`.

## What this establishes

Inside the frozen finite **object-level constructor calculus**:

```text
O2 not in Form(M0)
O2 in Form(M1)
O2 not in Form(M1 - O1)
O2 not in Form(M0 + any unary-only sham)
```

with the same episode-2 synthesis procedure in cold and developed arms.

That is stronger than the previous search-reachability toy because the old language lacks the result sort required by `O2`.

## What it does not establish

The host language did not become more expressive. Python could of course encode both regimes from the start. The scientific boundary is the frozen typed language made available to the developmental controller.

This is therefore a **constructed finite witness of strict object-language formability growth**, not evidence that arbitrary AI systems can invent unrestricted new type formers.

The real natural-system evidence remains in the Triskelion/Specimen lineage; this reproduction exists to isolate the mathematical distinction cleanly enough to discuss the regime-change object itself.
