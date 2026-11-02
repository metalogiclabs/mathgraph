# Native Proof-Relevance Advisory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional native SemantEq ProofChecker diagnostic to the generic operator CLI without promoting unbound proof fixtures into research-intent warrant.

**Architecture:** A small runner validates an independently pinned local fixture, checks the existing pinned Lean/SemantEq environment, executes the upstream strict proof checker and preserves raw output. The CLI joins this unbound diagnostic with its current formal statement and optional consumer receipts while keeping every authority boundary separate.

**Tech Stack:** Node.js ESM, Lean 4.30.0-rc1, pinned SemantEq v1.4.0, Node's built-in test runner.

**Spec:** `docs/superpowers/specs/2026-11-02-proof-relevance-advisory-design.md`

## Global Constraints

- Operator only; never execute arbitrary GitHub-supplied Lean code without an isolated sandbox.
- Fixture SHA-256, tool SHA, Mathlib Git, toolchain and manifest must match pinned inputs.
- `PASS` is an unbound local fixture result, not proof of current candidate dependence, intent or evidence warrant.
- Preserve all existing output schemas, statuses and failure provenance.

## Review Focus

- A synthetic PASS object cannot become a native receipt; only subprocess output can.
- A wrong source SHA rejects before tool execution.
- Malformed/multiple JSON records fail closed, without silently marking PASS.
- Runtime FAIL may still exit process zero; distinguish process success from proof-checker verdict.
- A clean consumer that bypasses candidate proof must not be promoted by a separate unbound fixture.

---

### Task 1: Introduce a byte-pinned native fixture audit

**Files:** Create `integrations/mathgraph-check-github/generic-proof-relevance-run-v1.mjs`, create `.../generic-proof-relevance-run-v1.test.mjs`.

**Interfaces:** `runGenericProofRelevance({source,expectedSha,projectDir,timeoutMs})` returns a structured native execution receipt with `verdict`, `proof_binding`, status, environment and full logs.

- [ ] Write failing CLI/native contract tests for unavailable environment, mismatch SHA, raw PASS/FAIL parsing and provenance.
- [ ] Run targeted tests and observe expected failure.
- [ ] Implement runner using the existing pinned environment inspector, strict proof-checker invocation and fail-closed JSON validation.
- [ ] Run tests and verify pass, including optional real native positive/negative fixtures.

### Task 2: Integrate optional CLI without authority promotion

**Files:** Modify `generic-semanteq-cli-v1.mjs`, `generic-semanteq-cli-v1.test.mjs`, `GENERIC_CLAIM_AUDIT_V1.md`.

**Interfaces:** `--proof-fixture`, `--proof-fixture-sha` pair produces `proof_fixture_audit` and always leaves `evidence_warrant/intent_fidelity = UNKNOWN`.

- [ ] Write failing CLI test requiring exact fixture pinning and a distinct advisory result.
- [ ] Verify red for missing flag contract.
- [ ] Implement minimal CLI integration and same-run environment correlation diagnostics.
- [ ] Verify focused tests; run all local relevant Node tests, including optional native tests with pinned project.
- [ ] Commit scoped code and tests; update existing draft PR only if current base/ref checks and remote permissions permit.
