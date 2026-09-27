# Ethereum Crystal V11 — go-ethereum package integration benchmark

V11 moves the frozen V8/V9 dependency interface into the actual go-ethereum BAL package.

The workflow pins go-ethereum at `920c07774c65ebb3023536f85df642c44478b540`, copies a benchmark-only test file into `core/types/bal`, and compares:

1. production geth `rlp.DecodeBytes(..., *BlockAccessList)`;
2. the frozen Crystal dependency view (addresses + storage reads + changed storage slots).

Before benchmarking, every one of the 1,112 held-out canonical BAL records is decoded both ways and the dependency view is checked field-for-field against geth's production object.

No upstream geth branch or PR is created. This is a local pinned integration experiment. A positive benchmark warrants a prototype optimization opportunity, not a claim that geth should merge the code as-is.


## Promotion status

**WARRANTED / REUSABLE** at the pinned go-ethereum package-integration boundary.

Authority: run 36355203318, job 108721455645, artifact 10943641142.

The frozen Crystal dependency view matches go-ethereum's production BAL decoder field-for-field on all 1,112 held-out records. In the pinned `core/types/bal` package benchmark it is **2.603x faster**, uses **52.9%** of allocation bytes, and **66.4%** of allocation calls relative to full BAL decode.

Full-node end-to-end benefit and upstream merge readiness remain UNKNOWN.
