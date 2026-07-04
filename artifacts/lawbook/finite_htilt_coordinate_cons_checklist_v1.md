# finite_htilt_coordinate_cons_checklist_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_cons_checklist.lean`

Verified declarations:

- `HTiltCoordinateConsChecklist.Coord`
- `HTiltCoordinateConsChecklist.shiftedSqMod`
- `HTiltCoordinateConsChecklist.residual`
- `HTiltCoordinateConsChecklist.ResidualEnvelope`
- `HTiltCoordinateConsChecklist.PositiveGapEnvelope`
- `HTiltCoordinateConsChecklist.CoordinateEnvelopeChecklist`
- `HTiltCoordinateConsChecklist.cons_residual_envelope`
- `HTiltCoordinateConsChecklist.cons_positive_gap_envelope`
- `HTiltCoordinateConsChecklist.cons_coordinate_envelope_checklist`
- `HTiltCoordinateConsChecklist.shiftedSqMod_gt_for_all_coords_of_cons_checklist_evidence`

## Claim

If a tail coordinate list already has:

`CoordinateEnvelopeChecklist c a b B δ coords`

and a new head coordinate `p` satisfies:

- `residual a b p <= B`
- `δ <= a - p.1`

then Lean verifies:

`CoordinateEnvelopeChecklist c a b B δ (p :: coords)`

and therefore:

`∀ q ∈ p :: coords, shiftedSqMod c q.1 q.2 < shiftedSqMod c a b`.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
