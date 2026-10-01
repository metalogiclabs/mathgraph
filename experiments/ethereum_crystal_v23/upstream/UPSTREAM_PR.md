# Upstream geth PR package

Target: `ethereum/go-ethereum@c9a2bc73c847319a8faa57de59e42c0efc420682` (master at qualification time)

Suggested title:

`core/types/bal, eth/protocols/snap: avoid redundant BAL materialization in catch-up`

## Summary

snap/2's `fetchAccessLists` already fully decodes each received BAL and calls `verifyAccessList` against the block header before returning the raw RLP to `catchUp`.

`catchUp` then fully decodes the same BAL again, although `applyAccessList` only consumes:
- account addresses,
- storage slots and their final post-values,
- final balance,
- final nonce,
- final code.

This change adds `bal.DecodeApplyRLP`, which parses the canonical BAL RLP but materializes only those apply-time consequences. Storage reads and intermediate changes are consumed structurally but not retained. Consensus validation and BAL hash verification remain unchanged and occur before this decoder is used.

## Correctness

The current-upstream qualification was frozen before measurement and run against geth `c9a2bc73c847319a8faa57de59e42c0efc420682` using an independently generated 1,112-record EELS Amsterdam/EIP-7928 corpus.

Across 21 alternating stock/optimized pairs (42 arms):
- exact final DB digest parity,
- exact pivot parity,
- exact final state-root parity,
- exact 1,112-block root-chain parity,
- 43 authenticated BAL requests in every arm.

State root:
`0xed5b65d3db70b9f481a9a80511d65dd04935fa36dbe8c2fa5fa795b24811f72f`

## Performance

Prospective rule was fixed before the run:
promotion iff paired median apply CPU ratio > 1, at least 14/21 pairs favor the change, and deterministic paired bootstrap 95% lower bound > 1.

Result:
- classification: `WARRANTED_PERFORMANCE`
- apply CPU median ratio: **1.021064847x**
- positive pairs: **16/21**
- paired bootstrap 95%: **[1.003378647, 1.036350589]**
- durable CPU median ratio: **1.021159076x**
- apply wall median ratio: **1.012817137x**

Qualification run:
https://github.com/metalogiclabs/mathgraph/actions/runs/36841681171

The benchmark boundary is authenticated `syncerV2.catchUp` in `phaseComplete`, with trie maintenance, per-block header-root verification, Pebble batch writes and pivot persistence. It is not a socket/mainnet benchmark.

## Files

- `bal_apply.go` -> `core/types/bal/bal_apply.go`
- `bal_apply_test.go` -> `core/types/bal/bal_apply_test.go`
- apply `syncv2.patch`

No consensus/authentication rule is weakened; the optimization is downstream of the existing successful BAL verification.
