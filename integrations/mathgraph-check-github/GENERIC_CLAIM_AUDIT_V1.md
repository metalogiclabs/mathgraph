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
That Lean acceptance does not establish *essential use* of the candidate:
the consumer might independently prove the target using a library theorem.

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

## Optional proof-use diagnostic (unbound)

For an independent *operator-authored* proof-relevance fixture, add both
`--proof-fixture /trusted/ProofUse.lean` and
`--proof-fixture-sha <independently-obtained-SHA256>` to the command above.
The fixture is expected to contain a hypothetical candidate theorem assumption
and a reference-target proof using (or failing to use) it. No single-argument,
unpinned option is accepted.

The CLI byte-checks and privately stages this fixture, then invokes the pinned
upstream proof checker as:

```sh
lake env .lake/build/bin/semanteq --raw --strict --proof /private/staged/ProofUse.lean
```

Its separate `proof_fixture_audit` records `PASS`, `FAIL` or `UNKNOWN`, the
actual exit code, SHA-256, captured stdout/stderr, elapsed time, upstream
verdict and environment pins. A parsed verdict of `FAIL` with native exit zero
is **not** an environment failure. Multiple/malformed records and nonzero exit
codes fail closed. `proof_same_run_correlation` checks the formal comparison
and proof fixture against the same pinned local executable, Mathlib revision,
toolchain, manifest and Lean/Lake versions within the CLI invocation.

**Important:** `proof_binding: UNBOUND_ADVISORY` is permanent in this v1.
The checker has not verified that the fixture's candidate assumption and goal
are the actual elaborated declarations in the trusted reference and candidate
files. Even `PASS` with matching environment is *not* candidate repair approval,
proof-to-paper fidelity, independent review or mathematical warrant.
`original_target_status` is not upgraded from this diagnostic;
`intent_fidelity` and `evidence_warrant` remain `UNKNOWN`. Binding the fixture
to exact elaborated theorem types is available separately through the
operator-only binding extension below. The fixture is not executed
from a GitHub webhook or arbitrary PR. Preserve raw output privately when its
source is sensitive.

## Optional exact-declaration native type binding

To request a *separate* native binding receipt, add all four names to the
byte-pinned proof fixture command. These refer to the real theorem declarations
in the exact reference/candidate source files and in the proof fixture:

```sh
  --proof-reference-name Original.target \
  --proof-candidate-name Proposed.candidate \
  --proof-assumption-name assumed_candidate \
  --proof-goal-name proof_goal
```

The binding runner independently compiles the staged exact source bytes into
`Reference.olean`, `Candidate.olean` and `ProofFixture.olean`, then compiles two
generated Lean audits: reference versus fixture goal, and candidate versus
fixture assumption. They require each named constant to be a theorem
*originating in its nominated staged module*, not merely an imported Mathlib
declaration. Lean `Meta.isDefEq` compares the full elaborated types, including
all quantifiers, premises and the conclusion; a textual name match alone never
qualifies. Separate audit modules allow the original and candidate to use the
same full theorem name without importing them together.

`proof_type_binding` preserves both type-comparison results, the actual
compiler trace/exit/logs, exact source hashes and pinned environment. An
accepted native ProofChecker verdict `PASS`, exact ProofChecker-selected
assumption and goal names, two native definitionally equal type comparisons,
byte-identical fixture/source pins and matching toolchain may yield
`bound_fixture_proof_use: NATIVE_TYPE_BOUND_FIXTURE_USE`. This is a type-bound
**hypothetical** proof-use result: the fixture assumed a theorem of the
candidate's type but did not consume the actual candidate proof constant.
`candidate_dependence` therefore still remains `UNKNOWN`.

This is **not mathematical research-intent warrant**. The candidate may itself
be sorried or axiom-dependent; the proof target may not express the paper's
claim; the operator-authored binding does not authenticate independent human
review. Accordingly `intent_fidelity` and `evidence_warrant` remain `UNKNOWN`.
A native `false` establishes non-definitional equality, **not** semantic
inequivalence: the bounded result is `UNKNOWN`, not `ALTERED`. A library bypass
can have both theorem types bound but still returns `bound_fixture_proof_use:
UNKNOWN` because ProofChecker rejects essential use.

Supported sources must compile as independent staged modules under the pinned
toolchain. Extra sibling imports, source-name collisions with the fixture,
unavailable dependencies and environment drift fail closed. This is not yet a
general import/repackaging service for the 14-module Kakeya export. No GitHub
App publication or webhook route was added.

## Optional actual candidate proof-term reference observation

With a separately hash-pinned original-target `--consumer`, `--consumer-sha`,
and `--consumer-name`, the operator may add:

```sh
  --consumer-candidate-name Proposed.candidate
```

This runs in the **same native Consumer replay** as the existing exact-source
Lean compilation. The generated audit requires the named candidate theorem to
originate in the staged `Candidate.olean` and the target theorem in the staged
`Consumer.olean`; imported/library impostors fail. It reads the actual
elaborated Consumer theorem's proof value, applies Lean `Meta.zetaReduce` to
discard unused `have`/`let` bindings, and checks for a *direct* occurrence of
the actual Candidate theorem constant. It also captures separate `#print
axioms` output for both the candidate and the consumer. Only an exact native
positive with both axiom sets restricted to `propext`, `Classical.choice`, and
`Quot.sound` yields `actual_candidate_proof_term_reference:
NATIVE_ZETA_NORMALIZED_DIRECT_REFERENCE` in the consumer replay receipt.

This is stronger than a text search, raw constant occurrence, or the previous
hypothetical assumed-fixture binding. A native control with an unused candidate
`have` retains the candidate's axioms in its *raw* theorem audit but loses the
candidate constant after zeta reduction; it is correctly not promoted. The
positive uses the actual compiled candidate theorem and the actual consumer
proof term. Nonetheless, a remaining reference is **not proof of mathematical
necessity**: an alternative proof could exist, transitive references via
helper theorems may not be found, and no paper-to-Lean interpretation is
authorized. `candidate_dependence`, `intent_fidelity` and `evidence_warrant`
stay `UNKNOWN`. The operator must not imply that the real source theorem is
faithful merely because the selected consumer compiled.

The independent native first-party arithmetic test is executable with
`MATHGRAPH_LEAN_BIN=/trusted/lean node --test
integrations/mathgraph-check-github/generic-candidate-proof-reference-v1.test.mjs`.
The script uses exact imported module boundaries and checks dependent, library
bypass, dead touch and wrong-module cases. No third-party SemantEq native suite
result is attributed to this standalone test. Unavailable pinned environments
yield `UNKNOWN`, never a forged Lean rejection or accepted proof.

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
node integrations/mathgraph-check-github/generic-proof-relevance-run-v1.test.mjs
node integrations/mathgraph-check-github/generic-proof-type-binding-run-v1.test.mjs
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
