# SorryDB v4.4.3 Missing-Manifest Backfill Planner

## Purpose

v4.4.3 converts the `MISSING_MANIFEST` rows identified by the v4.4.2 coverage profiler into a bounded replay plan. It joins each obstruction to its checked-in certificate, recovers a stable repository root only from exact checked-in evidence when possible, and checks whether a unique one-sorry source replacement can be formed safely.

The planner performs JSON, file, and source-text analysis only. It does not run Lean, Lake, Git replay, network access, or dependency hydration.

## Outputs

- `artifacts/sorrydb/backfill_plans_v4_4_3/summary.json`
- `artifacts/sorrydb/backfill_plans_v4_4_3/backfill_plan.json`
- `artifacts/sorrydb/backfill_plans_v4_4_3/backfill_queue.json`, only when replay-ready candidates exist

Ready rows are replay candidates, not accepted claims. A queue entry still requires controlled streaming Lean replay before it can produce a new accepted manifest or certificate. Blocked rows remain `NAMED_OBSTRUCTION` records with explicit backfill categories.

## Current checked-in result

The four certificate-only rows have complete file, source-snippet, and patch-snippet evidence. Their historical repository root is recoverable from later checked-in accepted evidence, but the referenced source checkout is not a checked-in input. They therefore remain `BACKFILL_BLOCKED_SOURCE_MISSING`; no backfill queue is emitted.

## Boundary

Bounded claim: v4.4.3 classifies missing-manifest evidence rows into replay-ready candidates or named backfill obstructions.

It does not prove any patch and does not claim:

- new proof discovery;
- Lean replay success;
- general SorryDB mining;
- arbitrary proof repair; or
- upstream submission.

## Next frontier

v4.4.4 should run a `BACKFILL_REPLAY_READY` queue through streaming Lean replay if any ready rows exist after exact source checkouts are supplied as controlled inputs.
