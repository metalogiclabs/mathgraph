# NAMED_OBSTRUCTION — L4YAML_CAPSTONE_LAYER_MISMATCH

**Terminal form:** `NAMED_OBSTRUCTION`  
**Status:** kernel-qualified  
**Upstream pin:** `nasa-jpl/L4YAML@16562a74421f94cc0f8216eecf21f1ff58166fa7`  
**Consolidated green gate:** https://github.com/metalogiclabs/mathgraph/actions/runs/36367045472

## Claim blocked

The advertised universal theorem

```lean
∀ input : String,
  ((∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs) ↔
   L4YAML.Surface.InYamlLanguage input)
```

is false at the pinned revision.

`NoGo.lean` proves its negation in Lean. This is a mathematical obstruction
to the current theorem statement, not an unfinished tactic proof.

## Independent witnesses

### 1. Simplified directive grammar

```text
%YAML .2
---
```

The surface grammar derives the input using ordinary constructors; the
executable scanner/parser rejects it. No `SLYamlStream.scannerDrop` occurs in
the surface derivation.

### 2. Stateful alias environment

```text
*x
```

The surface grammar derives an alias node. The executable pipeline rejects it
because no preceding `&x` binding exists. The pure surface relation carries
no anchor environment.

### 3. Stateful tag-handle environment

```text
!h!x
```

The surface grammar derives the named tag property. The executable parser
rejects it because `!h!` was not declared by a preceding `%TAG` directive.

### 4. Block-header over-approximation

```text
|+++
```

(with terminating newline)

`SCBBlockHeader` admits an unbounded `GStar` of header-indicator characters.
The executable scanner only consumes two header-indicator positions, so the
surface derivation exists while executable acceptance fails.

## Why removing scannerDrop is insufficient

All four witnesses above are constructed through ordinary surface-production
constructors. The first, second, third, and fourth counterexamples therefore
survive the conceptual removal of the top-level `scannerDrop` escape hatch.

The upstream Fix-A plan addresses a genuine flow-proof problem, but it does not
repair the theorem contract.

## Exact fact that is true

`CorrectedCapstone.lean` proves:

```lean
def InExecutableLanguage (input : String) : Prop :=
  ∃ tokens rawDocs,
    Scanner.scanFiltered input = .ok tokens ∧
    TokenParser.parseStream tokens = .ok rawDocs

theorem parse_iff_executable_language (input : String) :
  (∃ docs, TokenParser.parseYaml input = .ok docs) ↔
  InExecutableLanguage input
```

This is a factorization theorem, not a replacement independent specification.
It isolates the missing bridge.

## Resolution

A valid final capstone must align abstraction layers. Either:

- prove a syntax-only parser equivalent to an exact YAML surface language and
  prove load-time semantic validity separately; or
- keep the existing `parseYaml` load semantics and strengthen the
  specification side to `ExactSurfaceLanguage ∧ SerializationWellFormed`.

The complete audit and evidence are in [REPORT.md](./REPORT.md).

No upstream PR has been created or submitted.
