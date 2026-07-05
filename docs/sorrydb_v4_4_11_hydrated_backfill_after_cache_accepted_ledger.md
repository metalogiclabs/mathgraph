# SorryDB v4.4.11 Hydrated Backfill After Cache Accepted Ledger

v4.4.11 reran the hydrated v4.4.7 four-row backfill queue after the v4.4.10 cache hydration reality step.

Result:

    QUEUE_RUN_COMPLETED
    candidate_count=4
    completed_count=4
    accepted_count=4
    failed_count=0
    manifest_count=4
    certificate_count=4

Each candidate reached:

    BASELINE_PASSED
    PATCH_APPLIED
    PATCH_ACCEPTED

## Bounded claim

The hydrated four-row backfill queue was rerun after cache hydration, and all four candidates reached controlled Lean replay and were accepted. Four replay manifests and four patch certificates were regenerated.

## Does not claim

- new proof discovery
- general SorryDB mining
- arbitrary proof repair
- upstream submission
- the duplicated certificate identities are semantically distinct proofs

## Next frontier

v4.4.12 should deduplicate accepted replay certificates by source snippet, patch snippet, file, repo commit, and line span.
