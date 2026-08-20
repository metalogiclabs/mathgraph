# Daniel reproduction — strict typed regime growth

This is a minimal finite witness designed to separate **state/search improvement inside a fixed language** from **growth of the frozen object-level constructor language itself**.

Read [`MATHEMATICAL_NOTE.md`](MATHEMATICAL_NOTE.md) first. Then run:

```bash
python reproductions/daniel_typed_regime_growth_v1/reproduce.py
```

No packages, models, APIs, datasets, or network access are required after cloning.

## Headline result

The frozen old regime `M0` has only unary predicates

```text
U = A -> Bool
```

and every old denotation factors through the projection `(x,a) -> a`.

Episode 1 provides a finite factorization obstruction: states with the same `a` coordinate require different verified outputs. Relative to a **predefined extension family**, the protocol exhausts all 8 possible unary truth-table primitives on `A`; every unary-only alternative preserves the obstruction. The remaining supplied extension schema is `ExposeDependency`, which adds

```text
D = X × A -> Bool
```

plus `x=0 : D`, `lift : U -> D`, and Boolean composition on `D`.

The extension is conservative **in the explicitly defined finite semantic sense used here**: the set of denotable `U`-semantics is unchanged (4 classes before, 4 after). No claim of general proof-theoretic conservativity is made.

The episode-2 target is SHA-256 committed in the program before episode-1 selection, and `select_episode1_extension()` does not read it. This protects against online target leakage; it does **not** establish independent authorship of the experimental design.

Under `M0` there are exactly zero `D`-typed terms. Therefore the protected episode-2 target is outside `Form_D(M0)` by typing, not because bounded search happened to miss it. Under `M1 = M0 + ExposeDependency`, the unchanged size-ordered synthesizer constructs a composed `O2` term with the target semantics.

Removing `ExposeDependency` restores zero `D`-typed terms. Every unary-only sham still fails. The old `U` semantic fragment remains unchanged.

A successful run ends with:

```text
"verdict": "PASS_STRICT_TYPED_REGIME_GROWTH_V1"
"cold_constructible": false
"warm_constructible": true
"ablated_constructible": false
"all_unary_shams_constructible": false
"same_old_fragment": true
```

and all 12 gates set to `true`.

## Exact bounded claim

Inside the frozen finite object-level constructor calculus:

```text
Form_D(M0) = empty
O2 not in Form_D(M0)
O2 in Form_D(M1)
O2 not in Form_D(M1 - ExposeDependency)
O2 not in Form_D(M0 + any unary-only sham)
Sem_U(M0) = Sem_U(M1)
```

with the same episode-2 synthesis procedure in cold and developed arms.

This rules out the explanation that the second result is merely an already-well-formed object found by better search inside the same object language.

## Scientific boundary

`ExposeDependency` is **not invented from an unrestricted meta-language** in this witness. It is a supplied member of the frozen developmental extension family. The factorization obstruction rules out the complete unary-only subfamily; the protocol then admits the supplied dependency-exposing alternative after it passes the finite checks.

Python could encode both regimes from the start. The host language does not grow. The result is therefore:

> a constructed finite witness of strict typed **object-language** formability growth under a supplied developmental extension family.

It is **not** evidence of autonomous invention of arbitrary new type formers, nor a claim that the obstruction uniquely derives `ExposeDependency` from first principles.

The next stronger boundary would be to weaken the developmental meta-language so that `ExposeDependency` is not a named candidate and test whether a dependency-sensitive extension class can itself be synthesized from the obstruction.
