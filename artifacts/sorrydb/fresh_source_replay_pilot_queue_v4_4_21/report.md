# SorryDB v4.4.21 — Fresh-Source Replay Pilot Candidate Queue

## Queue

- candidate count: 5
- max candidate targets: 5
- pinned control candidates: 1
- fresh discovery candidates: 4

## Boundary

This is a queue only. It does not run Lean, clone repositories, contact upstream, or claim that a fresh target exists.

## Bounded claim

- v4.4.21 creates a bounded fresh-source replay pilot candidate queue from the v4.4.20 plan.
- the queue contains at most five candidates, including one pinned control and four fresh-target discovery queries.
- each fresh candidate requires exact source match or a named adapter before replay.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that any fresh target currently exists
- automated external contact
- upstream acceptance
- general SorryDB mining
- semantic portability beyond exact-source replay or verified adapters
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.22 run only local bounded discovery over existing artifacts/source-cache for the five-candidate pilot queue.
