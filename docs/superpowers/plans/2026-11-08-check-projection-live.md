# Check Projection Gap Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A qualified projection collision becomes a source-bound Check result, permitted Resolve proposal, and revocable Monitor state in the authenticated GitHub cycle.

**Architecture:** A pure adapter converts the existing finite quotient evidence into the product's advisory claim contract. `githubSnapshot` optionally calls it after independently reading the current PR SHA, combines the resulting claim, and reuses `resolve` and `compareSnapshots`/`monitor` unchanged.

**Tech Stack:** Node ESM, `node:test`, existing authenticated GitHub readback and finite warrant quotient modules.

**Spec:** `docs/superpowers/specs/2026-11-08-check-projection-live-design.md`

## Global Constraints

- No live GitHub writes, Cloudflare webhook changes, automatic merges or deploys.
- Trust policy must be a separate host-controlled input, never PR payload.
- Exact PR-head binding and UNKNOWN on missing or changed evidence.
- No universal positive correctness promotion.

## Review Focus

- A source-mismatched historical witness must not block a new PR.
- A provenance-only collision must not become a semantic no-go.
- A finite no-collision result must remain UNKNOWN for full claim sufficiency.
- An old BLOCKED state must withdraw on new PR head without fresh admission.
- Self-originating MathGraph Check runs must not qualify witness authority.

---

### Task 1: Pure source-bound claim adapter

**Files:**
- Create: `integrations/mathgraph-check-github/projection-claim-v1.mjs`
- Test: `integrations/mathgraph-check-github/projection-claim-v1.test.mjs`

**Interfaces:**
- Consumes: `checkFiniteWarrantQuotient(universe,authority)`.
- Produces: `checkProjectionClaim(subject,{id,statement,universe},authority)` returning `status`, `results`, `claim_dependencies`, `subject` and `permission`.

- [ ] Write tests for admitted target collision, provenance-only collision,
  finite preserved, missing authority, changed SHA and malformed inputs.
- [ ] Run `node --test integrations/mathgraph-check-github/projection-claim-v1.test.mjs`.
  **Expected:** RED because module does not yet exist.
- [ ] Implement pure adapter with fail-closed UNKNOWN and typed witness fields.
- [ ] Rerun the test. **Expected:** GREEN.
- [ ] Commit task 1.

### Task 2: Authenticated readback, Resolve and Monitor

**Files:**
- Modify: `integrations/mathgraph-check-github/authenticated-cycle-v1.mjs`
- Modify: `integrations/mathgraph-check-github/authenticated-cycle-v1.test.mjs`
- Update: `integrations/mathgraph-check-github/INTENT_WARRANT_V1.md`

**Interfaces:**
- Consumes: `checkProjectionClaim` from task 1.
- Produces: optional `projectionClaim` and separate `projectionAuthority` inputs
  on `githubSnapshot`, with combined advisory results and existing `resolve`/
  `compareSnapshots` behavior.

- [ ] Add failing tests for current-head qualified witness, allowed Resolve
  proposal, unchanged generic behavior, stale-head withdrawal and self-check
  exclusion.
- [ ] Run `node --test integrations/mathgraph-check-github/authenticated-cycle-v1.test.mjs`.
  **Expected:** RED in the new assertions.
- [ ] Wire the adapter only after authenticated GitHub source readback.
- [ ] Rerun relevant and full GitHub integration tests. **Expected:** GREEN.
- [ ] Update scope documentation and commit task 2.
