# SorryDB v4.4.24 — Control Replay Approval Gate

v4.4.24 records the replay approval gate after the v4.4.23 replay-or-obstruction queue.

## Decision

Replay is parked because no explicit approval token was supplied.

## Approval token required

APPROVE_PINNED_CONTROL_REPLAY_V4_4_24

## Bounded claim

- v4.4.24 records the replay approval gate after the v4.4.23 replay-or-obstruction queue.
- because no explicit approval token is present, v4.4.24 parks replay and returns to manual outbound review.
- it packages the pinned control replay command list but does not execute it.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that exact-source-ready local matches are fresh targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.25 either manually send or rewrite the outbound upstream message; only run pinned control replay if the approval token is explicitly supplied.
