# Protected review runner implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make exact signed finite-review admission plus archived proof-byte
corroboration available from a protected, source-pinned, read-only operator.

**Architecture:** Compose `githubSnapshot` and `corroborateLeanProofArtifact`,
adding independent GitHub run/job/artifact metadata readback and exact-head
race checks. A narrow CLI reads externally administered keys and policy.

**Tech Stack:** Node ESM, Node test, existing GitHub adapter and signature gate.

**Spec:** `docs/superpowers/specs/2026-11-08-check-protected-review-runner-design.md`

## Global constraints

- No production deployment, default-branch merge, GitHub write or permission
  escalation. Never run PR-authored code in a credential-bearing context.
- Only external key/policy files can supply reviewer trust; bad/missing context
  is `UNKNOWN`. No test-only signer becomes an approved external reviewer.
- Artifact matched to authenticated source run/job; no fresh Lean kernel replay.

## Review focus

- Non-default or PR context: UNKNOWN before any GitHub read.
- Artifact swapped or run/job failed: UNKNOWN even with valid signature.
- Head changes mid-run: UNKNOWN even if first GitHub read was valid.
- Missing/invalid independent key or signed packet: UNKNOWN.
- No positive universal proof or automatically authorized repair.

### Task 1: Guarded admission function

**Files:** create `integrations/mathgraph-check-github/protected-review-runner-v1.mjs`; extend `proof-artifact-corroboration-v1.test.mjs`.

**Interface:** `qualifyProtectedReview({context, signedProjectionReview,
trustedReviewerKeys, trustedProofReceipt, artifactPath, artifactId, fetcher})`.

- [x] Write the genuine synthetic ZIP/signature positive test and guarded
      negative tests; run them to RED on missing export.
- [x] Implement exact context checks, authenticated GitHub metadata readback,
      signed proof-byte gate and last-head recheck.
- [x] Run targeted tests and all Node `.test.mjs` suites, check diff, commit.

### Task 2: Protected-host CLI preparation

**Files:** create `integrations/mathgraph-check-github/run-protected-review-v1.mjs`; update product boundary doc.

- [x] Write a failing no-credentials CLI test with an exact UNKNOWN/exit boundary.
- [x] Implement file-based key/policy/packet inputs and read-only JSON output,
      with no secret or token echo.
- [ ] Publish to the existing draft PR, preserving no-deployment and
      missing-administrator-trust UNKNOWN status.

## Qualification / residual

- RED→GREEN: absent protected runner module; absent CLI; hostile `PATH`
  injection; early PR-context file-access boundary.
- Targeted protected/corroboration/CLI suites: 10/10 passed.
- Full JavaScript `.test.mjs` sweep: 636 total, 625 passed, 11 skipped,
  0 failed. Native Lean replay and Python suite not run in this slice.
- The PR's unprotected workflow tests these boundaries with synthetic keys,
  not with a real reviewer or admin-provisioned secrets.
- Actual protected-host activation, external reviewer approval and source-to-
  requirement authority remain UNKNOWN.
