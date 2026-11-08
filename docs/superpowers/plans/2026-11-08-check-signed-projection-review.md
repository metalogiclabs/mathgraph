# Signed Projection Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A candidate finite obstruction is reported as source-qualified only when a separate trusted reviewer signed its exact packet.

**Architecture:** A pure Ed25519 verifier accepts a canonical signed envelope, derives the exact existing finite claim authority, and calls `checkProjectionClaim`. It is an optional admission route, not a rewrite of Check or a public deployment.

**Tech Stack:** Node ESM `node:crypto`, `node:test`, current projection checker.

**Spec:** `docs/superpowers/specs/2026-11-08-check-signed-projection-review-design.md`

## Global Constraints

- The public key trust root is out-of-band; never accept an in-band key as authoritative.
- Unknown reviewer, stale source, tampering and missing evidence reference fail closed.
- Review signature is not independently replayed proof or universal correctness.
- Keep default GitHub runner unchanged and no external writes.

## Review Focus

- Canonical JSON field order must not invalidate authentic signatures.
- Changed statement, witness row or evidence digest must invalidate admission.
- A valid envelope at an old PR SHA cannot block a new head.
- Unknown key IDs or malformed signatures must not throw or admit.
- A signed non-collision still cannot imply universal positive sufficiency.

---

### Task 1: Pure signed-review admission

**Files:**
- Create: `integrations/mathgraph-check-github/signed-projection-review-v1.mjs`
- Create: `integrations/mathgraph-check-github/signed-projection-review-v1.test.mjs`
- Update: `integrations/mathgraph-check-github/INTENT_WARRANT_V1.md`

**Interfaces:**
- Consumes: `checkProjectionClaim`, `digestProjectionClaim`, `hashFiniteUniverse`.
- Produces: `projectionReviewBytes(payload)` and `admitSignedProjectionReview(subject,envelope,trustedKeys)`.

- [x] Write failing tests for a legitimately signed packet, changed statement,
      changed source SHA, tampered protected row, absent evidence, unknown key,
      malformed signature and signed finite no-collision.
- [x] Run `node --test integrations/mathgraph-check-github/signed-projection-review-v1.test.mjs` and observe expected RED.
- [x] Implement strict envelope validation, Ed25519 verification and existing
      projection checker bridge; return advisory UNKNOWN for every failure.
- [x] Run targeted tests and all integration tests; record pass/skip boundaries.
- [x] Document signature/proof distinction, run `git diff --check`, commit.

### Task 2: Authenticated Check readback signed route

**Files:**
- Modify: `integrations/mathgraph-check-github/authenticated-cycle-v1.mjs`
- Modify: `integrations/mathgraph-check-github/authenticated-cycle-v1.test.mjs`
- Update: `integrations/mathgraph-check-github/INTENT_WARRANT_V1.md`

**Interfaces:**
- Consumes: `admitSignedProjectionReview(subject,envelope,trustedKeys)`.
- Produces: optional `signedProjectionReview` and `trustedReviewerKeys` on
  authenticated `githubSnapshot` (no default workflow changes).

- [x] Write failing tests for a valid signed review, a forged review that stays
      UNKNOWN even with green CI, changed head withdrawal, and ambiguous double
      authority inputs.
- [x] Run targeted test to observe RED.
- [x] Call signed admission after authoritative current PR head readback, and
      keep the previous trusted host API available but mutually exclusive.
- [x] Run targeted and full integration tests; commit the bounded change.

## Qualification record

- RED: absent `signed-projection-review-v1.mjs` failed module import. GREEN: five
  signed-review tests. RED: four authenticated-cycle tests failed because signed
  inputs were ignored. GREEN after optional signed admission integration.
- Self-review found a missing no-native-Check case: invalid signature raised
  `NO_INDEPENDENT_CHECKS` instead of an explicit UNKNOWN. New test reproduced
  the failure, the bounded fix passed, and the original unsigned path retained
  its fail-closed behavior.
- Final full Node sweep: **612 total, 601 passed, 11 skipped, 0 failed**.
  The Python `pytest` suite was not run (`pytest` was unavailable in this
  environment). No Lean proof bytes or external artifact were replayed here.
- Final review: self-review only, not an independent reviewer; release and
  proof-byte verification are still UNKNOWN. The `pull_request` workflow runs
  PR merge-ref code, so trusted-policy injection belongs in a separately
  controlled execution context; no such deployment is made here.
