# finite_htilt_coordinate_checklist_master_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_checklist_master.lean`

Verified declarations:

- `HTiltCoordinateChecklistMaster.Coord`
- `HTiltCoordinateChecklistMaster.shiftedSqMod`
- `HTiltCoordinateChecklistMaster.residual`
- `HTiltCoordinateChecklistMaster.ResidualEnvelope`
- `HTiltCoordinateChecklistMaster.PositiveGapEnvelope`
- `HTiltCoordinateChecklistMaster.CoordinateEnvelopeChecklist`
- `HTiltCoordinateChecklistMaster.shiftedSqMod_sub_eq`
- `HTiltCoordinateChecklistMaster.shiftedSqMod_gt_of_bound`
- `HTiltCoordinateChecklistMaster.shiftedSqMod_gt_for_all_coords_of_envelopes`
- `HTiltCoordinateChecklistMaster.shiftedSqMod_gt_for_all_coords_of_explicit_c_envelopes`
- `HTiltCoordinateChecklistMaster.finite_coordinate_shifted_dominance_master`
- `HTiltCoordinateChecklistMaster.finite_coordinate_shifted_dominance_from_checklist`

## Claim

For a finite coordinate list `coords`, pointwise evidence over the list implies shifted dominance.

Inputs:

- `∀ p ∈ coords, residual a b p <= B`
- `∀ p ∈ coords, δ <= a - p.1`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

Lean verifies:

`∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

The bundled checklist form is also verified:

`CoordinateEnvelopeChecklist c a b B δ coords`

implies the same dominance conclusion.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
