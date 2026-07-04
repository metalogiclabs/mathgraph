# finite_htilt_coordinate_gap_envelope_from_witness_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_gap_envelope_from_witness.lean`

Imports:

`HTilt.CoordinateChecklist`

## Claim

This artifact verifies a witness-facing gap interface for the reusable finite H-Tilt coordinate checklist core.

Input shape:

`∀ p ∈ coords, p.1 ≤ a - δ`

Output shape:

`PositiveGapEnvelope a δ coords`

It also verifies that raw residual evidence plus this strict-gap witness can build:

`CoordinateEnvelopeChecklist c a b B δ coords`

and prove shifted squared-modulus dominance over every coordinate in the finite list.

## Boundary

This artifact is pre-spectral finite-coordinate real/list algebra only. It does not prove that coordinates are eigenvalues, does not prove matrix-spectrum correspondence, does not extract spectral data, does not prove Perron alignment, and does not invoke Perron-Frobenius.
