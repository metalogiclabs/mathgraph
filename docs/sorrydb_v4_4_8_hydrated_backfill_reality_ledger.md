# SorryDB v4.4.8 Hydrated Backfill Reality Ledger

v4.4.8 records real streaming replay contact for the four-candidate hydrated backfill queue produced by v4.4.7.

## Result

    HYDRATED_BACKFILL_REALITY_LEDGERED

Observed:

    queue_verdict: QUEUE_RUN_COMPLETED_WITH_FAILURES
    candidate_count: 4
    completed_count: 4
    accepted_count: 0
    failed_count: 4
    manifest_count: 4
    certificate_count: 0

All four candidates reached the controlled replay runner, but baseline Lean contact stopped before patch application with:

    OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY

The concrete boundary was missing Mathlib.olean / unknown module prefix Mathlib in the hydrated source cache search path.

## Bounded claim

The v4.4.7 hydrated backfill queue is executable through the streaming queue runner, and all four rows reached controlled replay. The replay result is a named cache/build obstruction, not accepted proof repair.

## Does not claim

- Lean replay success
- proof checking success
- new proof discovery
- general SorryDB mining
- arbitrary proof repair
- upstream submission

## Next frontier

v4.4.9 should create a controlled cache/dependency hydration plan for the pinned hydrated source checkout, without weakening exact-source admission.
