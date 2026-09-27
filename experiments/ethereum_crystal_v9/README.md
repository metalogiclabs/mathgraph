# Ethereum Crystal V9 — consequence-specific BAL consumer compiler

V8 proved exact reconstruction of canonical EIP-7928 BALs from Crystal's accumulated capability bank. V9 keeps the consensus object unchanged and asks the first systems question: can different consumers avoid materializing fields outside their protected consequence?

Two frozen views are compiled directly over canonical BAL RLP:

- **Dependency/scheduling view:** address, read-only storage slots, changed storage slots.
- **Reconstruction view:** address, changed storage slots and payloads, balance changes, nonce changes, code changes.

The parser scans canonical RLP structure but skips irrelevant payloads instead of instantiating the full EELS Pydantic BAL object. The two views must recombine to the exact original RLP bytes and reproduce the official fixture hash on every held-out record before any benchmark is reported.

The corpus is generated from the full official Amsterdam EIP-7928 test directory. The nine fixture families used in V8 are frozen as seen; V9 performance and exactness are reported only on the remaining generated families.

Performance is a Python CI microbenchmark and must not be generalized to production clients without native-client replication.
