# L4YAML Repository Contract Implementation Plan

> Implement inline with native replay and one independent review.

Goal: Check a fresh multi-file fork PR with one frozen repository contract and no per-PR adapter or expected-result changes.
Architecture: Reuse the frozen 1367-case regression generator and references. Derive changed Scripts modules and transitive Scripts imports from pinned snapshots, build them in an isolated trusted Lake project, then replay the identical corpus on base/head. Report other paths as uncovered.
Tech stack: Python standard library, Lean4.35, offline Docker, existing GitHub integration.
Spec: repository-contract-v1/contract.json.

Constraints: owned fork only; no upstream messages or production deployment; no new API keys or model spend; no head-controlled host commands. Existing proof-reference work does not establish semantic necessity.

Approaches: Per-PR handwritten adapters reproduce the current gap. Arbitrary model-generated obligations do not solve authority. The chosen implementation is one fixed regression contract plus automatic source/import discovery. It broadens executable scope while stating missing semantics.

Tasks:
- [ ] Freeze contract and newest PR metadata before diff inspection.
- [ ] Write failing admission/discovery tests (unsupported imports, source paths, incomplete evidence, passing and failing both-arm attribution), then implement generic discovery and isolated replay.
- [ ] Mirror fresh PR213 in our fork; add a labelled multi-file regression and withdrawal. Request IDs are run inputs; contract and expectations must not change.
- [ ] Native replay all snapshots with the same contract/corpus hashes. Keep passing, failing and UNKNOWN outcomes, plus uncovered paths.
- [ ] Independent review, appropriate regression suite, pinned artifacts, result report and Research OS reconciliation.
