# MathGraph Check: mathematical source-to-Lean evidence adapter V1

**CANDIDATE — pure PR-ready advisory payload, not an installed feature or
deployed mathematical verifier.** No GitHub API calls, webhooks, source fetches,
reviewer authentication, native Lean execution, PR comments, or repo writes.

The product problem is separate from successful proof compilation: a theorem
can pass Lean while failing to capture the intended meaning of its source.
Open Math Model's harness already pins Lean statements for proof verification.
This adapter records whether two further **distinct, exact-head** obligations
have independently qualified evidence:

1. `SOURCE_TO_FORMAL_REVIEWED`: an authenticated and independently qualified
   *human* source/theorem meaning-review receipt was observed.
2. `FORMAL_REPLAY_PASSED`: an authenticated and independently qualified *Lean
   replay* receipt was observed for the pinned statement/environment.

Absence, conflict, mutation, or unqualified evidence gives `UNKNOWN`. Even two
observed receipts give only `OBSERVED` within the declared bounded contract,
**never** proof of natural-language intent equivalence:
`intent_verification=NOT_ESTABLISHED`, `permission=ADVISORY_ONLY`. The proposed
Check Run is always `neutral`, and its rendered output explicitly disclaims
merge authorization. A neutral conclusion is not an endorsement and must never
be presented as a proof or enforced as an approval gate.
The math-source Check Run uses its own name and external ID to avoid colliding
with the existing generic MathGraph Check advisory run on the same commit.

## Interface

```js
import {
  buildMathIntentContract,auditMathSource,toAdvisoryCheckRun
} from './math-source-check-v1.mjs';

const probeContract=buildMathIntentContract(manifest);
const report=auditMathSource(manifest,authenticatedReceipts,trustedAuthority);
const proposedGitHubPayload=toAdvisoryCheckRun(report,trustedHeadSha);
```

`manifest` has exact fields:

```json
{
  "schema":"mathgraph.math-source.v1",
  "subject":{"repository":"owner/repo","pr":12,"base_sha":"<40hex>","head_sha":"<40hex>"},
  "source":{"reference":"https://...","sha256":"<64hex>","claim_sha256":"<64hex>"},
  "formal":{"path":"Proofs/Theorem.lean","statement_sha256":"<64hex>","environment_sha256":"<64hex>"},
  "checks":{
    "review":{"oracle_sha256":"<64hex>","verifier_sha":"<40hex>"},
    "replay":{"oracle_sha256":"<64hex>","verifier_sha":"<40hex>"}
  }
}
```

All receipts use the existing strict `mathgraph.intent-probes.v1` receipt
format and bind to `digestContract(probeContract)` and the exact head and
probe input hashes. The host must independently construct `trustedAuthority`
with existing intent fields `allowedRepositories`, `expectedHeadSha`,
`expectedContractSha256`, `authenticatedReceiptIds`,
`qualifiedVerifierShas`, and `qualifiedOracleShas`, **plus** separate
`qualifiedHumanReviewReceiptIds`, `qualifiedLeanReplayReceiptIds`, and
`observedSourceSha256`, `observedClaimSha256`, `observedFormalSha256`,
`observedEnvironmentSha256`. None may be copied uncritically from a PR,
AI output, a self-hashed file, or a forged CI status. Authenticate human
identity and Lean toolchain/axiom constraints in that external authority.
The payload builder separately requires the host's authenticated `trustedHeadSha`;
it rejects a Check Run targeted at a different, PR-authored head SHA.

## Qualification and negative controls

Run from repository root:

```bash
node integrations/mathgraph-check-github/math-source-check-v1.test.mjs
node --test integrations/mathgraph-check-github/*.test.mjs
```

The first test uses synthetic qualified receipts to exercise the policy,
then removes human or Lean authority independently, alters source/theorem/
environment/head, duplicates receipts and adds in-band forged approvals.
The pinned external `marcusm117/ProofNet-Verified` `Artin_exercise_2_2_9`
fixture, commit `14879cb23e078d122adecd9578dd26a7304f753b`, includes
three changed statement controls. They all remain `UNKNOWN` with no
independent authority. That benchmark's public statement ends in `sorry`;
**we have not obtained a new human source-to-formal review**.

The separate research workflow
`.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml` attempts a
**real, isolated Lean 4.28 replay** of the archived Artin gold proof. It pins
the upstream commit, exact source, extracted gold proof, and proof archive
hashes. Its small preflight reads one member from the zip at runtime without
publishing the gold proof, checks against altered source/archive/formal text,
then uses Mathlib `v4.28.0` and parses `#print axioms` for the theorem. An
unrecognized or missing axiom report fails closed; only `propext`,
`Classical.choice`, and `Quot.sound` are accepted. The intended output is
machine-only preflight and axiom evidence, never an automatic human review or
`qualifiedLeanReplayReceiptId`. **Until the native CI run succeeds and is
independently authenticated, replay evidence remains `UNKNOWN`.** The latest
ProofNet statement project instead targets Lean 4.34, so this archived replay
is not proof of a 4.34 replay.

This finite experiment does not outperform exact-text comparison or prove
semantic fidelity. Before offering this to the Open Math Model community,
qualify a real reviewer-authenticated statement mapping, authenticate and bind
a successful archived Lean replay run with its full environment hash, implement the independently sourced
host, and test against a comparably informed strong baseline on untouched
third-party formalizations. Public source use requires license/consent review.
