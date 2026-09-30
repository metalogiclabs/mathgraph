# Ethereum Crystal V18 — geth disk-backed A/B gate

V18 crosses the storage boundary left open by V16 without changing the frozen semantic consequence.

## Frozen inputs

- geth: `920c07774c65ebb3023536f85df642c44478b540`
- EELS: `84e7d2c266e3319fc3882e72f379282bb1c40f2d`
- corpus: the same 1,112 held-out canonical Amsterdam EIP-7928 BAL records used by V9–V17
- decoder consequence: V13/V16 final-state apply view, unchanged

## Experiment

The first 556 corpus records create one Pebble-backed seed database through the full production BAL decoder. The seed is closed, synchronized, and then cloned byte-for-byte before every A/B arm.

Each arm applies the remaining 556 records through the real geth `snap.applyAccessList` + batch-write path:

- control: full production `BlockAccessList` RLP decode
- Crystal: frozen compact final-state decoder

Two regimes are measured over seven paired trials with alternating arm order:

1. `fresh_open` — open the identical cloned seed and immediately apply the measured suffix.
2. `prewarmed` — scan the identical clone before measurement to warm Pebble/cache state.

For each trial V18 records:

- async apply wall time (matching geth Pebble's default asynchronous writes)
- durability-inclusive wall time after one final `SyncKeyValue`
- final database digest
- Pebble database statistics

The gate does **not** require Crystal to be faster. Performance may promote, narrow, or reject the node-storage hypothesis. The hard correctness requirement is exact final database parity in every paired trial and every regime.

## Claim boundary

This is a pinned geth Pebble-backed corpus continuation from a corpus-derived seed DB. It includes actual disk-backed storage-engine writes and a durability boundary. It does not include peer/network latency and it is not a replay of canonical mainnet chaindata. A green result therefore advances V16 across the storage-engine boundary but does not by itself establish live-mainnet whole-node speedup.
