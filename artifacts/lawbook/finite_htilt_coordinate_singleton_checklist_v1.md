# finite_htilt_coordinate_singleton_checklist_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_singleton_checklist.lean`

Verified declarations:

- `HTiltCoordinateSingletonChecklist.Coord`
- `HTiltCoordinateSingletonChecklist.shiftedSqMod`
- `HTiltCoordinateSingletonChecklist.residual`
- `HTiltCoordinateSingletonChecklist.ResidualEnvelope`
- `HTiltCoordinateSingletonChecklist.PositiveGapEnvelope`
- `HTiltCoordinateSingletonChecklist.CoordinateEnvelopeChecklist`
- `HTiltCoordinateSingletonChecklist.singleton_residual_envelope`
- `HTiltCoordinateSingletonChecklist.singleton_positive_gap_envelope`
- `HTiltCoordinateSingletonChecklist.singleton_coordinate_envelope_checklist`
- `HTiltCoordinateSingletonChecklist.shiftedSqMod_gt_of_singleton_checklist_evidence`

## Claim

For a singleton coordinate list `[p]`, pointwise evidence constructs the bundled checklist.

Inputs:

- `residual a b p <= B`
- `δ <= a - p.1`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

Lean verifies:

`CoordinateEnvelopeChecklist c a b B δ [p]`

and therefore:

`shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that `p` is an eigenvalue, does not prove that `[p]` is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
