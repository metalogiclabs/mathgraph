# Independent PKC @Checked statement audit — 19 October 2026

## Result

**SOURCE-CONFIRMED: an optional `@Checked.statement` is not compared to the cited Lean proposition.**
This is a *trust-boundary/claim-scope* finding, not a Lean kernel unsoundness
finding or an assertion that the SysML generated module proves `False`.

## Evidence, immutable source

- JPL source `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`
- [Model.lean](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/interchange/PropertyKindCalculus/Interchange/Model.lean):
  `Checked` has `decl : String` and optional `statement : Option String`.
  Its documentation says the claim is checked against the environment on import.
- [sysml/PKC.sysml](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/sysml/PKC.sysml):
  `@Checked` exposes the optional `statement`.
- [Harvest.lean](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/interchange/PropertyKindCalculus/Interchange/Harvest.lean):
  `unverifiedCitations` passes only `c.decl` to `notEvidence`, which checks
  declaration category and axiom dependencies. The optional string is not read.
- [EmitLean.lean](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/interchange/PropertyKindCalculus/Interchange/EmitLean.lean):
  `citationComment` places the free-form statement in a `-- checked: ...`
  comment. Comment content is not a Lean proof obligation.
- [scripts/ingest-sysml.lean](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/scripts/ingest-sysml.lean):
  ingest uses `Harvest.unverifiedCitations` and gates on its empty result.

## Independently executed source gate

[GREEN CI](https://github.com/metalogiclabs/mathgraph/actions/runs/39172475242),
[nine positive/negative controls](https://github.com/metalogiclabs/mathgraph/actions/runs/39172475242/artifacts/12153405169),
exact source SHA. Verdict `SOURCE_CONFIRMED_UNCHECKED_OPTIONAL_STATEMENT`.

## Native execution status

The independent experiment is in
[the frozen V3 research branch](https://github.com/metalogiclabs/mathgraph/tree/research/jpl-pkc-checked-statement-v3-20261019/research/jpl_pkc_statement_v3),
with actual `Harvest.unverifiedCitations` tests using the authentic PKC
specialization constructor, a conflicting `False` statement, plus missing/data/axiom
negative controls and generated Lean compilation.

Initial run [#39171965474](https://github.com/metalogiclabs/mathgraph/actions/runs/39171965474)
FAILED APPARATUS before entering Lean: Lake couldn't check out the exact pinned
FloatLib SHA `5f8218dc571c01d6f8bd070c65bcd0de3a40b3c5`.
A pinned-SHA dependency-hydration correction was committed without altering
the experiment. Corrected [native run #39172147382](https://github.com/metalogiclabs/mathgraph/actions/runs/39172147382)
is a separate authority; **do not claim its result until completed and inspected**.

## Consequential interpretation

An independent verifier can determine that an annotated declaration denotes
*some* checked proposition while leaving the human-visible proposition that the
author wrote unverified. A semantically unrelated theorem could therefore be
mistaken for support for the annotated model element if consumers treat that
metadata as a proof of the specified statement. This is an assurance policy gap
above the kernel, not a theorem that Lean accepted falsehood.

Smallest source correction: either clearly declare `statement` to be
**non-authoritative documentation**, or compare a typed/canonicalized claim to
the actual checked proposition and fail closed on mismatch. Merely comparing
arbitrary printable strings would not be a reliable semantic equivalence test.

No JPL writes or messages.
