# finite_htilt_coordinate_nil_checklist_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_nil_checklist.lean`

Verified declarations:

- `HTiltCoordinateNilChecklist.Coord`
- `HTiltCoordinateNilChecklist.shiftedSqMod`
- `HTiltCoordinateNilChecklist.residual`
- `HTiltCoordinateNilChecklist.ResidualEnvelope`
- `HTiltCoordinateNilChecklist.PositiveGapEnvelope`
- `HTiltCoordinateNilChecklist.CoordinateEnvelopeChecklist`
- `HTiltCoordinateNilChecklist.nil_residual_envelope`
- `HTiltCoordinateNilChecklist.nil_positive_gap_envelope`
- `HTiltCoordinateNilChecklist.nil_coordinate_envelope_checklist`
- `HTiltCoordinateNilChecklist.shiftedSqMod_gt_for_all_coords_of_nil_checklist_evidence`

## Claim

For the empty coordinate list `[]`, the residual and positive-gap envelopes are vacuous.

Inputs:

- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

Lean verifies:

`CoordinateEnvelopeChecklist c a b B δ []`

and therefore:

`∀ p ∈ [], shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
