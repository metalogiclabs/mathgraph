# MathGraph Check: opt-in mathematical evidence host (V1 research)

**Read-only, bounded evidence observation. Not a deployed GitHub App feature,
formal intent certificate, or authorization to merge.**

`math-source-github-host-v1.mjs` obtains GitHub API observations using an
installation-scoped token that the existing authenticated worker supplies. It
does not mint MathGraph's separately qualified intent receipts, post comments,
approve reviews, publish Check Runs, or mutate repositories.

The host independently checks five things:

1. The PR's current base/head repositories and exact head commit.
2. A GitHub Actions replay run for that same head, with the expected workflow
   ID/path, completed success, and correct owning repository.
3. The actual workflow file at the run commit has a SHA-256 **supplied by a
   trusted app administrator outside the PR**, not derived from PR metadata.
4. The expected replay job and all mandatory verification steps succeeded;
   one same-run, non-expired artifact has a GitHub-recorded SHA-256 digest and
   was created after the current attempt started.
5. A distinct human reviewer in the **independently configured GitHub user-ID
   allowlist** submitted an `APPROVED` review on the exact head with an explicit
   source/claim/theorem/environment hash declaration. A later dismissal or
   change request withdraws the observation. Ordinary `LGTM` is insufficient.

The current observation contract accepts only **GitHub Actions attempt 1**. The artifacts API associates artifacts with a workflow *run* but provides no dependable artifact-to-attempt identity; a successful rerun must not inherit an earlier artifact. Start a fresh run instead. This deliberately conservative restriction can be relaxed only after attempt-specific evidence is authenticated.

Before returning, the host re-fetches the PR head and workflow run to detect
head changes or reruns during observation. Missing APIs, pagination limits,
duplicates, unreviewed workflow bytes, stale artifacts, revocations, and forged
identity fields return `UNKNOWN`. Everything remains `ADVISORY_ONLY` with a
neutral conclusion and `intent_verification=NOT_ESTABLISHED`.

## Trusted invocation

```js
import {observeGitHubMathSource} from './math-source-github-host-v1.mjs';

const report=await observeGitHubMathSource({
  repository:'owner/repository',
  pr:42,
  runId:12345678,
  token:installationScopedReadToken,
  trusted:{
    repository:'owner/repository',pr:42,
    headSha:authenticatedCurrentHeadSha,
    workflowPath:'.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml',
    workflowSha256:administratorAuditedWorkflowDigest,
    workflowId:administratorApprovedWorkflowId,
    jobName:'pinned-artin-replay',
    artifactName:'mathgraph-proofnet-artin-evidence',
    approvedReviewerIds:administratorApprovedHumanIds,
    sourceSha256:independentlyPinnedSourceDigest,
    claimSha256:independentlyPinnedClaimDigest,
    formalSha256:independentlyPinnedFormalStatementDigest,
    environmentSha256:independentlyPinnedLeanEnvironmentDigest,
  },
});
```

All `trusted` values must come from independently configured, access-controlled
host policy or a trusted head readback. **Never copy them from a proposed PR,
workflow artifact, AI-generated statement, or reviewer's self-declared identity.**

The human writes a GitHub **PR review** with `state=APPROVED` and a body
containing exactly this JSON shape, replacing all sample digests with real
observed hashes:

```json
{
  "schema":"mathgraph.source-to-formal-review.v1",
  "source_sha256":"<64 lowercase hex>",
  "claim_sha256":"<64 lowercase hex>",
  "statement_sha256":"<64 lowercase hex>",
  "environment_sha256":"<64 lowercase hex>",
  "verdict":"SOURCE_TO_FORMAL_REVIEWED"
}
```

This review records a human's explicit, scoped comparison. It does not make
the comparison infallible, prove mathematical semantic equivalence, or grant a
merge permit. The app cannot designate itself a qualified human reviewer.

## Scope left open

- The artifact's bytes are **not downloaded** by this V1 host. It trusts
  GitHub's run/job/artifact metadata only after separately pinning the workflow
  source; its evidence scope is explicitly `GITHUB_RUN_JOB_AND_ARTIFACT_METADATA`.
- It does not yet fetch and independently hash the original mathematical source
  or the resolved Lean dependency manifest; policy values remain external.
- It does not yet create authenticated `mathgraph.intent-probes.v1` receipts or
  supply qualified authority to `auditMathSource`. Its report always includes
  `receipt_qualification=NOT_YET_CONTRACT_BOUND`.
- No reviewer has yet provided this explicit Artin attestation, and the new
  host has not been installed or deployed. The public research CI replay alone
  does not suffice to claim a complete source-to-formal warrant.

Run negative controls with:

```bash
node integrations/mathgraph-check-github/math-source-github-host-v1.test.mjs
```

This V1 is an opt-in candidate for application wiring and independent security
review, not a default required status check.
