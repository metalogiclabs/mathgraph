# Ethereum Crystal V16 — Promotion

**State:** WARRANTED / REUSABLE at the pinned geth in-memory snap catch-up end-to-end boundary.

**Authority:** run 36358745584, job 108731561495, artifact 10944827384, artifact digest `sha256:f5df0d00eb7feb1208c090f94762d6aab6593a445c89895becacc3469cc579fe`.

Pinned geth: `920c07774c65ebb3023536f85df642c44478b540`.

The frozen V13 final-state decoder and the full production BAL decoder are both driven through the real geth `snap.applyAccessList` state mutation path and committed through DB batches over the same 1,112 held-out canonical BAL records.

Before benchmarking, the final database key/value digest is required to match exactly:
`e55478e602cd9f1666a5cda95c3f738cdc7b2252a455d17ac7f8fe3d518e4584`.

Median corpus pass:
- full decode + apply + batch write: **29.846835 ms**
- compact decode + apply + batch write: **25.461591 ms**
- speedup: **1.172230x**
- allocation bytes: **17,899,256 → 16,310,560 B/op** (ratio **0.911242**)
- allocation calls: **243,839 → 191,348/op** (ratio **0.784731**)

Promoted law:

```
verified final-state consequence
→ compact BAL decode
→ identical geth state mutation
→ identical committed DB state
→ lower end-to-end catch-up work
```

This is an in-memory geth snap catch-up benchmark, not a live p2p/mainnet sync throughput claim. Network latency and real disk I/O remain outside the measured boundary.
