# Ethereum Crystal V13 — local geth snap/2 catch-up prototype

V13 turns the benchmark-only consequence view into the smallest local geth
prototype that changes a real client path.

The peer-response boundary remains unchanged: geth fully decodes and verifies
the BAL against the trusted header. During subsequent catch-up application,
however, geth currently decodes the same raw BAL a second time. V13 adds
`bal.DecodeApplyRLP`, which materializes only the consequences observed by
`snap.applyAccessList`, and locally patches the second decode to use it.

The compact decoder retains:

- address;
- changed storage slot + final post-value;
- final balance;
- final nonce;
- final code.

It discards storage reads, intermediate changes, and non-final indexed history
at the application boundary.

Qualification requires:
1. field-for-field equivalence against production geth BAL objects on all
   frozen held-out EELS BALs;
2. the native `core/types/bal` test suite;
3. geth snap pivot-movement/catch-up regression tests through the patched path;
4. a persisted patch artifact and benchmark log.

This is a local pinned prototype only. No upstream go-ethereum branch or PR is
created.
