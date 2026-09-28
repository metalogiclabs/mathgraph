# L4YAML SerializationWellFormed v1

**Status:** WARRANTED / Lean-green  
**Qualification:** https://github.com/metalogiclabs/mathgraph/actions/runs/36416541382  
**Upstream working-state pin:** `nasa-jpl/L4YAML@326e4bdfd599fa74e7601bdd84632845a3353ccb`  
**MathGraph branch:** `l4yaml-serialization-wellformed-v1`

## Objective

Construct the missing stateful specification requested by Nicolas Rouquette
after the grammar-completeness audit:

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

## What is now proved

### Independent semantic state

`SerializationWellFormed.lean` defines its own event language and environment:

```text
begin/end document
define/use anchor
declare/use tag handle
```

with no definition in terms of `scanFiltered` or `parseStream`.

The generalized checker is proved equivalent to the declarative relation.
Document boundaries reset both state families. The semantic state is also
proved extensional: only set membership of anchor names and custom handle names
can affect these acceptance decisions; ordering, multiplicity, parser tag
prefixes, and unrelated runtime state are irrelevant.

### Exact runtime guard bridges

For every scanner state and alias name:

```text
scanner alias-membership guard
↔ independent AliasAllowed
```

For every parser state and alias name:

```text
parser alias-membership guard
↔ independent AliasAllowed
```

For every parser state and tag handle:

```text
parser tag-handle guard
↔ independent TagHandleAllowed
```

The tag bridge proves that handle→prefix data can be quotiented to handle-name
presence for declaration acceptance.

### Source lexeme bridges

`SourceEvents.lean` recognizes the four state-changing/use lexemes directly
from `List Char`, without calling the scanner or parser:

```text
&name        → defineAnchor
*name        → useAlias
%TAG !h! …   → declareTag
!h!suffix    → useTag
```

The generalized source lemmas are kernel-side. Anchor definition, alias use,
and named-tag use are additionally connected to the corresponding L4YAML
surface-production witnesses.

### Runtime document scope

`RuntimeScopes.lean` proves:

- explicit scanner document start resets the scanner alias environment;
- successful parser document preparation replaces the tag-handle table with
  exactly the declarations of the current document.

This matches the independent semantic reset law rather than merely testing
fixed examples.

## Fixed-input census

`Census.lean` is measurement only; no generalized theorem depends on it.

The green qualification records:

```text
alias:
  unbound                 → undefinedAlias
  define then use         → ok
  use before definition   → undefinedAlias
  explicit same document  → ok
  cross-document use      → undefinedAlias
  redefine next document  → ok

tag handle:
  undeclared named        → undeclaredTagHandle
  declared named          → ok
  cross-document use      → undeclaredTagHandle
  builtin secondary       → ok
  builtin primary         → ok
  verbatim                → ok
```

## Trust profile

No generalized claim in `SerializationWellFormed.lean`,
`SourceEvents.lean`, or `RuntimeScopes.lean` uses `native_decide`.

Representative `#print axioms` profiles from the green run:

```text
checkFrom_correct                         [propext]
scanner_alias_guard_exact                 [propext, Quot.sound]
parser_alias_guard_exact                  [propext, Quot.sound]
parser_tag_guard_exact                    [propext, Quot.sound]
alias_use_source_exact                    [propext]
named_tag_use_source_exact                [propext]
anchor_definition_surface                 [propext]
alias_use_surface                         [propext]
named_tag_use_surface                     [propext]
prepareDocumentState_tagHandles_exact     [propext, Quot.sound]
```

No `sorryAx` appears in the qualified results.

## Highest-leverage residual

The semantic state itself is no longer the unknown.

The remaining bridge is **whole-input contextual event extraction**: prove that
the anchor/tag events selected from a YAML input are exactly the semantic
occurrences relevant to execution, while not treating indicator-looking
characters inside quoted scalars, block scalar contents, or comments as
events.

The local source lexemes and their surface-production witnesses are now proved,
so this residual is isolated from the state semantics and runtime guard
equivalence.

The next experiment should attach these local event witnesses to an exact
surface derivation (rather than build a second scanner), then prove that the
resulting ordered event trace is the one consumed by
`SerializationWellFormed`.

No upstream PR has been created or submitted.
