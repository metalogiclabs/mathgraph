# SorryDB v4.4.22 — Local Bounded Discovery

## Result

- searched files: 9318
- candidate count: 5
- replay attempted: false
- status counts: `{"CONTROL_TARGET_LOCATED": 1, "LOCAL_EXACT_SOURCE_MATCH_FOUND_REPLAY_NOT_ATTEMPTED": 2, "LOCAL_SELECTOR_HITS_FOUND_NAMED_ADAPTER_REQUIRED": 2}`

## Boundary

This run uses existing artifacts and source-cache only. It does not clone repositories, use network access, run Lean, run Lake, or perform external contact.

## Bounded claim

- v4.4.22 runs local bounded discovery over existing artifacts and source-cache only.
- the run searches the five-candidate v4.4.21 pilot queue without cloning, networking, Lean replay, or heavy builds.
- outcomes are recorded as control located, exact-source match found, selector hit requiring adapter, or named obstruction.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that selector hits are valid replay targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- general SorryDB mining
- semantic portability beyond exact-source replay or verified adapters
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.23 convert any local exact-source matches into a replay-or-obstruction queue; if none, park the fresh-source pilot and return to manual outbound review.
