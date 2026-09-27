# Ethereum Crystal V15 — Cross-client promotion (Reth)

**State:** WARRANTED / REUSABLE for cross-client semantic replication and
optimized decode benefit at Reth's pinned snap-sync production-consumer boundary.

**Primary scientific run:** 36356411033, job 108724906135.
**Evidence seal:** green run 36357291612.
**Reth pin:** `5723a3fed5521fad105b44f86876580242f31be9`.
**Frozen parent interface:** geth V13 run 36355884299.

The geth-derived final-state consequence was frozen before Reth was evaluated:
address, final post-value for each changed storage slot, final balance, final
nonce, final code. No Reth-specific field was added.

On the same **1,112 held-out canonical EIP-7928 BAL records**:

- the compact decoder produced exactly the same Reth production
  `BalStateUpdate` as full `Vec<AccountChanges>` decode on **1,112/1,112**;
- full decode median corpus pass: **0.024908064 s**;
- compact final-state decode: **0.017736225 s**;
- speedup: **1.404361075x**;
- Reth independently exposes an architectural separator: unlike geth, its
  verified downloader already carries one decoded BAL forward, so the
  geth-specific duplicate-decode removal does not transfer.

The original run is intentionally retained as red lineage: after the successful
parity/benchmark, the full Reth crate suite ran **161 native tests successfully**
but re-ran the injected corpus-dependent test without `CRYSTAL_BAL_CORPUS`.
That wrapper failure was `CRYSTAL_BAL_CORPUS: NotPresent`, not a semantic
counterexample. Green evidence-seal run 36357291612 verifies these exact markers
from GitHub's own prior-run log. Commit
`a409f3707a6b6780bca9c234040f771cf32daed8` repairs the environment binding
for the single-run rerun.

Promoted cross-client law:

```
same verified consequence
→ geth production consumer
→ Reth production consumer
→ exact protected-effect parity
```

Client-specific mechanisms are **not** forced to be identical. Crystal retains
the consequence and lets each architecture expose its own cheapest realization.
