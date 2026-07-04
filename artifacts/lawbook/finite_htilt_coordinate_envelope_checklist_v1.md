# finite_htilt_coordinate_envelope_checklist_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_envelope_checklist.lean`

Verified declarations:

- `HTiltCoordinateEnvelopeChecklist.Coord`
- `HTiltCoordinateEnvelopeChecklist.shiftedSqMod`
- `HTiltCoordinateEnvelopeChecklist.residual`
- `HTiltCoordinateEnvelopeChecklist.ResidualEnvelope`
- `HTiltCoordinateEnvelopeChecklist.PositiveGapEnvelope`
- `HTiltCoordinateEnvelopeChecklist.CoordinateEnvelopeChecklist`
- `HTiltCoordinateEnvelopeChecklist.shiftedSqMod_sub_eq`
- `HTiltCoordinateEnvelopeChecklist.shiftedSqMod_gt_of_bound`
- `HTiltCoordinateEnvelopeChecklist.shiftedSqMod_gt_for_all_coords_of_envelopes`
- `HTiltCoordinateEnvelopeChecklist.shiftedSqMod_gt_for_all_coords_of_explicit_c_envelopes`
- `HTiltCoordinateEnvelopeChecklist.shiftedSqMod_gt_for_all_coords_of_checklist`

## Claim

A single bundled checklist over a finite coordinate list implies shifted dominance for every coordinate.

The checklist consists of:

- `ResidualEnvelope a b B coords`
- `PositiveGapEnvelope a δ coords`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

From this, Lean verifies:

`∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
