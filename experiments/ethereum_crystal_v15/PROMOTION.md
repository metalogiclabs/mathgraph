# Ethereum Crystal V15 — Cross-client promotion (Reth)

**State:** WARRANTED / REUSABLE for cross-client semantic replication and optimized decode benefit at Reth's pinned snap-sync production-consumer boundary.

**Active authority:** run 36357032694, job 108726711616, artifact 10943534315, digest `sha256:c095d0f9166c7f1323fceb835b9b9798192861a70313aca8bd3439e184a355a5`.
**Reth pin:** `5723a3fed5521fad105b44f86876580242f31be9`.
**Frozen parent interface:** geth V13 run 36355884299.

The geth-derived final-state consequence was frozen before Reth was evaluated: address, final post-value for each changed storage slot, final balance, final nonce, final code. No Reth-specific field was added.

On the same **1,112 held-out canonical EIP-7928 BAL records**:
- exact equality with Reth production `BalStateUpdate`: **1,112/1,112**;
- full decode median corpus pass: **0.024908064 s**;
- compact final-state decode: **0.017736225 s**;
- speedup: **1.404361075x**;
- the complete pinned Reth snap-sync suite is green: **162/162 tests**.

Architectural separator: unlike geth, Reth's verified downloader already carries one decoded authenticated BAL forward, so geth's duplicate-decode elimination does not transfer as the mechanism. The verified consequence transfers; each client exposes its own cheapest realization.

Earlier run 36356411033 is retained as red infrastructure lineage only: its parity/benchmark passed, but the subsequent all-tests invocation omitted `CRYSTAL_BAL_CORPUS`. Commit `a409f3707a6b6780bca9c234040f771cf32daed8` corrected that wrapper and produced the active green authority above.

Promoted law:

```
same frozen verified consequence
→ geth production consumer
→ Reth production consumer
→ exact protected-effect parity
→ client-specific realization
```

No upstream Reth PR is claimed.
