# L4YAML Grammar-Completeness Audit — MathGraph Report

**Date:** 2026-09-28  
**Upstream:** `nasa-jpl/L4YAML`  
**Pinned upstream commit:** `16562a74421f94cc0f8216eecf21f1ff58166fa7`  
**MathGraph branch:** `l4yaml-parser-boundary-v1`

## Executive result

The advertised capstone

```lean
theorem parse_iff_grammar (input : String) :
    (∃ docs, parseYaml input = .ok docs) ↔ InYamlLanguage input
```

is **false at the pinned upstream revision**. This is now a kernel-checked
result, not a search failure or an architectural opinion.

MathGraph found three independent classes of obstruction:

1. **Flow proof-boundary mismatch.** Scanner acceptance is broader than parser
   acceptance for adjacency-invalid flow syntax. The current
   `parse_strict_proof` obtains parser success and then discards it, forcing
   scanner-only proof machinery to reconstruct distinctions the parser already
   made.
2. **Local surface over-approximations.** Ordinary surface constructors derive
   strings the executable parser rejects, independently of
   `SLYamlStream.scannerDrop`. Verified examples include malformed
   `%YAML .2` syntax and an overlong block-scalar header.
3. **Stateful semantic conditions absent from the surface relation.** The
   executable load pipeline rejects an unbound alias and an undeclared named
   tag handle, while the pure surface grammar derives both strings.

Consequently, removing `scannerDrop` cannot make the advertised
biconditional true. The problem is not just unfinished proof engineering: the
two sides currently describe different languages at different abstraction
layers.

## Kernel-qualified evidence

### A. Scanner acceptance is not exact parser syntax

The parser-boundary probe checks:

```text
scan "[[a][b]]"  = yes    parse = no
scan "[[a]b]"    = yes    parse = no
scan "[\"a\"\"b\"]" = yes    parse = no
scan "{a: b: c}" = yes    parse = no
scan "[a,b]"      = yes    parse = yes
```

It also proves that every successful `parseYaml` already contains both
`scanFiltered` success and `parseStream` success through upstream
`parseYamlRaw_ok_decompose`.

**Evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36362994161

The same probe derives parser-loop theorems showing that after a flow
collection has an item/pair, any successful growth crosses an explicit
`.flowEntry` token. It also upgrades comma scanning to an exact
`GLit ','` production witness.

### B. Exact nested flow is constructible without `scannerDrop`

`ExactNestedFlow.lean` builds a complete ordinary surface derivation for
`[[],[]]`, while `[[][]]` remains the negative parser control.

`FlowContinuation.lean` proves a continuation algebra for
`SFlowSeqEntries` and `SFlowMapEntries`. This avoids repeatedly rebuilding
or inverting the right-recursive grammar while execution proceeds
left-to-right.

These results make parser-guided flow reconstruction a concrete alternative to
the proposed large scanner-side `snoc` accumulator.

### C. Malformed directive: local grammar counterexample

For

```text
%YAML .2
---
```

Lean proves:

```lean
InYamlLanguage "%YAML .2\n---"
```

using ordinary surface-production constructors and no `scannerDrop`, while
the executable scanner/parser rejects the malformed YAML version.

The kernel then proves:

```lean
¬ ((∃ docs, parseYaml "%YAML .2\n---" = .ok docs) ↔
   InYamlLanguage "%YAML .2\n---")
```

The cause is explicit in upstream source: `SLDirective` is deliberately
simplified to approximately `'%' + arbitrary non-break text + comments`,
while the scanner validates special directives more strictly.

**Evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36365275334

### D. Unbound alias: stateful semantic counterexample

For

```text
*x
```

the surface grammar derives a normal alias node with
`SCNsAliasNode → SFlowNode.alias → SBlockNode → SLYamlStream`.

The executable scanner/parser rejects it because no preceding `&x` binding
exists. This stateful environment requirement is not present in the pure
surface derivation.

Therefore surface syntax alone cannot characterize the current `parseYaml`
load API merely by repairing local grammar productions.

### E. Undeclared named tag handle: second stateful counterexample

For

```text
!h!x
```

the ordinary surface tag/property constructors derive the input, but
`parseNodeProperties` rejects it because `!h!` was not introduced by a
preceding `%TAG` directive.

This independently confirms the layer mismatch: executable acceptance includes
per-document semantic environments that `InYamlLanguage` does not encode.

### F. Block-scalar header: second local grammar counterexample

The surface `SCBBlockHeader` currently uses an unbounded `GStar` over block
header indicator characters. The executable scanner only consumes two header
indicator positions.

MathGraph therefore proves an exact surface derivation for

```text
|+++
```

(with the terminating newline) while `parseYaml` rejects it. This witness is
also independent of directives, aliases, tags, and `scannerDrop`.

A separate executable audit found that `|++\n` and `|11\n` are currently
accepted. Upstream's own block-header specification comments describe the
intended header as at most one chomping indicator and one indentation
indicator, so strict YAML-spec conformance at this boundary deserves a separate
repair even where parser and current surface grammar agree.

### G. Universal no-go theorem

The consolidated fast qualification kernel-checks:

```lean
theorem advertised_parse_iff_grammar_is_false :
  ¬ (∀ input : String,
      ((∃ docs, parseYaml input = .ok docs) ↔ InYamlLanguage input))
```

