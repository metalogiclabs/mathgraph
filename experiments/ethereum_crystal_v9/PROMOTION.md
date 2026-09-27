# Ethereum Crystal V9 — Promotion

**State:** WARRANTED / REUSABLE on the declared EELS/Python boundary.

**Authority:** run 36354473773, job 108719320678, artifact 10943795345, branch head `e9b0432e5abb592255f7881b669944cb56ecdfc8`.

Crystal's V8 capability bank was frozen before evaluation on the broader official Amsterdam EIP-7928 corpus. The run generated 1,134 realized BAL records from EELS and evaluated 1,112 held-out records across 163 families.

All held-out records reassembled to the exact original BAL bytes and matched their official `blockAccessListHash`. The dependency view materialized 49.303% of raw BAL payload and parsed 2.838x faster than the full EELS Pydantic BAL decoder in the declared Python CI benchmark, with peak traced allocation ratio 0.02850. The reconstruction view materialized 70.386% of payload, parsed 1.517x faster, with peak traced allocation ratio about 0.141.

This promotion does **not** change the consensus encoding and does **not** claim production-client performance. Geth/Reth/Nethermind/Besu/Erigon replication remains UNKNOWN.

The durable reusable claim is:

```
verified consequential interface
→ compiled consumer-specific view
→ less materialized work
→ exact canonical object recoverable
→ exact protocol commitment preserved
```

Rejected/superseded lineage is preserved in the branch and ROS: monolithic BAL compression, atomic slot separator, unique post encoding, and the plain-pytest EELS runner path.
