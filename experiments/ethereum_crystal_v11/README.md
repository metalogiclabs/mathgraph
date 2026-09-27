# Ethereum Crystal V11 — go-ethereum package integration benchmark

V11 moves the frozen V8/V9 dependency interface into the actual go-ethereum BAL package.

The workflow pins go-ethereum at `920c07774c65ebb3023536f85df642c44478b540`, copies a benchmark-only test file into `core/types/bal`, and compares:

1. production geth `rlp.DecodeBytes(..., *BlockAccessList)`;
2. the frozen Crystal dependency view (addresses + storage reads + changed storage slots).

Before benchmarking, every one of the 1,112 held-out canonical BAL records is decoded both ways and the dependency view is checked field-for-field against geth's production object.

No upstream geth branch or PR is created. This is a local pinned integration experiment. A positive benchmark warrants a prototype optimization opportunity, not a claim that geth should merge the code as-is.
