# finite_htilt_coordinate_raw_evidence_master_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_raw_evidence_master.lean`

Imports:

`HTilt.CoordinateChecklist`

## Claim

This artifact verifies the raw external-evidence master theorem for the finite H-Tilt coordinate checklist core.

It accepts raw finite-coordinate evidence:

- `∀ p ∈ coords, |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B`
- `∀ p ∈ coords, p.1 ≤ a - δ`
- `0 < δ`
- `0 ≤ c`
- `B / (2 * δ) < c`

It builds the checklist-native envelopes:

- `ResidualEnvelope a b B coords`
- `PositiveGapEnvelope a δ coords`

It also builds:

`CoordinateEnvelopeChecklist c a b B δ coords`

and proves shifted squared-modulus dominance:

`∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
