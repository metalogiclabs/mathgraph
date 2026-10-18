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

## Native execution — WARRANTED_BOUNDED on the real PKC importer

**GREEN** [GitHub Actions run #39174459130](https://github.com/metalogiclabs/mathgraph/actions/runs/39174459130),
[job #117814155927](https://github.com/metalogiclabs/mathgraph/actions/runs/39174459130/job/117814155927),
source `metalogiclabs/mathgraph@3f67cebfc7f84bc333a107b26554ce4d3aa1632e`.
[Unmodified JPL source](https://github.com/nasa-jpl/PropertyKindCalculus/commit/e0deb453e05ffa63297d9704ceb47d0855193824)
was checked out at exact SHA with Lean `v4.34.0`; JPL's own
`Interchange` and `PropertyKindCalculus.Iso80000.Part3` compiled successfully
(1,750 Lake jobs). Exact immutable FloatLib `5f8218dc` was hydrated first;
the optional Mathlib dependency cache did not alter any revision.

The real `Harvest.unverifiedCitations` returned:

```text
ACTUAL_DECL_TYPE:
  PropertyKindCalculus.Iso80000.Part3.Edge
    (PropertyKindCalculus.Iso80000.Part3.width.kind LTMCTDimensionBase)
    (PropertyKindCalculus.Iso80000.Part3.length.kind LTMCTDimensionBase)
CONTROL_PASS: valid_proposition; missing_declaration_rejected; data_rejected; axiom_rejected
FALSE_STATEMENT_ISSUES=[]
TRUE_STATEMENT_ISSUES=[]
CANDIDATE_UNCHECKED_STATEMENT_METADATA: forged textual statement accepted at PKC citation gate
```

`EmitLean.emit` rendered the same citation in the generated Lean source as:

```lean
-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False
```

and **the generated Lean module compiled**. The accepted *proof declaration*
remains the genuine `Edge.width_length` constructor; `False` is an
unchecked comment, never a proof obligation.

**Independent raw-evidence artifact:**
[artifact #12153673474](https://github.com/metalogiclabs/mathgraph/actions/runs/39174459130/artifacts/12153673474),
ZIP SHA256
`44486d0ae2ead7c888e72b3d875430625f9574bf83abca84aaee7e3db7a7d187`.

Earlier history is retained instead of being overwritten:

- [#39171965474](https://github.com/metalogiclabs/mathgraph/actions/runs/39171965474) failed before Lean at the source-locked FloatLib Git fetch.
- [#39172147382](https://github.com/metalogiclabs/mathgraph/actions/runs/39172147382) completed JPL's 1,758-job build, then our **own** `real_importer_probe.lean` had a Lean parse error from using reserved `axiom` as a local identifier.
- [#39174459130](https://github.com/metalogiclabs/mathgraph/actions/runs/39174459130) changed only that local identifier plus optional dependency caching; original target SHA, claimed proposition, forged strings and positive/negative controls were preserved.

**Precisely bounded inference:** this is a native source-exact falsifier of
the **citation-checking semantic promise**, not a run of the complete external
OpenSysML → API JSON → PKC import CLI. There is no implication that the
Lean kernel proves `False`, nor that a third-party author has used this
mismatch in practice. The author's intended semantics for optional
`statement` metadata must be clarified.

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
