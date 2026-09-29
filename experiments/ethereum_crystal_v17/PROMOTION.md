# Ethereum Crystal V17 — Nethermind third-client promotion

**State:** WARRANTED / REUSABLE for third-client semantic replication on the pinned Nethermind BAL boundary.

**Authority:** MathGraph run 36502416400, job 109196097263, artifact 11005958772, artifact digest `sha256:36509bbba8af6f3c6e868c9692b7332a69a58723630aed2d378293c9fada80ea`.

**Pinned Nethermind:** `62e29468020c5770a78594e84a07a8a328759e93`.

The frozen final-state consequence from geth V13–V16 and Reth V15 was reused without adding a Nethermind-specific field:
address, final post-value for each changed storage slot, final balance, final nonce, final code.

On the same **1,112 held-out canonical EIP-7928 BAL records**, the compact projection matches Nethermind's production `ReadOnlyBlockAccessList` final-state projection on **1,112/1,112** records. Nethermind's own BAL decoder regression suite also passes **46/46**.

The performance result is deliberately negative:
- production full Nethermind decode median: **0.116897200 s**
- generic compact Crystal C# decode median: **0.438569300 s**
- `full / compact = 0.266542141`, so the compact implementation is about **3.752x slower**.

This is a useful client-specific separator, not a failed semantic transfer. The verified consequence transfers; the geth/Reth implementation strategy does not. Nethermind's existing decoder is already better than the generic compact parser used in V17.

Promoted law:

```
verified consequence transfers across clients
≠ one optimization recipe transfers across clients
```

The correct Crystal action for Nethermind is therefore to retain the semantic capability and reject this particular compact-decoder implementation on performance grounds.

No upstream Nethermind branch or PR was created.
