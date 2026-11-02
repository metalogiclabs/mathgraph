# Native Candidate Proof Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report a native, exact-source observation that the actual Consumer proof term directly references the actual Candidate theorem after zeta reduction, without claiming essential mathematical dependence.

**Architecture:** A small pure Lean-audit generator and marker parser; an optional extension to the pinned native consumer runner. Execute the generated audit against separately compiled byte-staged Candidate and Consumer modules; the current original-target consumer proof/axiom receipt remains separate.

**Tech Stack:** Node ESM tests, pinned Lean 4.30.0-rc1 `run_cmd`, existing SemantEq environment/consumer runner.

**Spec:** `docs/superpowers/specs/2026-11-03-native-candidate-proof-reference-design.md`.

## Global Constraints

- Operator-reviewed sources only; do not compile arbitrary PR files.
- No output may elevate `candidate_dependence`, research intent, human authority, or `evidence_warrant`.
- Preserve old JSON/behavior when optional name omitted.

## Review Focus

- Dead `have` that mentions candidate: native reduced reference is false.
- Imported theorem masquerading as candidate: module-origin audit rejects.
- Candidate proof with sorry/custom axiom: no positive status.
- Forged/duplicate native output: no positive status.
- Environment unavailable: distinct from Lean rejection.

### Task 1: Native audit and classification

**Files:** Create `integrations/mathgraph-check-github/generic-candidate-proof-reference-v1.mjs` and `.test.mjs`.

**Interfaces:** `buildCandidateProofReferenceAudit({candidateName,consumerName,marker})` creates the native Lean audit; `parseCandidateProofReferenceMarker(stdout,marker)` parses a unique result; `classifyCandidateProofReference({record,compiled,axioms})` returns bounded status.

- [ ] Write negative-first tests of marker uniqueness, invalid names and failed evidence, plus an actual Lean native trio (positive, bypass, dead touch).
- [ ] Run tests and observe missing implementation failure.
- [ ] Implement the minimal generator/parser/classifier.
- [ ] Run native tests under the official digest-verified Lean binary and observe three concrete outcomes.

### Task 2: Integrate into exact-source consumer runner

**Files:** Modify `generic-lean-consumer-run-v1.mjs` and its tests; update `GENERIC_CLAIM_AUDIT_V1.md`.

**Interfaces:** Optional `candidateName` selects the generated audit, retains original target status, and adds `actual_candidate_proof_term_reference`, `normalized_direct_reference`, `candidate_dependence: UNKNOWN`.

- [ ] Add red tests for unavailable native environment, bad name, and non-promoting evidence.
- [ ] Implement same-run generation and classification, print both axiom sets, record generated source hash.
- [ ] Run focused and full available Node suites. Record native/skip split honestly.
- [ ] Commit on isolated draft branch, publish with exact tree/lease, verify fresh CI.
