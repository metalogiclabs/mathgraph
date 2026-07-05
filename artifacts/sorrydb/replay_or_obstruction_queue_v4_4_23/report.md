# SorryDB v4.4.23 — Replay-or-Obstruction Queue

## Result

- item count: 5
- ready count: 3
- obstruction count: 2
- replay attempted: false
- status counts: `{"OBSTRUCTED_NAMED_ADAPTER_REQUIRED": 2, "READY_FOR_CONTROL_REPLAY_IF_APPROVED": 1, "READY_FOR_EXACT_SOURCE_REPLAY_IF_APPROVED": 2}`

## Boundary

This converts discovery observations into queue states only. It does not run Lean, clone repositories, use network access, or contact upstream.

## Bounded claim

- v4.4.23 converts the v4.4.22 local discovery observations into a replay-or-obstruction queue.
- the queue separates approval-gated replay candidates from internal evidence matches and selector-hit obstructions.
- no Lean replay, clone, network access, or heavy build is executed.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that internal artifact matches are fresh targets
- that selector hits are valid replay targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.24 either run the pinned control replay with explicit approval, or park fresh-source replay and return to manual outbound review.
