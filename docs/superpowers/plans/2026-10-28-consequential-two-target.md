# Consequential Two-Target Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the already CI-qualified protected-frame mechanism at `0aab2b4d` with exact-byte research pins, an independent second historical target, and cold Metatron causal replay without enlarging runtime authority.

**Architecture:** Add a pure opt-in source/receipt adapter to existing `assessWarrant(..., protectedFrame)`. Freeze two declarative source-specific frames; require qualified named native observations, not receipt envelope alone. Replay through unmodified source adapters and unmodified pinned Metatron Nucleus. Keep the production Worker unchanged until an authorized owner frame is available.

**Tech Stack:** Node 22+ native `node:test`, `node:crypto`; Python 3 standard library for pinned Nucleus lineage; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-28-consequential-two-target-design.md`

## Global Constraints

- Never modify `integrations/mathgraph-check-github/warrant.mjs` or the trusted Metatron Nucleus.
- Build on the two already qualified protected-frame commits `8faaf2fa` and
  `0aab2b4d`; this work must not claim their GOETH repair as newly discovered.
- Preserve the GOETH two RED semantic counterexamples in `goeth-v19-pilot.test.mjs`.
- Fixed source/report/artifact pins; native adapters remain authoritative within their declared historical boundary.
- No production Worker flag, secret, GitHub Check promotion, grant issuance or external action.
- Claims use `WARRANTED_BOUNDED`, `UNKNOWN`, `REJECTED`, `REUSABLE` and `SUPERSEDED` at explicit boundaries.

## Review Focus

- Forged `verifiedOwner` object bypassing actual signature verification: caller must pass the result of the existing verifier; the assessor may not claim independent cryptographic authentication.
- Digest and subject mismatch: return `ABSTAIN`, never throw an accidental `ADMIT`.
- Missing or duplicate required obligations: reject the frame or signed packet; omission cannot reduce the requirement set.
- Repeated/stale native receipt status, missing/mismatched native observation, or
  source mismatch: withdraw derived statuses, preserve negative history.
- A valid unexpired grant cannot override unknown/false obligations; a verified native pass cannot create an external owner grant.

---

### Task 1: Pure independent obligation-frame assessor

**Files:** Create `integrations/mathgraph-check-github/consequential-frame.mjs`; test `integrations/mathgraph-check-github/consequential-frame.test.mjs`.

**Interfaces:** `assessConsequentialFrame({snapshot,verifiedOwner,frameBytes,frameSha256,nativeReceipt,asOf}) -> {boundary,decision,residuals,future,missing_observations,...}`; delegates to existing protected-frame `assessWarrant` without modifying it. `nativeReceipt` and `observations` are trusted adapter-side inputs, not untrusted signed packet fields.

- [ ] Write tests for exact frame, signed omitted obligation, signed falsely true, fully qualified positive, false negative, expiry, revocation, wrong head, wrong digest, native receipt withdrawal and duplicate definitions.
- [ ] Run `node --test integrations/mathgraph-check-github/consequential-frame.test.mjs`; expected RED due missing module.
- [ ] Implement schema, digest/subject, complete-name checks and status reconciliation, reusing the existing warrant grant evaluator.
- [ ] Run the new tests and the preexisting `goeth-v19-pilot.test.mjs`; expected GREEN and old negative retained.
- [ ] Commit Task 1 files and record test results.

### Task 2: Two source-native framed cases and equal-information baseline

**Files:** Create `integrations/mathgraph-check-github/fixtures/consequential-goeth-v19.v1.json`, `.../consequential-goccy-pr958.v1.json`, `integrations/mathgraph-check-github/consequential-two-target.test.mjs`, `integrations/mathgraph-check-github/consequential-two-target-replay.mjs`.

**Interfaces:** The same `assessConsequentialFrame` and fixed source profiles; a report-only runner outputs exact decisions, negative lineage, baseline counts and epistemic boundaries, never a GitHub Check write.

- [ ] Write tests for both exact subjects, native adapter outcomes, non-vacuous positive, inherited residual, no cross-source status transfer, withdrawal and independent conventional baseline TIE.
- [ ] Run `node --test integrations/mathgraph-check-github/consequential-two-target.test.mjs`; expected RED due missing replay module/fixtures.
- [ ] Add reviewed research frames and pure replay utility; no per-target evaluator branches.
- [ ] Run both new test files and the existing external-receipt/geth tests; expected GREEN.
- [ ] Commit Task 2 and record source/fixture digests.

### Task 3: Metatron history and cold-replay causal withdrawal

**Files:** Create `integrations/mathgraph-check-github/consequential-metatron-replay.py`, `integrations/mathgraph-check-github/consequential-metatron-replay.test.mjs`.

**Interfaces:** Python bridge imports *exact pinned* `runtime.metatron.nucleus` through an explicit read-only checkout path; records source, qualified frame/receipt, derived decision, revoke, and unrelated target; dumps/loads and checks selective `live_ids`. It has no action API.

- [ ] Write test that fails until real pinned Nucleus replay and source-withdrawal descendant cut exist.
- [ ] Run `node --test integrations/mathgraph-check-github/consequential-metatron-replay.test.mjs`; expected RED.
- [ ] Implement a small stdlib-only import/JSONL driver; require `METATRON_SOURCE_CHECKOUT` and exact source pin/hash; fail closed if absent.
- [ ] Run fresh local test with the separately cloned Metatron checkout; expected GREEN with source withdrawal, preserved independent target, and cold restart.
- [ ] Commit Task 3 and record the exact Nucleus source digest.

### Task 4: Evidence, regression, and handoff

**Files:** Create `docs/research/consequential-two-target-evidence-20261028.md` and `.github/workflows/mathgraph-consequential-two-target-v2.yml` to require exact pinned Metatron checkout and run the independent CI suite; no production deployment files.

**Interfaces:** Exact reproducible commands, source refs, fixed frame hashes, 2-target evidence, baseline, negative lineage and named remaining obligations.

- [ ] Run complete `node --test integrations/mathgraph-check-github/*.test.mjs integrations/mathgraph-check-github/cloudflare/*.test.mjs` under permitted local process/loopback permissions; expected 0 failing tests.
- [ ] Run Python Metatron replay and two-target report; compare against independently checked frozen expected decisions and record actual counts.
- [ ] Write evidence report explicitly separating the packet-only counterexamples, frame repair, historical native sources, baseline TIE and L7 UNKNOWN.
- [ ] Verify `git diff --check`, no changes to trusted source or production Worker, and scoped commits.
- [ ] Commit report, prepare reviewable draft PR without merging or deploying; reconcile Research OS only with evidence-backed qualification.
