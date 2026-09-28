# SerializationWellFormed — handoff status

Upstream working-state pin: nasa-jpl/L4YAML@326e4bdfd599fa74e7601bdd84632845a3353ccb
MathGraph qualified head: 825cbf205750ca567bd269465fd19d609efe4175
Qualification: GitHub Actions run 36471324111 (green)

This directory answers the stateful part of the corrected L4YAML load capstone.

## Independent contract

SerializationWellFormed.lean defines an implementation-independent event
semantics with only the distinctions needed for current load-state acceptance:

- document scope;
- committed anchor names;
- custom tag-handle declarations;
- alias uses;
- tag-handle uses.

The semantic environment is proved extensional: order, duplicate membership,
tag prefixes, and unrelated parser/scanner state do not affect these decisions.

## Exact executable bridges

For every relevant runtime state/name:

- scanner alias membership iff independent AliasAllowed;
- parser alias membership iff independent AliasAllowed;
- parser tag-handle guard iff independent TagHandleAllowed;
- document start resets scanner alias scope;
- parser document preparation replaces the custom handle table with exactly the
  current document's declarations;
- parser node finalization commits an anchor name exactly at node completion.

## Commitment timing

The runtime distinguishes lexical anchor appearance from semantic commitment:

    &x [*x]       scanner ok; load rejects undefinedAlias
    [&x 1, *x]    load accepts

CommitTrace.lean and AnchorRuntime.lean formalize this boundary. A pending
anchor is appended as defineAnchor only after its content events.

## Surface bridge

SourceEvents.lean and SurfaceEvents.lean attach alias/anchor/tag events to
actual surface-production witnesses instead of scanning indicator-looking
characters globally. This prevents quoted scalar, comment, or block-scalar
content from becoming false semantic events.

## Adversarial completeness census

ErrorCensus.lean exhaustively classifies the current ScanError constructors.
Under the corrected contract, the only executable rejection constructors whose
cause is serialization environment state are:

    undefinedAlias
    undeclaredTagHandle

Fuel/depth/single-document API guards are separated as resourceOrAPI. All other
current structured rejection constructors describe surface/structural
acceptance rather than additional serialization environment state.

This census is intentionally exhaustive over the current ScanError ADT, so a
new constructor added upstream forces the classification proof to be revisited.

## Trust boundary

General family claims are Lean proofs. native_decide is not used to carry a
generalized claim. Fixed-input runtime probes remain measurements only.

## Remaining integration boundary

This work does not claim the moving upstream surface grammar is already exact:
scannerDrop and the known surface tightenings remain upstream work.

The intended final capstone shape after those surface obligations close is:

    parseYaml input succeeds
      ↔ ExactSurfaceLanguage input ∧ SerializationWellFormed input

The stateful predicate and its runtime correspondence are the contribution of
this branch; the remaining surface exactness work belongs to the upstream
grammar-completeness refactor.

## Evidence map

- SerializationWellFormed.lean — independent state/event semantics and exact runtime guard projections.
- SourceEvents.lean — independent local source lexeme recognition and surface-production bridges.
- RuntimeScopes.lean — document-scope reset correspondence.
- AnchorTiming.lean — separator proving lexical anchor appearance is not semantic commitment.
- CommitTrace.lean — compositional node-completion event ordering.
- SurfaceEvents.lean — surface witnesses become pending/use events at the correct layer.
- AnchorRuntime.lean — parser addAnchor/applyNodeFinalization correspondence.
- ErrorCensus.lean — exhaustive current ScanError layer classification.
- Census.lean — fixed executable controls, including self-reference and cross-document reset.

## Verification boundary

Qualified at MathGraph head 825cbf205750ca567bd269465fd19d609efe4175 by
run 36471324111 against upstream pin
326e4bdfd599fa74e7601bdd84632845a3353ccb.

There are no sorry/admit placeholders in the packaged Lean files. The printed
axiom profiles for generalized claims contain only Lean/L4YAML ambient logical
axioms such as propext, Quot.sound, and where surface extraction requires it,
Classical.choice. No generalized theorem is carried by native_decide.

The runtime census is evidence for fixed controls; the family-level claims are
the Lean theorems listed above.

No upstream PR has been opened.
