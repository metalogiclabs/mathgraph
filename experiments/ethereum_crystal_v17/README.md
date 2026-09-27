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
