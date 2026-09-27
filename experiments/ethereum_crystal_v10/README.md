# Ethereum Crystal V10 — native consumer replication

V9 found a large consequence-specific parsing advantage on 1,112 held-out EELS BAL records, but its baseline is the Python/Pydantic EELS object model. V10 tests whether the result survives an optimized native implementation.

The V8/V9 interface split is frozen. No new feature discovery is allowed.

The workflow regenerates the full Amsterdam EIP-7928 corpus at the same pinned EELS commit, exports only the V9-held-out canonical BAL RLP records, and runs a dependency-free Rust parser compiled with `rustc -O`.

Three parsers share the same byte-level RLP scanner:

- full BAL materialization;
- dependency/scheduling view;
- reconstruction view.

The two partial views must reassemble every original canonical RLP byte string exactly before timing. A counting global allocator reports cumulative heap bytes and allocation calls for one full corpus pass.

The benchmark is still a microbenchmark, not a production-client benchmark. A native positive result rules out Python/Pydantic overhead as the sole explanation and justifies a production client prototype.
