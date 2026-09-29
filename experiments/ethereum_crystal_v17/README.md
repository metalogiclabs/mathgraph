# Ethereum Crystal V17 — Nethermind third-client replication

V17 freezes the same final-state consequence already qualified in geth V13–V16
and Reth V15:

- account address;
- final post-value for every changed storage slot;
- final balance;
- final nonce;
- final code.

No Nethermind-specific field is added.

The independent compact C# RLP parser is checked against Nethermind's production
`Rlp.Decode<ReadOnlyBlockAccessList>` objects over the same 1,112 held-out EELS
BAL records. The comparison is exactly the field family consumed by
`BlockAccessListManager.ApplyStateChanges`, whose production implementation
applies the last balance/nonce/code change and each changed slot's last value
while ignoring storage reads.

Only after 1,112/1,112 parity is established are production full-decode and
compact final-state decode timed in the same Release test process.

This is third-client semantic/performance replication in .NET, not an upstream
Nethermind patch and not a whole-node throughput claim.


## Promotion result

**WARRANTED / REUSABLE for semantic cross-client replication.**

Authority: run 36502416400, job 109196097263, artifact 11005958772.

The frozen final-state consequence matches Nethermind's production BAL projection on 1,112/1,112 held-out records, and Nethermind's BAL decoder regression suite is 46/46 green.

The generic compact C# parser is **not** promoted as a Nethermind optimization: full production decode is 0.116897200 s median versus 0.438569300 s for the compact parser, making the compact implementation about 3.752x slower. Crystal therefore retains the semantic capability and rejects this implementation strategy for Nethermind.
