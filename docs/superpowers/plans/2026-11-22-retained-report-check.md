# Retained Report Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Run one retained report-integrity investigation on exact local Git revisions with fresh finite evidence and a concise comparison.

**Architecture:** Extract only pure probe construction from the existing report adapter. A local Node coordinator acquires Git sources, runs the existing independent reference and a small local native Lean driver, then reuses probe assessment and comparison. Hosted admission is unchanged.

**Tech Stack:** Node 24, Python standard library, Lean 4.35.0, local Git.

**Spec:** `docs/superpowers/specs/2026-11-22-retained-report-check-design.md`

## Global Constraints

- The source path is `Tests/SuiteRunner/Reports.lean`.
- Preserve the existing 19-case corpus, three groups, source whitelist and reference.
- Output statuses: `OBSERVED_AGREEMENT`, `OBSERVED_MISMATCH`, `UNKNOWN`.
- Exit codes: 0 complete head agreement, 1 complete head discrepancy, 2 incomplete.
- Both revisions execute afresh; source/corpus changes invalidate observations.
- No deployment, App permission changes, external messages or fabricated human trial.

## Review Focus

- Wrong/missing Git revision or module: diagnostic UNKNOWN and no borrowed identity.
- Failed compilation/control or incomplete/duplicate case output: UNKNOWN, never green.
- A failing valid-input control: describe the actual discrepancy rather than always saying malformed input was accepted.
- Later source outside historical digests: local finite check can run; hosted admission still refuses it.
- Changed source/corpus/driver or reused output directory: preserve old evidence and refuse ambiguous current evidence.

### Task 1: Retain the existing experiment without weakening admission

**Files:** `pr-pilot-v1/report-integrity.mjs`, `pr-pilot-v1/report-integrity.test.mjs` under `integrations/mathgraph-check-github/`.

**Interfaces:** Export `reportProbePlan()` for the same three fixed obligations. Existing `reportPlan(subject)` remains exact-source gated.

- [x] Add a failing test for source-independent construction plus refusal of new bytes by hosted admission.
- [x] Extract `reportProbePlan()`; do not alter the corpus or expectation semantics.
- [x] Run report, reuse and monitor tests; commit.

### Task 2: Execute the retained check on real local Git sources

**Files:** add `pr-pilot-v1/local-report-check.mjs`, `local-report-native.py`, `local-report-check.test.mjs`.

**Interfaces:** CLI described by the spec; Node passes exact acquired sources and frozen probes to Python; Python emits native arms with the existing `inspectArm` shape, plus individual cases and real logs. Export small pure assessment/report functions for meaningful failure-input tests.

- [x] Write failing CLI tests for exact Git acquisition, missing source/Lean, and native base/head outcomes using real temporary Git repositories.
- [x] Implement bounded local subprocess execution reusing `guard_outcome`, `renderProbe`, `inspectArm` and `compareProbeRows`.
- [x] Verify frozen reference hashes/results and pre/post source/method identity.
- [x] Emit concise report and measured run evidence; distinguish local observations from hosted admission.
- [x] Run tests, actual historical forward/reverse/no-change native checks and unsupported input controls; commit.

### Task 3: Qualify source reuse and prepare operator handoff

**Files:** add `pr-pilot-v1/LOCAL_REPORT_CHECK.md`, isolated Actions workflow and a small qualification driver.

- [ ] Freeze the implemented method commit before opening selected later source content.
- [ ] Execute the same method against the selected upstream integration and retain the default-main missing-module result.
- [ ] Document real commands, outcomes, scope and human trial NOT_RUN; retain bulky logs in Actions artifacts.
- [x] Run the Check regression suite and relevant Python tests; independent whole-change review and required fixes.
- [ ] Persist a draft PR and exact qualification run; append concise result to the existing ROS checkpoint.

## Verification before later-source execution

- Native local-entry suite: 9 passed, including actual forward, reverse, unchanged, later-compatible fixture, missing runtime and compile-error controls.
- Check regression suite: 633 passed, 14 skipped, 0 failed; three skips are the native tests run separately above.
- Relevant Python unit suites: 51 passed (47 existing and 4 qualification provenance controls).
- Independent review required masking incomplete group outcomes, truthful early-UNKNOWN evidence wording, launcher invocation preservation, and committed method provenance; corrected and covered by tests.
- Bare whole-project `python3 -m pytest -q` could not start because this runtime has no pytest installation. No whole-project Python qualification is claimed.
- Later-source file contents remain unopened at this checkpoint.
