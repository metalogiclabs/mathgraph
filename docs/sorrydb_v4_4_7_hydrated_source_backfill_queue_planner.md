# SorryDB v4.4.7 Hydrated-Source Backfill Queue Planner

## Purpose

v4.4.7 converts v4.4.6 `SOURCE_HYDRATED_VERIFIED` rows into v4.3.5/v4.3.7-compatible backfill queue candidates. It joins hydration, registration, snippet, hash, and line-span evidence by row identity and admits a candidate only when every exact-source gate remains satisfied in the controlled local cache.

The planner checks one source-snippet occurrence, matching source and patch hashes, exactly one source `sorry`, no `sorry` in the patch, a known line span, a known certificate identity, and a source file under the recorded controlled cache root.

## Current result

All four hydrated rows become `HYDRATED_BACKFILL_READY`. They represent four missing-manifest identities over two exact source replacements. The emitted queue preserves each certificate identity separately so later replay can regenerate the missing manifest/certificate trail.

Conservative defaults are:

- replay timeout: 240 seconds;
- queue timeout: 600 seconds;
- required free space: 5 GiB; and
- baseline replay enabled.

## Boundary

v4.4.7 performs JSON, file, and text planning only. It does not run Lean or replay patches. Ready rows are queue candidates, not accepted claims.

Bounded claim: verified hydrated source rows can be converted into replay-ready queue candidates.

It does not claim:

- Lean replay success;
- proof checking;
- new proof discovery;
- general SorryDB mining;
- arbitrary proof repair; or
- upstream submission.

## Next frontier

v4.4.8 should run this hydrated backfill queue through the streaming Lean replay runner and ledger accepted and failed outcomes without weakening exact-source admission.
