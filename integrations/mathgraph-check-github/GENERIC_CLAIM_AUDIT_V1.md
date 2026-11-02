# Generic formal-claim comparison: operator-only v1

This is a reusable *formal-statement comparison*, not a source-to-paper fidelity
certification or a deployed GitHub PR checker. It extends the experimental
MathGraph assurance toolbox beyond the two registered `@MathGraph` examples,
without modifying the live mention handler or its allowlist.

## What this verifies

An operator supplies a trusted reference Lean source, its independently
obtained exact SHA-256, and a candidate Lean source. The runner binds both byte
hashes, executes real pinned SemantEq locally, retains the native JSONL output,
and refuses to certify a formal relationship without the expected tool metadata,
native exit code, matching case ID, and successful elaboration of both statements.

Only `ExactMatch`, `DefEq`, and `EquivalentRestricted` become
`NATIVE_CERTIFIED_EQUIVALENT` **at the formal-statement layer**. This is limited
to what SemantEq proves about the elaborated formal declarations; it is not
proof that either declaration expresses the researcher's original intention.
Directional signals, timeouts, inconclusive cases, and failures become
`UNKNOWN`, not `ALTERED`. A declaration's proof body is **not** verified by
SemantEq. The separate `qualifyOriginalRepair` contract requires source build,
original-target consumer replay and a clean axiom audit; this v1 does **not**
automatically produce arbitrary repaired proofs. The separate native consumer
runner *does* execute an operator-authored, independently byte-anchored
original-target consumer in the same pinned environment, and audits the
consumer theorem's actual axioms through a separate compiler invocation.

Every report retains distinct fields: `formal_statement_relation`,
`candidate_source_build`, `intent_fidelity`, `evidence_warrant`. The last two
always remain `UNKNOWN` absent genuinely independent evidence. In particular,
no self-authored human-review field, green CI status or model confidence is
accepted as independent mathematical authority.

## Pinned native tool

- SemantEq source: `f92767000e14d11744580946980cf874324f5d19` (`v1.4.0`).
- Lean toolchain: 4.30.0-rc1; tracked `lean-toolchain` SHA-256:
  `1098ca8368e0db12138f33b070187e1f6527984ae0451a587b20e3e661f96a76`.
- Resolved manifest SHA-256:
  `cafd720ea1ea51f4c8653d5dca284ebcfc7ca16fdfb1a2a1499c71ad6408a666`.
- Manifest Mathlib commit: `0c154d67103f74be3a0f2c509f72ccbf5be9f2a7`.
- The runner also independently checks the actual local Mathlib Git HEAD and
  tracked-source cleanliness, records the SemantEq executable's SHA-256, and
  records real `lake --version` and `lake env lean --version` output.
- Native invocation: `lake env .lake/build/bin/semanteq --timeout 12 INPUT OUTPUT`,
  with a separate wall-clock ceiling, using a private temporary directory.

The compiled executable's supply chain is not authenticated against a signed
attestation. This is reproducible *local evidence*, not independent review.

## Command

After separately installing and building the pinned SemantEq tool, on
**operator-reviewed, first-party** local files:

```sh
node integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs \
  --reference /trusted/Original.lean \
  --candidate /trusted/Candidate.lean \
  --reference-sha <64-hex-sha256-from-trusted-source> \
  --project /trusted/semanteq_upstream \
  --output /private/evidence/claim-audit.json
```

To additionally replay the proof against the original trusted target, provide
an **independently authored and reviewed** `Consumer.lean` that imports
`Candidate` and declares a named consumer theorem. The consumer must reproduce
the original target, including quantifiers and hypotheses; this mathematical
correspondence is not established by the CLI.

```sh
node integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs \
  --reference /trusted/Original.lean \
  --candidate /trusted/Candidate.lean \
  --reference-sha <trusted-reference-sha256> \
  --consumer /trusted/Consumer.lean \
  --consumer-sha <independently-authorized-consumer-sha256> \
  --consumer-name MathGraphConsumer.original_claim \
  --project /trusted/semanteq_upstream \
  --output /private/evidence/combined-claim-audit.json
```

The combined command compiles `Candidate.lean` and `Consumer.lean` as separate
modules and generates a third audit module with `#print axioms` for the selected
consumer. It checks identical source and environment pins for the comparison
and replay within the same operator invocation. Axiom output containing
`sorryAx` or any nonstandard axiom leaves `original_target_status: UNKNOWN`,
even if all three Lean compilations exit zero.

Native replay uses a uniquely named temporary subdirectory of the ignored
`.lake/build` tree. This matters for concurrent jobs: a root-level untracked
Lean source caused SemantEq to mark the source checkout dirty and fail closed.
The explicit parallel-native test covers that regression.

`--output` must not exist. The CLI never overwrites an existing report and
returns exit code 2 on environment or execution failure. Exit code 0 means the
configured tools *ran*, not that the candidate is mathematically warranted.
The JSON report holds
original input JSONL, raw SemantEq output, stdout/stderr, exact source hashes,
input/output hashes, command arguments, source revision, toolchain and manifest
hashes, Lean/Lake versions, measured wall-clock time and distinct assurance statuses. Keep reports
private if the supplied sources are private.

```sh
node integrations/mathgraph-check-github/generic-claim-audit-v1.test.mjs
node integrations/mathgraph-check-github/generic-semanteq-cli-v1.test.mjs
node integrations/mathgraph-check-github/generic-lean-consumer-run-v1.test.mjs
MATHGRAPH_SEMANTEQ_PROJECT=/trusted/semanteq_upstream \
  node integrations/mathgraph-check-github/generic-semanteq-run-v1.test.mjs
```

The optional native tests use a previously built pinned tool and an
unregistered `Init` arithmetic pair; they skip only when the project variable
is not set. Do not interpret a skipped native test as native success.

## Safety and cutover

Lean elaboration can run user-authored macros and elaborators. **Do not connect
this CLI to arbitrary GitHub PR content** without a separately reviewed,
network-isolated execution sandbox and resource controls. The existing live
`@MathGraph -check` / `-fix` adapter is deliberately unchanged. Any future
public App integration needs a positive original-claim consumer, byte-pinned
same-run proof/environment receipts, independently authorized source intent,
and red-team tests for receipt replay, custom axioms and stale commits.
