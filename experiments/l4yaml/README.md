# L4YAML grammar-completeness audit

Public MathGraph audit of `nasa-jpl/L4YAML`, pinned at
`16562a74421f94cc0f8216eecf21f1ff58166fa7`.

## Current terminal result

**NAMED_OBSTRUCTION: `L4YAML_CAPSTONE_LAYER_MISMATCH`**

The advertised universal capstone

```lean
∀ input : String,
  ((∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs) ↔
   L4YAML.Surface.InYamlLanguage input)
```

is false at the pinned revision.

This is proved in Lean by concrete surface-language witnesses that the
executable pipeline rejects. The witnesses are independent of
`SLYamlStream.scannerDrop`, so removing that constructor alone cannot repair
the theorem.

See:

- [REPORT.md](./REPORT.md) — full technical audit and corrected contract
- [NAMED_OBSTRUCTION.md](./NAMED_OBSTRUCTION.md) — terminal obstruction
- [CapstoneObstruction.lean](./CapstoneObstruction.lean) — malformed directive + universal no-go
- [SemanticObstruction.lean](./SemanticObstruction.lean) — unbound alias
- [TagHandleObstruction.lean](./TagHandleObstruction.lean) — undeclared named tag handle
- [BlockHeaderObstruction.lean](./BlockHeaderObstruction.lean) — surface block-header over-approximation
- [CorrectedCapstone.lean](./CorrectedCapstone.lean) — exact executable factorization
- [LanguageRelation.lean](./LanguageRelation.lean) — parser-language versus surface-language relation
- [ParserBoundaryProbe.lean](./ParserBoundaryProbe.lean) — flow scanner/parser separator
- [FlowContinuation.lean](./FlowContinuation.lean) — continuation algebra for flow reconstruction
- [ExactNestedFlow.lean](./ExactNestedFlow.lean) — exact nested-flow witness without `scannerDrop`

## Main findings

The scanner is broader than the parser on adjacency-invalid flow syntax, but
current `parse_strict_proof` discards its successful `parseStream` witness.
That makes the scanner proof carry syntactic work the parser has already done.

More importantly, the current surface predicate and executable load pipeline
do not describe the same layer. Examples:

```text
%YAML .2
---
```

is in the current surface language but rejected by the executable directive
validation;

```text
*x
```

is a surface alias but rejected because there is no earlier `&x`; and

```text
!h!x
```

is surface tag syntax but rejected because `!h!` was never declared.

The corrected end state is therefore either a syntax-only capstone plus a
separate serialization-validity theorem, or a load capstone whose
specification explicitly combines exact surface syntax with stateful
serialization well-formedness.

No upstream PR has been created or submitted.