and a second proof of the same universal negation using the unbound-alias
counterexample.

**Consolidated evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36367733540

**Dedicated universal no-go gate:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36367703623

### H. Strict language relation

MathGraph combines upstream `parse_strict_proof` with the concrete
counterexample to prove:

```lean
(∀ input, ParseLanguage input → InYamlLanguage input) ∧
(∃ input, InYamlLanguage input ∧ ¬ ParseLanguage input)
```

So the current executable parse language is a **proper subset** of the current
surface language.

**Evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36367643538

### I. Exact executable factorization

MathGraph also proves the exact theorem that *is* already true:

```lean
def InExecutableLanguage (input : String) : Prop :=
  ∃ tokens rawDocs,
    Scanner.scanFiltered input = .ok tokens ∧
    TokenParser.parseStream tokens = .ok rawDocs

theorem parse_iff_executable_language (input : String) :
  (∃ docs, TokenParser.parseYaml input = .ok docs) ↔
  InExecutableLanguage input
```

This is not proposed as an independent YAML specification; it is a
factorization theorem. It isolates the real missing bridge from specification
to executable acceptance.

## Acceptance audit

The executable differential audit is green and records:

```text
"--- foo"                         OK
"--- a: b"                       ERR content-on-document-start-line
"*x"                             ERR undefined alias
"!h!x"                           ERR undeclared tag handle
"%YAML 1.2\n%YAML 1.2\n---"     ERR duplicate YAML directive
"%YAML .2\n---"                  ERR malformed/trailing directive content
"!!"                             OK
"!h!"                            ERR undeclared named handle
"|++\n"                          OK
"|11\n"                          OK
```

**Evidence:**  
https://github.com/metalogiclabs/mathgraph/actions/runs/36366475770

## What changed relative to the upstream plan

The upstream plan treats this as essentially:

```text
remove scannerDrop
→ prove grammar_completeness
→ assemble parse_iff_grammar
```

The verified dependency structure is instead:

```text
surface-spec exactness
        +
stateful load well-formedness
        +
parser-guided flow reconstruction
        ↓
exact specification ↔ executable acceptance
        ↓
parse/load capstone
```

`scannerDrop` is one obstruction, not the root contract.

## Correct contract

There are two coherent end states.

### Option 1 — syntax capstone

Separate syntax recognition from stateful loading/validation, then prove:

```text
syntax parser accepts input
    ↔
exact YAML 1.2.2 surface syntax
```

Alias binding, tag-handle environments and similar serialization constraints
are proved in a second theorem about loading/validation.

### Option 2 — load capstone

Keep the current `parseYaml` behavior and strengthen the right-hand side:

```text
parseYaml accepts input
    ↔
ExactSurfaceLanguage input
  ∧ SerializationWellFormed input
```

where `SerializationWellFormed` explicitly carries the stateful conditions
currently enforced operationally, including at least anchor/alias ordering and
tag-handle declaration state.

Either route is layer-correct. The current pure
`parseYaml ↔ InYamlLanguage` statement is not.

## Epistemic status

**WARRANTED / kernel-checked**

- Scanner success alone is broader than parser acceptance for the recorded
  flow-adjacency cases.
- Successful `parseYaml` contains a successful `parseStream` witness that
  current `parse_strict_proof` does not use.
- The advertised universal `parse_iff_grammar` theorem is false at the pinned
  upstream revision.
- The malformed-directive counterexample does not use `scannerDrop`.
- The unbound-alias counterexample does not use `scannerDrop`.
- The undeclared-tag-handle counterexample does not use `scannerDrop`.
- The overlong block-header counterexample does not use `scannerDrop`.
- Exact nested-flow surface evidence is constructible without
  `scannerDrop`.
- Continuation-style flow accumulation is valid Lean algebra.
- Full `parseYaml` acceptance is exactly equivalent to the factored
  scanner+`parseStream` predicate `InExecutableLanguage`.

**CANDIDATE**

- Parser-guided reconstruction plus continuation accumulation can remove most
  of the proposed scanner-side Fix-A complexity.
- Splitting the syntax and load contracts will lead to a substantially smaller
  and more maintainable final proof than enriching scanner strictness until it
  duplicates parser/semantic state.

**UNKNOWN**

- The complete set of surface/spec deviations beyond the now-verified
  directive and block-header examples.
- The smallest independent definition of `SerializationWellFormed` that
  exactly matches all current load-time checks.
- Final implementation size after Nicolas chooses syntax-capstone versus
  load-capstone semantics.

## Ultimate target

The useful finish is no longer “force the advertised theorem through.”

It is a sorry-free, independently specified contract in which the two sides
actually describe the same layer, followed by a proof of their equivalence.
For the existing load API that means:

```text
ExactSurfaceLanguage
+ explicit stateful serialization validity
             ↕
scanFiltered + parseStream
             ↕
          parseYaml
```

The transferable proof-engineering result is:

> **Before spending proof effort on a biconditional, audit whether both sides
> carry the same distinctions. Never force an earlier proof layer to recreate
> information already certified downstream, and never equate a local syntax
> relation with an executable pipeline that enforces additional stateful
> semantics.**

No upstream PR has been created or submitted. All work remains on the public
MathGraph experiment branch.
