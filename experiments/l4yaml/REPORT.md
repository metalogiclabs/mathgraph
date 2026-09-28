# L4YAML Grammar-Completeness Audit — MathGraph Report

**Date:** 2026-09-28  
**Upstream:** `nasa-jpl/L4YAML`  
**Pinned upstream commit:** `16562a74421f94cc0f8216eecf21f1ff58166fa7`  
**MathGraph branch:** `l4yaml-parser-boundary-v1`

## Executive summary

The advertised final capstone is:

```lean
theorem parse_iff_grammar (input : String) :
    (∃ docs, parseYaml input = .ok docs) ↔ InYamlLanguage input
```

The current upstream plan treats removal of `SLYamlStream.scannerDrop` as the
main prerequisite for the converse direction.

MathGraph found two distinct issues.

1. **Parser-boundary mismatch.** The scanner accepts/tokenizes some malformed
   flow-adjacency inputs that the parser correctly rejects. Yet
   `parse_strict_proof` obtains the successful `parseStream` witness and
   discards it, proving surface-language membership from scanner success alone.
   This explains why `scannerDrop` is needed and suggests a smaller exact
   proof boundary:
   `scanFiltered ok ∧ parseStream ok → exact surface derivation`.

2. **Independent capstone obstruction.** Even if `scannerDrop` is removed,
   the current biconditional is still false as stated. The surface grammar's
   simplified `SLDirective` accepts malformed YAML directives that the
   executable parser rejects. This was kernel-checked with the concrete input:

   ```text
   %YAML .2
   ---
   ```

   Lean verifies both `InYamlLanguage` for this string and that no
   `parseYaml` result can be `.ok`, yielding a direct proof that the current
   biconditional fails on this input.

The consequence is that the cheapest route to the true capstone is not to
begin with the full planned 1.1–2.3k-line flow-scanner strengthening. First
audit and tighten every intentionally relaxed surface production that can
admit strings rejected by the executable scanner/parser. Then remove
`scannerDrop`, preferably at the parser-success boundary, and only then prove
the converse.

## Verified results

### 1. Scanner success is not exact YAML syntax

The public MathGraph probe kernel-checks:

```text
scanAccepts "[[a][b]]" = true
parseAccepts "[[a][b]]" = false

scanAccepts "[[a]b]" = true
parseAccepts "[[a]b]" = false

scanAccepts "[\"a\"\"b\"]" = true
parseAccepts "[\"a\"\"b\"]" = false

scanAccepts "{a: b: c}" = true
parseAccepts "{a: b: c}" = false

scanAccepts "[a,b]" = true
parseAccepts "[a,b]" = true
```

It also proves that any successful `parseYaml` already contains both
`scanFiltered` success and `parseStream` success through upstream
`parseYamlRaw_ok_decompose`.

**Evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36362994161

### 2. Parser success contains the missing separator distinction

The MathGraph probe proves, for flow sequences and mappings, that once a
collection already contains an item/pair, successful loop growth requires the
current parser token to be `.flowEntry`.

This is exactly the syntactic distinction absent from scanner-only strictness.

### 3. Exact flow grammar can be built without `scannerDrop`

`ExactNestedFlow.lean` constructs a full exact surface derivation for
`[[],[]]` using the ordinary YAML surface constructors only. It also keeps
`[[][]]` as the negative parser control.

This demonstrates that the flow-side target object is constructible without
the escape hatch.

### 4. Continuation algebra removes unnecessary left-to-right rebuild cost

`FlowContinuation.lean` defines continuation-style interfaces for
`SFlowSeqEntries` and `SFlowMapEntries`.

Instead of repeatedly rebuilding or inverting a right-recursive grammar while
the scanner/parser proceeds left-to-right, the proof keeps a continuation:

```text
valid tail from current position
    -> valid full collection from collection start
```

Each comma-separated entry composes one constructor into the continuation.
This is a smaller proof interface than bespoke structural `snoc` machinery.

### 5. The current capstone statement is false independently of `scannerDrop`

The kernel-checked theorem establishes:

```lean
¬ ((∃ docs, L4YAML.TokenParser.parseYaml "%YAML .2\n---" = .ok docs) ↔
   InYamlLanguage "%YAML .2\n---")
```

The surface witness uses the normal document/directive constructors, not
`SLYamlStream.scannerDrop`.

The root cause is upstream's deliberately simplified directive production:

```text
SLDirective ≈ '%' + arbitrary non-linebreak text + line ending
```

whereas the executable scanner validates special `%YAML` syntax, including
nonempty numeric version components.

**Evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36365275334  
https://github.com/metalogiclabs/mathgraph/actions/runs/36365275334/job/108750293248

## Epistemic status

**WARRANTED**

- Scanner success alone is broader than parser acceptance for the tested flow
  adjacency cases.
- Successful `parseYaml` retains a successful `parseStream` witness that
  current `parse_strict_proof` does not use.
- The current advertised `parse_iff_grammar` statement is false on the
  kernel-checked malformed `%YAML .2` input.
- This counterexample does not depend on `scannerDrop`.
- Exact nested-flow surface evidence can be constructed without
  `scannerDrop`.
- Continuation-style flow accumulation is valid Lean algebra for the existing
  surface grammar.

**CANDIDATE**

- Replacing scanner-only strictness with a parser-guided surface
  reconstruction will materially reduce the full Fix-A proof burden.
- Continuation accumulation can replace most of the proposed entry-`snoc`
  machinery in the final upstream implementation.

**UNKNOWN**

- Whether directive exactness is the only non-`scannerDrop` obstruction.
- How many other deliberately relaxed surface productions admit parser-rejected
  strings.
- The final line count / complexity of the repaired capstone proof.

## Corrected route to the capstone

The evidence supports the following order:

```text
1. Audit all relaxed surface productions against executable acceptance.
2. Tighten every proven surface/parser mismatch.
3. Replace scanner-only exactness at flow boundaries with
   scanner-character evidence + parser-success structure.
4. Remove scannerDrop.
5. Prove:
      InYamlLanguage input -> ∃ docs, parseYaml input = .ok docs
6. Assemble:
      (∃ docs, parseYaml input = .ok docs) ↔ InYamlLanguage input
7. Run full upstream qualification and submit the minimal patch series.
```

The highest-leverage immediate experiment is a finite, systematic
surface-relaxation differential audit. The source already marks several
productions as simplified or deliberately loose (directives, tag/property
syntax, comment/directive character handling, selected document/prefix
rules). Each should be tested for a kernel-constructible surface witness paired
with executable rejection.

## Ultimate target

The ultimate result is not merely a critique of the proof plan. It is an
upstream-quality, sorry-free patch series that:

- makes `InYamlLanguage` exact enough for the claimed YAML 1.2.2 contract;
- removes `scannerDrop`;
- proves `grammar_completeness`;
- proves the final `parse_iff_grammar` biconditional;
- preserves the existing build/test/capstone qualification; and
- leaves behind a reusable proof-engineering rule: **do not force one proof
  layer to reconstruct distinctions already certified by a later layer, and
  audit every intentional over-approximation before attempting a
  bidirectional correctness theorem.**

That final rule is the transferable MathGraph result from this case.
