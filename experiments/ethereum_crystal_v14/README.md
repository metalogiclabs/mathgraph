# Ethereum Crystal V14 — geth full-node build / snap end-to-end seal

V13 changed the real geth snap/2 catch-up path: canonical BAL bytes are fully
authenticated at the peer-response boundary, then the second application decode
uses the frozen Crystal final-state consequence rather than rematerializing
storage reads and intermediate history.

V14 does not change that interface. It raises the integration boundary:

1. patch the same pinned go-ethereum source as V13;
2. run the complete `core/types/bal` package tests;
3. run the complete `eth/protocols/snap` package tests;
4. repeat the catch-up/pivot tests that exercise the modified path;
5. build the actual `cmd/geth` binary and execute its version command;
6. retain the exact local patch and binary digest.

A green V14 warrants full geth source/build integration and end-to-end snap
catch-up test-path compatibility at the pinned commit. It is not a live-mainnet
node benchmark and creates no upstream branch or PR.
