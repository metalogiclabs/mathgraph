# SorryDB v4.4.28 — Attempt 002 Snippet Inspection

v4.4.28 inspects exact source snippets from the v4.4.27 top candidates.

## Bounded claim

- v4.4.28 inspects exact source snippets from the v4.4.27 top candidates.
- it selects one candidate for possible future replay based on simple source-shape heuristics.
- it does not clone, replay Lean, modify upstream, or contact maintainers.

## Does not claim

- new proof discovery
- new Lean replay
- candidate repairability
- that selected source will replay locally
- that the selected repo is active
- upstream acceptance
- automated external contact

## Next frontier

v4.4.29 clone only the selected attempt002 candidate repo into a bounded temp directory and run source/Lean-version reconnaissance before replay.
