# Upstream PR draft

## Title

`core/types/bal, eth/protocols/snap: avoid redundant BAL materialization during catch-up`

## Body

Snap/2 verifies BAL responses before `catchUp` applies them. The catch-up path then decodes the same canonical BAL RLP into the full `BlockAccessList`, even though `applyAccessList` only consumes the final state-changing consequence for each account/storage field.

This change adds `bal.DecodeApplyRLP`, which parses the same canonical RLP but retains only:
- account address;
- final write for each storage slot;
- final balance;
- final nonce;
- final code.

Storage reads and intermediate changes are consumed but not materialized. Consensus validation / BAL hash verification remain unchanged and still happen at the existing peer-response boundary.

The catch-up call site uses the compact apply view only after the BAL has already been verified.

### Qualification

Pinned current geth master: `c9a2bc73c847319a8faa57de59e42c0efc420682`.

External deterministic completed-state qualification over 1,112 canonical EIP-7928 BAL records preserved exact DB digest, pivot, state root and root-chain digest across all 42 stock/changed arms.

21 alternating fresh-process pairs:
- median apply CPU ratio: **1.021064847x**
- positive pairs: **16/21**
- deterministic bootstrap 95% CI: **[1.003378647, 1.036350589]**
- median durable CPU ratio: **1.021159076x**
- median apply wall ratio: **1.012817137x**

Evidence: https://github.com/metalogiclabs/mathgraph/actions/runs/36841681171

The benchmark is intentionally scoped to authenticated completed-state BAL catch-up with trie maintenance; it is not a whole-node or mainnet speedup claim.

### Tests

- `go test ./core/types/bal -count=1`
- compile/test `./eth/protocols/snap`
- external 21-pair current-master qualification above
