# L4YAML SerializationWellFormed v1

**Upstream working-state pin:** `nasa-jpl/L4YAML@326e4bdfd599fa74e7601bdd84632845a3353ccb`  
**MathGraph branch:** `l4yaml-serialization-wellformed-v1`

## Objective

Construct the missing independent stateful specification requested by Nicolas
Rouquette after the grammar-completeness audit:

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

## v1 experiment

`SerializationWellFormed.lean` introduces an implementation-independent event
semantics and semantic environment, then proves:

- a generalized checker ↔ declarative well-formedness theorem;
- anchor definition/use and document-reset laws;
- tag declaration/use and document-reset laws;
- the scanner's alias guard agrees with the independent alias condition for
  every scanner state/name;
- the parser's tag-handle guard agrees with the independent tag condition for
  every parser state/handle.

The generalized results use no `native_decide`.  Axiom profiles are printed
by the qualification run.

## Residual

The next bridge is **input → semantic event trace**.  The important constraint is
that this extractor must not simply call `scanFiltered`/`parseStream`, or the
specification would collapse back into executable acceptance.

The cheapest next experiment is to recover anchor-definition / alias-use events
directly from source spans and recover %TAG declarations / named tag uses from
the corresponding source productions, then prove agreement with the runtime
state projections.
