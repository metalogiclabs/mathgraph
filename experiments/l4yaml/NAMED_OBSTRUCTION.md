# NAMED_OBSTRUCTION — L4YAML `parse_iff_grammar` is false on current main

**Status:** `NAMED_OBSTRUCTION`

**Upstream pin:** `nasa-jpl/L4YAML@16562a74421f94cc0f8216eecf21f1ff58166fa7`

**Kernel-qualified run:** https://github.com/metalogiclabs/mathgraph/actions/runs/36365198859

## Counterexample

```text
%YAML .2
---
```

The executable parser rejects this input, as YAML 1.2.2 requires the
`%YAML` version to have the shape `digit+ "." digit+`.

But the current surface grammar proves:

```lean
InYamlLanguage "%YAML .2\n---"
```

using only the ordinary surface-production constructors. The derivation does
**not** use `SLYamlStream.scannerDrop`.

The same kernel-checked file proves:

```lean
theorem parse_iff_grammar_current_statement_false :
  ¬ ((∃ docs, L4YAML.TokenParser.parseYaml "%YAML .2\n---" = .ok docs) ↔
     InYamlLanguage "%YAML .2\n---")
```

Source: [CapstoneObstruction.lean](./CapstoneObstruction.lean).

## Cause

`Surface/Basic.lean` explicitly defines `SLDirective` as a simplified
shape grammar:

```
"%" + arbitrary non-break text + comments
```

while the executable scanner gives `%YAML` and `%TAG` their stricter
YAML 1.2.2 validation.

The grammar-completeness plan currently identifies `scannerDrop` as the
remaining source of over-approximation. This counterexample shows there is at
least one independent over-approximation below `SLYamlStream`.

## Consequence

Removing `scannerDrop` is necessary but cannot make the advertised
`parse_iff_grammar` theorem true by itself.

The cheapest corrected route is:

1. audit every deliberate surface-grammar simplification against parser
   rejection;
2. tighten/refine the mismatching productions, beginning with directives;
3. then remove `scannerDrop` using parser-guided flow reconstruction;
4. only then attack the converse theorem.

This obstruction prevents spending thousands of proof lines on a theorem
whose current statement has a concrete kernel-checked counterexample.
