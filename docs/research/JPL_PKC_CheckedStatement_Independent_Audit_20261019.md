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

## V4 — actual API-JSON ingest and causal fail-closed correction: WARRANTED_BOUNDED

Independent [GREEN run #39176658515](https://github.com/metalogiclabs/mathgraph/actions/runs/39176658515),
[source and frozen protocol](https://github.com/metalogiclabs/mathgraph/tree/research/jpl-pkc-ingest-policy-v4-20261019/research/jpl_pkc_statement_v4),
[raw artifact #12153809553](https://github.com/metalogiclabs/mathgraph/actions/runs/39176658515/artifacts/12153809553),
independently downloaded ZIP SHA256
`297c1fc06c8c795d66275aa960ddf9dd43d8ab6541809e8cf983c1df5621d2f5`.

The six inputs were independently assembled in **the same API-element JSON form used by
JPL's own `Tests.Interchange.ApiJson` fixture**, read by the real `ApiJson.read`,
then passed to the real `scripts/ingest-sysml.lean` script.
`nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824` and
its source-declared Lean/FloatLib/Mathlib dependencies were never changed in the
original lane.

| Exact input | Original JPL import | One-site strict policy |
|---|---|---|
| Genuine `Edge.width_length` citation; `statement = none` | **ACCEPT** | **ACCEPT** |
| Genuine `Edge.width_length`; `statement = "False"` | **ACCEPT** | **REJECT** |
| Same declaration; `statement = "True"` | **ACCEPT** | **REJECT** |
| Missing declaration | REJECT | REJECT |
| `Nat.add` data citation | REJECT | REJECT |
| `propext` axiom citation | REJECT | REJECT |

The generated Lean module with
`-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False`
also compiled in the original lane. No `False` theorem was asserted.

**Causal ablation:** after rebuilding with the strict rule, the original valid
citation remained accepted, conflicting optional strings were rejected, and
all three existing negative gates were preserved; physically withdrawing
the single-source-file policy and rebuilding restored acceptance of
`statement = "False"`. All **13 actual native admissions** matched the
predeclared vector, and the independent receipt verifier checked the
native rejection reasons. The initial original build was 3,031 Lake jobs
and strict/withdraw builds completed successfully (1,749 jobs each).

**Exact repaired source policy, source-local only:**
in `Harvest.unverifiedCitations` reject any `c.statement.isSome` with
`@Checked.statement is unchecked free text; typed correspondence required`.
The one-site source patch touched only
`interchange/PropertyKindCalculus/Interchange/Harvest.lean`. The source
SHA256 changed from
`28bb3c84b7cf86813e60967eb88d680e274f9a8f5d59d8e4432f411dfe75263c`
to
`ff1e12beb4dccd58cc1a9ba3da022cb8f018c229b11e9705c45544974e25cf98`.
It is a conservative *candidate* policy until Nicolas selects semantics for
the optional prose field.

**Distinct next gate:** the external OpenSysML `sysml -convert api-json`
textual converter was NOT exercised in V4, and no complete round-trip
from arbitrary SysML text was claimed. A source-aware Metalogic fork
[candidate patch](https://github.com/metalogiclabs/PropertyKindCalculus/commit/de056636b6c6fa60d5158db04e6a7e6175e62e81)
contains the guarded source correction, a clarified model comment and
regression tests; its **own fork CI is not qualified** (shallow-checkout
preflight failure). JPL's upstream repository was not mutated.

## V5 — actual OpenSysML text-to-Lean chain, causally qualified

**GREEN / WARRANTED_BOUNDED_FULL_TEXT_TO_KERNEL_WITHDRAWAL**:
[GitHub Actions #39177893785](https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785),
[job #117824250514](https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785/job/117824250514),
[full raw evidence #12155725060](https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785/artifacts/12155725060).
The artifact's original downloaded ZIP was independently SHA256-verified against
the GitHub metadata:
`8546dfc16783f8243329883e12b7a11f49b6d0c7a3634aaa5293e6c32613cbc6`.

**V5 provenance:** `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`,
Lean v4.34.0, external Open-MBEE/OpenSysML binary `sysml v0.9.1` from its
released `sysml-linux-amd64.tar.gz`. The published archive checksum
`eb22167262f05969ba91d4fc0cb25875bc0b220d209aa82a47b11de9c303f8a3`
was independently matched byte-for-byte before execution. Its reported build
commit was `b9de3b070906585c7f070610f3d7651ef3f6e5ce`. Original JPL
source, source dependencies and the frozen V3/V4 adversarial requirement were
not changed.

**Frozen original source text** generated by real JPL `EmitSysml.emit`:

```sysml
package M {
    private import PKC::*;
    private import PKC::Kinds::*;
    private import PKC::Modules::*;
    private import PKC::Tape::*;

    #kind width {
        :>> id default = "width"; :>> scale default = ScaleType::ratio;
        @Checked { decl = "PropertyKindCalculus.Iso80000.Part3.Edge.width_length"; statement = "False"; }
    }
}
```

The exact same text successfully passed OpenSysML `-validate`, was emitted as
OpenSysML's full real `api-json` element list (the `"False"` value was present),
was ingested by JPL's own `scripts/ingest-sysml.sh`, and the
generated Lean module compiled with this original **comment**:

```lean
-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False
```

The original cited Lean declaration instead has the checked type
`Edge (width.kind LTMCTDimensionBase) (length.kind LTMCTDimensionBase)`,
not `False`.

| Full text-to-import test | Original JPL | Strict one-site policy |
|---|---|---|
| Same genuine `Edge.width_length` proof, no `statement` | **ACCEPT** | **ACCEPT** |
| Same proof with `statement = "False"` | **ACCEPT** | **REJECT** |

The strict rejection log contains the expected
`@Checked.statement is unchecked free text; typed correspondence required`
reason and follows an exact-context, one-file patch to
`Interchange/Harvest.lean`. **Causal withdrawal** of that exact patch
(and restoration of the original module) readmitted the identical
`statement = "False"` SysML text after another successful build.
The independent final result verifier checked all five original/strict/withdraw
cases, exact policy SHA256, native rejection reasons, original generated
comment, real converter retention and release version.

**Scientific interpretation:** on this frozen realistic but minimal SysML
model, an `@Checked` reference is accepted based on the truth of the **cited
declaration** while its separately supplied **textual claim** is not checked.
This is not false proof acceptance by the Lean kernel, an exploit of arbitrary
JPL models, or evidence that any existing scientific result is wrong. The
underlying policy choice is whether the optional string is an *authoritative
typed claim* or merely *untrusted human commentary*. The candidate refusal
policy is deliberately conservative: legitimate, correct optional statements
would also be rejected until a more expressive typed checker is specified.

**Trial status:** a separate Metalogic fork candidate
[commit de056636](https://github.com/metalogiclabs/PropertyKindCalculus/commit/de056636b6c6fa60d5158db04e6a7e6175e62e81)
contains a small source correction, scope note and regression test. Its own
CI is **NOT qualified** because the source-ancestor preflight failed in a
shallow checkout. The fully executed V4/V5 ephemeral original/strict/withdrawal
policy tests are independently green, but this does not magically qualify a
separate unexecuted fork workflow. No JPL PR was opened and no message sent.

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
