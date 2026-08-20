# Daniel reproduction — target-independent regime growth V2

This version fixes the main weakness of V1: there is **no hand-picked P1 or P2** and no single target-shaped extension choice.

The finite world is

```text
W = X × Y × A,   X=Y=A={0,1}
```

and the base regime observes only `A`.

The developmental meta-language is frozen once as the single symmetric schema

```text
Expose(S),   S ⊆ {x,y}
```

which means: extend the object-level observation regime by exposing the hidden coordinate subset `S`.

Then the experiment evaluates:

- **all 256 Boolean targets** `W -> Bool`;
- **all 65,280 distinct ordered two-episode target pairs**;
- all four possible A-only sham predicates.

Run:

```bash
python reproductions/daniel_target_independent_regime_growth_v2/reproduce.py
```

No packages, APIs, models, datasets, or network access are required after cloning.

## Exact one-episode result

For each of the 256 targets, the verifier computes fiber conflicts and the target's essential hidden-coordinate set. The resulting exact minimal extension classification is:

```text
BASE          4 targets
Expose(x)    12 targets
Expose(y)    12 targets
Expose(x,y) 228 targets
```

So the selector does not always choose one prebuilt representation. Different targets induce different minimal regime extensions under the same frozen generic schema.

For every target, the selected mask is checked to be sufficient, and removing any required coordinate restores a certified fiber conflict.

## Exact two-episode result

Every distinct ordered pair `(P1,P2)` is tested.

Episode 1 selects the exact minimal `Expose(S)` extension for `P1`. Episode 2 uses the same canonical table synthesizer in the cold and developed regimes.

Across all 65,280 pairs:

```text
57,492 pairs
```

have the strict property

```text
P2 not formable in M0
P2 formable after the extension selected by P1
P2 not formable again after ancestor ablation back to M0
```

broken down as:

```text
Expose(x)      132
Expose(y)      132
Expose(x,y) 57,228
```

No second target is selected for favorable transfer; the whole finite pair universe is evaluated.

## What this fixes

V1 could be criticized because the same author chose P1, P2, and a named `ExposeDependency` candidate in the same constructed witness.

V2 removes the target-selection confound by evaluating the complete finite target universe. It also replaces the one named dependency extension with a single coordinate-symmetric generic schema `Expose(S)` and demonstrates that different verified obstructions choose different minimal instantiations.

## Exact claim boundary

This is a complete finite theorem/check about **dependency-sensitive object-language regime selection**:

> verified fiber conflicts determine the exact minimal hidden-coordinate exposure needed for every target in the finite universe, and an extension acquired on one target can strictly enlarge formability for later targets.

It does **not** establish autonomous invention of the generic `Expose` schema. The developmental meta-language still contains that schema from the start.

Mathematically, this is closely related to ordinary functional dependency / partition refinement: a target is formable exactly when it is constant on the fibers of the current observation map. We are not claiming that fact as novel.

The remaining stronger question is one level down:

> Can a weaker generic developmental meta-language synthesize the representation-changing extension class itself, rather than merely instantiate a predeclared `Expose(S)` schema?

That is the next actual invention boundary.
