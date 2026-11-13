# L4YAML differential V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducibly qualify 532 native L4YAML value observations and separate known anchor failures from ordinary unaffected YAML behavior.

**Architecture:** Fixed Python grammar and independently verified ruamel.yaml oracle generate JSONL inputs. One dynamic Lean runner executes legacy and indexed JSON paths at one frozen SHA. A strict Python verifier validates complete source-native logs and classifies all observations without granting proof or release authority.

**Tech Stack:** Lean 4.35.0, standard Python 3.12, pinned ruamel.yaml 0.18.17 and PyYAML 6.0.3 wheels, GitHub Actions, MathGraph's existing source-bound evidence convention.

**Spec:** `docs/superpowers/specs/2026-10-24-l4yaml-differential-v2-design.md`

## Global constraints

- No modification to nasa-jpl/L4YAML. No use of historical native outputs as evidence of a new commit.
- Bound claims to the 532 generated acyclic inputs; do not count correlated mismatches as distinct underlying defects.
- Reject changing oracle, source, native log, missing cases, stale revision, or mismatched toolchain; no authorization to merge/deploy.

## Review focus

- An omitted or duplicated native row must fail qualification, even if the remaining examples all agree.
- A renamed anchor should preserve outcomes only when that name is syntactic metadata, not a visible scalar.
- A repaired anchor case must become an observed match rather than an unexpected checker failure.
- A novel mismatch in the ordinary suite must surface as an additional family, never be silently skipped.
- A byte-identical source file at a different commit must not transfer the old receipt.

---

### Task 1: Strict generated differential verifier

**Files:** `research/l4yaml_semantic_diff_v2/differential.py`; `tests/test_mathgraph_l4yaml_semantic_diff_v2.py`.

**Interfaces:** `generate_cases() -> tuple[list[dict], list[dict]]` and `classify(native_rows, oracle_rows) -> dict`.

- [ ] Write unit tests for 180/352 exact unique case grammars and deterministic hashes.
- [ ] Run tests and observe missing-implementation failure.
- [ ] Implement deterministic generator and strict classifier; preserve all mismatch families.
- [ ] Run tests green, including removed/duplicated case, unknown status and stale source controls.

### Task 2: Dynamic Lean source-native replay and CI

**Files:** `research/l4yaml_semantic_diff_v2/BatchProbe.lean`; `.github/workflows/mathgraph-check-l4yaml-semantic-continuity.yml`; README update.

**Interfaces:** newline-delimited JSON strings input; newline-delimited JSON objects with `input`, `legacy`, `indexed` results.

- [ ] Use the validated dynamic Lean probe, pinned source checkout and official toolchain; never modify the upstream working files.
- [ ] Regenerate the independent oracle from the exact official ruamel wheel within Actions, and independently corroborate the 352 ordinary cases with the byte-checked PyYAML wheel.
- [ ] Run both suites; validate all source identities and write a separate bounded `differential-v2.json` artifact.
- [ ] Verify local tests and the new GitHub Actions run, inspect its artifacts, then update ROS.
