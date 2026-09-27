# Ethereum Crystal V12 — geth snap/2 apply-view compiler

V12 specializes the frozen Crystal capability bank to the **actual** go-ethereum
snap/2 BAL catch-up consumer.

At geth commit `920c07774c65ebb3023536f85df642c44478b540`,
`eth/protocols/snap.applyAccessList` consumes only:

- account address;
- each changed storage slot and its final post-value;
- the final balance change;
- the final nonce change;
- the final code change.

It does not consume `storageReads`, any `blockAccessIndex`, or intermediate
changes. Crystal therefore compiles a smaller apply view directly from canonical
BAL RLP using geth's own zero-copy `rlp.Split*` primitives.

Before benchmarking, every one of the frozen 1,112 held-out EELS BALs is decoded
both by geth's production `BlockAccessList` decoder and the compact apply-view
decoder, and all consequences that `applyAccessList` can observe are compared
field-for-field.

This is still benchmark-only code copied into a pinned geth checkout. It does
not modify an upstream client. A positive result opens the next gate: locally
replace the snap/2 catch-up full decode with an idiomatic compact decoder/apply
path and run the native snap package tests.
