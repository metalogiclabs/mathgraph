# SorryDB v4.4.1 Mined Queue Reality Ledger

v4.4.1 records real Lean-contact replay of the queue produced by the v4.4.0 exact-source candidate miner.

This closes the local loop:

    accepted replay artifacts
    → exact-source miner
    → mined queue
    → streaming queue runner
    → real Lean replay
    → accepted manifests
    → emitted certificates
    → source restoration

## Result

    MINED_QUEUE_REALITY_PASSED

Observed:

    queue verdict: QUEUE_RUN_COMPLETED
    candidate_count: 2
    accepted_count: 2
    failed_count: 0
    partial_summary_count: 1
    manifest_count: 2
    certificate_count: 2
    line 97 restored to sorry
    line 99 restored to sorry

## Bounded claim

The v4.4.0 mined exact-source queue is directly executable by the streaming queue runner and both mined candidates are accepted by real Lean replay.

## Does not claim

- new proof discovery
- general SorryDB mining
- arbitrary proof repair
- multi-file patching
- upstream submission

## Importance

v4.4.0 created candidate supply from exact evidence. v4.4.1 verifies that this mined supply can feed the queue runner and survive real Lean contact.

## Next frontier

Scale the mined queue beyond the two known replay rows, or add a broader miner over exact-source SorryDB rows.
