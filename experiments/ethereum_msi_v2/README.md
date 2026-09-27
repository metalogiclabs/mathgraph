# Ethereum EELS / MSI v2

This experiment moves the MSI claim onto a pinned slice of Ethereum's executable Amsterdam specification.

CI checks out `ethereum/execution-specs@84e7d2c266e3319fc3882e72f379282bb1c40f2d` and refuses to run unless the Amsterdam `SLOAD`, `SSTORE`, `BlockAccessListBuilder`, no-op filtering test, and cross-index round-trip test are present. The local exhaustive model then tests the corresponding BAL consequence contract.

## Claim boundary

**WARRANTED if green:** for the finite BAL semantic slice represented here, future-equivalence erases untouched state exactly; each retained slot distinction has an ablation witness; and semantic commutation/noncommutation can be derived from protected post-state equality.

**Not yet warranted:** that the synthesized quotient is minimal for arbitrary EVM bytecode, arbitrary Ethereum blocks, gas/refund semantics, calls/reverts, or the full EELS state space.

The next decisive experiment is fixture-level: generate real EELS state/BAL fixtures, project them through the MSI learner, replay the quotient, and search adversarially for a protected continuation that distinguishes a collapsed pair.
