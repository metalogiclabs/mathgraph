# Ethereum MSI v3 — typed minimal interfaces

The v2 result suggested compressing Ethereum's Block Access List. Reading the normative EIP-7928 contract adversarially shows that this is too coarse a question.

EIP-7928 intentionally serves multiple consequence families:

1. **Dependency / parallel-validation interface** — accessed addresses and slots matter even when unchanged.
2. **Reconstruction / executionless-update interface** — post-state changes matter; no-op writes can disappear.

These interfaces are not interchangeable. MSI therefore predicts two different minimal quotients rather than one globally minimal BAL.

V3 exhaustively verifies this typed separation in the finite semantic core:
- the dependency quotient is strictly coarser than the combined BAL consequence;
- the reconstruction quotient is also strictly coarser;
- neither quotient subsumes the other (explicit witnesses exist both ways);
- their product recovers the combined consequence;
- no-op accesses are erased from reconstruction while necessarily retained for dependency analysis.

This corrects the naive “compress BAL” hypothesis. The reusable result is stronger: **minimality is relative to protected consequences; a multi-purpose protocol object is naturally the product/refinement of multiple minimal sufficient interfaces.**

Verification boundary: exact finite abstraction of the normative EIP-7928 inclusion/change rules, with the EIP and EELS semantic anchors pinned in CI. Full protocol minimality remains UNKNOWN.
