# MathGraph × LeanEval

This directory is the MathGraph solver-side integration for `leanprover/lean-eval`.

## Goal

Measure verified capability growth against an external comparator-based Lean benchmark. A problem is counted only when LeanEval's comparator accepts the submitted workspace.

## Frozen baseline

Initial upstream pin:

- lean-eval commit: `de48559590eb8cff2125e8e933b3e13bb8a3ff98`
- upstream toolchain at inspection time: Lean `v4.32.2`

The first gate is intentionally cheap: build the pinned benchmark CLI, inspect the current catalog, create the official `two_plus_two` starter workspace, and build it. This separates integration/toolchain failures from proof-search failures before spending Actions time on the full comparator stack.

## Development loop

1. **PUSH** the strongest existing MathGraph/Lean route against a selected benchmark problem.
2. **READ** the exact Lean/comparator residual.
3. **DIAGNOSE** search vs capability vs representation/observability vs constructor/language vs soundness/infrastructure failure.
4. **MAP** the smallest deciding experiment.
5. **CONSTRUCT** only the missing capability justified by that residual.
6. **VERIFY** with LeanEval comparator; accepted solutions terminate as `VERIFIED_PROOF`.
7. **REPLAY / ABLATE / TRANSFER** before claiming a reusable capability gain.

A build, candidate proof, tactic success outside the comparator, bounded search miss, or local heuristic score is not a solved benchmark problem.

## First experiment sequence

- Gate 0: pinned CLI + catalog + starter workspace build.
- Gate 1: install the exact pinned `landrun`, `lean4export`, and `comparator` stack and run LeanEval's `check-comparator-installation`.
- Gate 2: freeze a small non-starter problem tranche and record cold baseline outcomes.
- Gate 3+: apply the residual loop only to unresolved problems; every new constructor/capability must be tested for replay and transfer.

The public leaderboard submission repo accepts a repository containing one or more benchmark workspaces; only `Submission.lean` and Lean files under `Submission/` are consumed by the hosted evaluator.

<!-- CI trigger: quartic universal verification 2026-08-27 -->
