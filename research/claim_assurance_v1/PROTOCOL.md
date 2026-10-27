# MathGraph Claim Assurance V1 — independent scientific claim warrant

**Status:** Research experiment. No JPL upstream writes, installation, communication,
or production release. This source is solely owned by Metalogic Labs.

## Problem and genuine inputs

A valid PKC `@Checked.decl` identifies the Lean declaration
`PropertyKindCalculus.Iso80000.Part3.Edge.width_length`, while its separately
authored optional `@Checked.statement` can contain `False`. The exact untouched
JPL `scripts/ingest-sysml.sh` and external OpenSysML 0.9.1 CLI accept the
source text and produce a compilable Lean file where `False` appears in a
comment, not as a kernel-checked proposition. The independent checker must
not promote that comment as a proof or infer that the user intended the
optional field to be authoritative; The intended field contract is unresolved.

### Exact provenance

- Upstream: `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`
- Upstream toolchain: `leanprover/lean4:v4.34.0`
- OpenSysML: public `v0.9.1` archive, verified against release SHA256SUMS
- Source models: real PKC test-API constructors (`research/jpl_pkc_statement_v4`)
  and real `EmitSysml.emit` text rendered from those neutral PKC models
  (`research/jpl_pkc_statement_v5`)
- Actual text pipeline: `sysml -validate`, `sysml -convert api-json`, JPL
  `scripts/ingest-sysml.sh`, native `ApiJson.read`, JPL import policy,
  generated Lean and native Lean checker.
- We also run thirteen authenticated API-JSON importer cases from V4;
  those three non-proof citation controls have not been run through external
  SysML text conversion, and must not be advertised as such.
- MathGraph's checker and its withdrawal/forgery oracle are independently
  written in stdlib Python and do not import the native PKC policy helper.

## Six predeclared claim controls

| ID | Real evidence / adversarial condition | Exact authority |
|---|---|---|
| C1 | Valid citation, no optional textual assertion; original and strict real text ingest pass | `WARRANTED_CITATION_ONLY`: a named kernel-checked declaration, not a scientific theorem about physical reality |
| C2 | Authentic OpenSysML converts `statement = "False"`; original imported Lean compiles, strict proposed policy rejects | `REJECTED_UNCHECKED_STATEMENT` for claim authority; no assertion that Lean proves `False` |
| C3 | V4 actual importer receives absent declaration, `Nat.add` data and `propext` axiom references, each with genuine typed rejection | `REJECTED_INVALID_EVIDENCE`, three qualified subcases |
| C4 | V4 actual importer admits `statement = "True"` with a valid citation; strict policy rejects it | `REJECTED_UNCHECKED_STATEMENT` regardless of whether the text happens to sound true |
| C5 | Full prior evidence, but source revision changed without independent new replay | `WITHDRAWN`, not a claim that upstream became incorrect |
| C6 | One required authenticated evidence artifact removed | `WITHDRAWN`; reintroduction of unchanged evidence restores conditional warrant |

The native strict policy is only an **ephemeral, precisely pinned JPL checkout
mutation** used as causal proof of concept. Before/after withdrawal shows that
the original pipeline again admits identical `False` metadata. Regardless of
this rollback, MathGraph's independent claimed-`False` judgment remains
`REJECTED_UNCHECKED_STATEMENT`. The policy is deliberately conservative: it
would refuse harmless optional commentary too, until the authoritative claim
semantics are agreed and a typed statement interface exists.

### Independent robustness checks (not new scientific discoveries)

The checker is also challenged with five prospective alterations to an actual
completed full-source run: wrong repository revision, deleted source SysML,
forged converter literal, removed generated-Lean comment boundary, and
counterfeit strict-importer successful exit. These must fail closed. These
tests are mutations of real retained evidence, not artificial substitutions
for the original source-native tests.

## Acceptance / release boundary

Only declare `WARRANTED_BOUNDED_SELECTED_CITATION` if all of the following
hold in **one current CI job**:

1. Exact upstream SHA, Lean pin and release archive checksum match.
2. Both original PKC native input families and the original external SysML
   text conversions complete with their own independent, retained logs.
3. Real PKC original/strict/withdrawn native result matrices match all
   expected success/failure cases and typed rejection reasons.
4. The converter retains the proof citation and literal `False`, while
   actual generated Lean includes the text **only as an annotation**.
5. Six claim controls plus five withdrawal/forgery counterfactuals pass.
6. Both source revisions and report inputs are hashed into the retained
   Actions artifact, and the local JPL checkout is restored clean.
7. The workflow has a retained artifact digest. The artifact itself
   establishes a bounded result; it does not establish a general oracle
   for arbitrary SysML specifications or certify external deployments.

**Open:** generalized typed `@Checked.statement` equivalence; real
device/data measurements; complete end-to-end PKC semantics; full FGM
comparison; generalized automatic extraction; operational
adoption. Authority for these remains `UNKNOWN`.

## Reproduce

GitHub Actions workflow:
`.github/workflows/mathgraph-claim-assurance-v1.yml`

Review output:
`research/claim_assurance_v1/results/CLAIM_ASSURANCE_V1_REPORT.json` and
`research/claim_assurance_v1/results/NEGATIVE_CONTROLS.json`.

The existing V5 workflow and its real-source V4 dependency remain unchanged.
The CI source checkout is local and is never pushed to JPL. Do not construe
this demonstration or source reuse as institutional endorsement.
