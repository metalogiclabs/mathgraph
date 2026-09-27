# Ethereum Crystal V14 — Promotion

**State:** WARRANTED / REUSABLE at the pinned geth source/build + snap catch-up integration boundary.

**Authority:** run 36356411019, job 108724906064, artifact 10943562791,
artifact digest `sha256:250f8689237d232dcf5f7687bb1055999092411837effc19e15bb2d3d1864339`.

Pinned go-ethereum: `920c07774c65ebb3023536f85df642c44478b540`.
Parent real-path authority: V13 run 36355884299.

The V13 compact apply decoder is patched into the real geth snap/2 catch-up path.
V14 then qualifies the complete `core/types/bal` package, the complete
`eth/protocols/snap` package, repeats the modified pivot/catch-up tests five
times, builds the actual `cmd/geth` executable, executes its version command,
and seals the resulting binary digest and local patch.

Promoted claim:

```
verified BAL
→ frozen final-state consequence
→ compact second decode in real snap catch-up path
→ full snap-package compatibility
→ buildable geth node binary
```

This is not a live-mainnet throughput benchmark and no upstream geth PR is
claimed.
