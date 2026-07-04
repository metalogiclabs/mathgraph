# finite_htilt_coordinate_list_checklist_builder_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_list_checklist_builder.lean`

Verified declarations:

- `HTiltCoordinateListChecklistBuilder.Coord`
- `HTiltCoordinateListChecklistBuilder.shiftedSqMod`
- `HTiltCoordinateListChecklistBuilder.residual`
- `HTiltCoordinateListChecklistBuilder.ResidualEnvelope`
- `HTiltCoordinateListChecklistBuilder.PositiveGapEnvelope`
- `HTiltCoordinateListChecklistBuilder.CoordinateEnvelopeChecklist`
- `HTiltCoordinateListChecklistBuilder.pointwise_residual_envelope`
- `HTiltCoordinateListChecklistBuilder.pointwise_positive_gap_envelope`
- `HTiltCoordinateListChecklistBuilder.list_coordinate_envelope_checklist`
- `HTiltCoordinateListChecklistBuilder.shiftedSqMod_gt_for_all_coords_of_list_checklist_evidence`

## Claim

For a finite coordinate list `coords`, pointwise evidence over the list constructs the bundled checklist.

Inputs:

- `∀ p ∈ coords, residual a b p <= B`
- `∀ p ∈ coords, δ <= a - p.1`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

Lean verifies:

`CoordinateEnvelopeChecklist c a b B δ coords`

and therefore:

`∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
