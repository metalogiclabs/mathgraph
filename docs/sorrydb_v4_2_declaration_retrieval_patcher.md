# SorryDB v4.2 Declaration-Retrieval Patcher

## Purpose

This declaration-retrieval patcher upgrades generic SorryDB tactic replay with nearby theorem and declaration retrieval. It is designed to produce exact-line accepted patches or named obstructions, especially for LeanLangur and LeanLion.

## Run

`python experiments/sorrydb/sorrydb_v4_2_declaration_retrieval_patcher.py`

Environment variables: `SORRYDB_V42_WORK_ROOT`, `SORRYDB_V42_RECORDS_PATH`, `SORRYDB_V42_MAX_RECORDS`, `SORRYDB_V42_FOCUS_REPOS`, and `SORRYDB_V42_TIMEOUT_SECONDS`.

## Lawbook admission

A candidate is admitted only when the baseline compiles, the exact target line is changed, the patch compiles, the target sorry is removed without adding forbidden placeholders, unrelated holes are not counted, the patch is small, and full provenance is recorded.

## Outcomes

The harness distinguishes exact-line acceptance, ambiguous alignment, type mismatch, unsolved goals, identifier/scope failures, import/build boundaries, timeout, missing files, and missing build commands.

## MathGraph and TheoremGraph relation

The loop is: Residual → retrieval candidate → patch attempt → replay → accepted patch or named obstruction. Local declaration scoring is a small TheoremGraph-style retrieval pattern, not a claim of TheoremGraph correctness. No LeanLangur success is claimed without accepted exact-line replay.
