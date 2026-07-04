# finite_htilt_coordinate_checklist_projection_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_checklist_projection.lean`

Verified declarations:

- `HTiltCoordinateChecklistProjection.Coord`
- `HTiltCoordinateChecklistProjection.shiftedSqMod`
- `HTiltCoordinateChecklistProjection.residual`
- `HTiltCoordinateChecklistProjection.ResidualEnvelope`
- `HTiltCoordinateChecklistProjection.PositiveGapEnvelope`
- `HTiltCoordinateChecklistProjection.CoordinateEnvelopeChecklist`
- `HTiltCoordinateChecklistProjection.checklist_residual_envelope`
- `HTiltCoordinateChecklistProjection.checklist_positive_gap_envelope`
- `HTiltCoordinateChecklistProjection.checklist_delta_pos`
- `HTiltCoordinateChecklistProjection.checklist_c_nonneg`
- `HTiltCoordinateChecklistProjection.checklist_explicit_c_bound`

## Claim

A bundled coordinate-envelope checklist exposes each component through verified projection lemmas.

From

`CoordinateEnvelopeChecklist c a b B δ coords`

Lean verifies projections to:

- `ResidualEnvelope a b B coords`
- `PositiveGapEnvelope a δ coords`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
