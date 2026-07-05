# SorryDB v4.4.14 — Source Cleanliness and Replay Restoration Ledger

v4.4.14 records source restoration invariants after the v4.4.11 hydrated replay acceptance and v4.4.13 compact Lawbook seed bundle.

## Checks

- pinned source checkout remains at the expected commit
- `MetaExamples/Fiddle.lean` exists
- `git status --short` is recorded
- tracked source changes are clean
- untracked cache/build artifacts are recorded rather than hidden
- `git diff -- MetaExamples/Fiddle.lean` is clean
- `git diff --name-only` is clean

## Bounded claim

- after v4.4.11 replay and v4.4.13 seed packaging, the hydrated source checkout remains at the expected pinned commit
- the target source file has no git diff
- the source checkout has no tracked file modifications
- untracked cache/build artifacts may remain after cache hydration and are recorded rather than hidden

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches
- general SorryDB mining
- arbitrary proof repair
- upstream submission
- that source cleanliness proves semantic portability
