# Ethereum Crystal V15 — Reth cross-client consequence replication

V15 freezes the V13 geth snap-application consequence without adding any new
field or domain-specific repair:

- account address;
- final storage post-value for each changed slot;
- final balance;
- final nonce;
- final code.

Reth is intentionally a different architecture. Its snap downloader already
hashes raw BAL bytes before decoding and carries one decoded BAL forward, so the
geth-specific “remove a second decode” mechanism is not assumed to transfer.

The experiment therefore asks the correct cross-client question: can the same
frozen consequence be decoded from the same 1,112 held-out EELS BAL records and
produce exactly the same **Reth production BalStateUpdate** as Reth's full
`Vec<AccountChanges>` decode?

The test is injected only into a pinned local Reth checkout. It uses Reth's
actual `SnapCatchUpStore::block_access_list_update` implementation as the
protected consumer, then measures full alloy BAL decode versus the compact
frozen-consequence decoder in an optimized test binary.

A positive speed result is cross-client performance evidence. Semantic parity
without a speed result is still a valid cross-client replication and an
architectural separator. No upstream Reth branch or PR is created.
