# L4YAML SerializationWellFormed v1

**Upstream working-state pin:** `nasa-jpl/L4YAML@326e4bdfd599fa74e7601bdd84632845a3353ccb`  
**MathGraph branch:** `l4yaml-serialization-wellformed-v1`

## Objective

Construct the missing stateful specification requested after the
grammar-completeness audit:

```text
ExactSurfaceLanguage input
∧ SerializationWellFormed input
        ↔
InExecutableLanguage input
```

This branch starts with the two stateful families that survive every local
surface tightening:

1. anchor definition / alias-use ordering;
2. %TAG declaration / named tag-handle use.

## WARRANTED — v1 semantic core

`SerializationWellFormed.lean` now kernel-checks a small implementation-
independent trace semantics with its own state:

```text
anchors    : List String
tagHandles : List String
```

The tag-prefix values carried by the real parser are intentionally erased.
They affect tag resolution, but the declaration accept/reject guard depends
only on the handle name.  This is the current minimum sufficient state for the
two acceptance families.

Generalized proofs (no `native_decide`):

- independent checker ↔ declarative trace well-formedness;
- anchor definition/use laws and document-reset laws;
- tag declaration/use laws and document-reset laws;
- scanner alias guard ↔ independent alias condition for every scanner state/name;
- parser tag guard ↔ independent tag condition for every parser state/handle;
- extensionality: any two runtime states with the same minimal projection make
  the same acceptance decision.

Qualification:
https://github.com/metalogiclabs/mathgraph/actions/runs/36414025242

Axiom profiles in that run:

```text
checkFrom_correct            [propext]
scanner_alias_guard_exact    [propext, Quot.sound]
parser_tag_guard_exact       [propext, Quot.sound]
```

No `sorryAx`, custom axiom, or `native_decide` supports the generalized
claims.

## WARRANTED — executable census

`Census.lean` measures the stateful boundary on the same upstream pin.

Alias family:

```text
*x                         scanner: undefinedAlias     load: undefinedAlias
a: &x 1 / b: *x           scanner: ok                 load: ok
a: *x / b: &x 1           scanner: undefinedAlias     load: undefinedAlias
cross-document *x          scanner: undefinedAlias     load: undefinedAlias
redefine in next document  scanner: ok                 load: ok
```

Tag-handle family:

```text
!h!x without %TAG          scanner: ok  load: undeclaredTagHandle
declared !h!               scanner: ok  load: ok
cross-document !h! reset   scanner: ok  load: undeclaredTagHandle
!!str                      scanner: ok  load: ok
!local                     scanner: ok  load: ok
verbatim tag               scanner: ok  load: ok
```

This confirms the architectural split Nicolas identified: alias validity is
enforced in the scanner, while named tag-handle validity is enforced later in
the token parser.  A single independent semantic environment nevertheless
accounts for both decisions.

The census is fixed-input executable measurement only; no generalized theorem
depends on it.

## Highest-leverage residual

The semantic core is **not yet the final predicate over `String`**.  The
remaining bridge is:

```text
raw input
  -> independently justified semantic event trace
  -> SerializationWellFormed trace
```

The extractor must not simply call `scanFiltered` / `parseStream`, or the
specification would collapse back into executable acceptance.

The next experiment is therefore to identify the smallest source/surface
witness sufficient to recover these four event kinds:

```text
defineAnchor
useAlias
declareTag
useTag
```

plus document scope boundaries, and then prove its correspondence to the
runtime state projections.

## Status

**REUSABLE:** independent event semantics + minimum sufficient state + runtime
guard bridges.

**UNKNOWN:** the smallest non-circular input→event extraction relation and the
full `ExactSurfaceLanguage ∧ SerializationWellFormed ↔ InExecutableLanguage`
composition.
