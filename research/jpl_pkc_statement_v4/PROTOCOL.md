# JPL PKC V4 — Actual API-JSON ingestion falsifier and smallest fail-closed policy

## Frozen claim and source (before V4 native outcomes)

- Unmodified NASA/JPL source: `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`; `leanprover/lean4:v4.34.0`.
- Prior independent native result: [V3 #39174459130](https://github.com/metalogiclabs/mathgraph/actions/runs/39174459130), validated the actual citation gate and generated-module compiler with an internally created `PkcModel`.
- V4's additional claim: **the real `scripts/ingest-sysml.lean` API-element entry point can accept a model with `@Checked.statement = "False"` when its `@Checked.decl` names a real, unrelated kernel-checked proposition**. This tests the ingest path below external SysML conversion, not merely a manually constructed neutral record.
- The external OpenSysML binary, SysML text parsing and reverse round trip are **NOT** executed by this test. The JSON input deliberately uses the same API-element form as the repository's `Tests.Interchange.ApiJson` fixture.

## One frozen native input family

One `#kind width` source model, scale ratio, one `@Checked` citation to the real
`PropertyKindCalculus.Iso80000.Part3.Edge.width_length` constructor. Generate the
API-element JSON using JPL's own `ApiJson` test fixture constructors, but do
not invoke a mocked citation verifier.

Six cases:

1. `no_statement` — correct proof citation, no prose statement: **must be admitted**.
2. `false_statement` — same correct proof but optional `statement = "False"`: **expected currently admitted; strict policy must reject**.
3. `true_statement` — identical except `statement = "True"`: **expected currently admitted; strict policy must reject**.
4. `missing_declaration` — name is absent: **must reject**.
5. `data_citation` — `Nat.add` is data/function, not evidence: **must reject**.
6. `axiom_citation` — `propext` is an axiom: **must reject**.

The `no_statement` positive and the three invalid-declaration negatives must
produce the **same** verdict before and after the repair. The original parser
and its native `Harvest.unverifiedCitations` are the authority for actual
accept/reject outcomes. A `True`/ `False` pair should not be interpreted as
a semantic string parser: they are deliberately conflicting **unverified prose**.

## Minimal proposed policy, restricted to the isolated test checkout

Instead of pretending arbitrary printable strings provide typed Lean propositions,
make optional free-form `@Checked.statement` **fail closed** at
`Harvest.unverifiedCitations`:

`if c.statement.isSome then out := out ++ ["... unchecked statement text ..."]`

Retain every existing source and proof-validity check. This policy is **not**
a general solution for carrying explanatory statements across SysML; it
safely refuses to certify their content until a typed, explicitly specified
statement-to-Expr correspondence is implemented. Metadata users may need
a distinct non-authoritative note field to preserve backward compatibility.

Apply the pinned patch only in the CI checkout after testing the unmodified
source. Never modify or PR JPL's repository. After patching, compare original
and strict gates on the same six input JSON blobs.

## Required causal controls

- Original `scripts/ingest-sysml.lean` MUST accept both `false_statement` and
  `true_statement`, and reject missing/data/axiom; otherwise the old claim
  is not promoted and the run fails scientific expectation.
- Generated original `false_statement` Lean module must compile with
  `-- checked: ... — False` present solely as a comment; it must not contain
  a theorem of `False`.
- The patch must be exact-context with original content SHA recorded,
  must not alter the frozen six JSON files or exact external dependencies.
- Strict gate MUST reject `false_statement` and `true_statement`, while
  accepting `no_statement`, rejecting all three old negatives.
- Source patch reverted or isolated after experiment. Any unexpected source
  change or divergence is `UNKNOWN_APPARATUS` or `REJECTED_POLICY`, not success.

## Claim bounds

A passing V4 is **source-native API-JSON ingest and strict-policy
qualification on a small model**. Not full OpenSysML text ingestion,
not a theorem that Lean proves `False`, not a kernel exploit, not evidence
of actual misuse by any external author. Report both original and strict
outcomes, false positives and unverified future assumptions accurately.

No upstream writes, unsolicited PR or external communication.
