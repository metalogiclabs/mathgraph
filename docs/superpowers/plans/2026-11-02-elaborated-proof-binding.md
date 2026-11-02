# Elaborated Proof Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind a native proof-use fixture's theorem types to exact trusted and candidate Lean declarations, without promoting actual candidate proof-artifact dependence, source intent or external warrant.

**Architecture:** Independently byte-stage the reference, candidate and fixture; compile native .olean modules and two generated ownership/type comparisons; combine only with a same-run ProofChecker receipt whose names and hashes match. Fail closed.

**Tech Stack:** Node.js ESM and test runner, pinned Lean 4.30.0-rc1/Mathlib/SemantEq.

**Spec:** `docs/superpowers/specs/2026-11-02-elaborated-proof-binding-design.md`

## Global Constraints

- Operator-only, no untrusted GitHub PR Lean execution.
- Full source SHA-256, module ownership, theorem kind and Lean `Meta.isDefEq` are independent requirements.
- False defEq, failed compilation, stale hash, wrong proof selected or missing pinned tool returns UNKNOWN, never evidence warrant.
- Native ProofChecker PASS never becomes `NATIVE_TYPE_BOUND_FIXTURE_USE` without a real same-invocation binding receipt; actual candidate dependence always stays UNKNOWN.
- Existing status fields and production publication remain unchanged.

## Review Focus

- An imported library declaration must not impersonate the actual reference theorem.
- Candidate/reference declarations with identical names in different modules must still bind through separate passes.
- A strengthened assumption with a valid Lean proof must fail candidate type binding.
- A clean independently provable goal must not become candidate-dependent with a valid type-binding alone.
- Malformed or forged audit output, wrong record names and stale source bytes must fail closed.

---

### Task 1: Native ownership and full-type binder

**Files:** Create `integrations/mathgraph-check-github/generic-proof-type-binding-run-v1.mjs` and `.test.mjs`.

**Interface:** `runGenericProofTypeBinding({reference,candidate,expectedReferenceSha,fixturePath,expectedFixtureSha,names,projectDir,timeoutMs})` returns exact source hashes, native trace, two type relations, `binding_status`, environment and raw logs.

- [ ] Write failing missing-env, stale-hash, malformed name tests and native positive/strengthened/wrong-module/goal controls.
- [ ] Observe RED before implementation.
- [ ] Implement native staged compiler, exact module-ownership and theorem-kind audit and full `isDefEq` type comparisons.
- [ ] Run targeted unit and real native controls, check observed outputs against expectations.

### Task 2: Same-run CLI correlation and candidate-dependence status

**Files:** Modify `generic-semanteq-cli-v1.mjs`, its tests and `GENERIC_CLAIM_AUDIT_V1.md`.

**Interface:** Four optional `--proof-*-name` flags, all required together and with fixture, add `proof_type_binding`, `proof_binding_correlation`, and `bound_fixture_proof_use`; actual `candidate_dependence`, `intent_fidelity` and `evidence_warrant` stay UNKNOWN.

- [ ] Write failing CLI tests for incomplete binding flags and an unbound PASS that cannot promote.
- [ ] Observe RED, integrate binder and correlation with exact native proof names and SHA match.
- [ ] Run actual native positive, strengthened and bypass controls end to end.
- [ ] Run focused and full Node suites under pinned toolchain, then review and commit scoped work.
- [ ] Update existing draft PR only if exact head/tree lease and public/private boundaries hold; record CI separately.
