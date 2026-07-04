# finite_htilt_finite_spectral_shift_bound_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_finite_spectral_shift_bound.lean`

Verified declarations:

- `HTiltFiniteSpectralShiftBound.shiftedSqMod`
- `HTiltFiniteSpectralShiftBound.shiftedSqMod_sub_eq`
- `HTiltFiniteSpectralShiftBound.shiftedSqMod_gt_of_bound`
- `HTiltFiniteSpectralShiftBound.shiftedSqMod_gt_for_all_competitors`
- `HTiltFiniteSpectralShiftBound.shiftedSqMod_gt_for_all_competitors_of_shared_bound`

## Claim

The single-pair shifted squared-modulus dominance theorem lifts to a finite list of real-coordinate competitors.

If every competitor satisfies the pairwise bound

`|(u^2+v^2) - (a^2+b^2)| < 2*c*(a-u)`

then every listed competitor has strictly smaller shifted squared modulus.

A second theorem verifies a shared-envelope version: if a scalar `B` bounds every residual and `B` is strictly below every corresponding shift gap, then every listed competitor is dominated after the shift.

## Boundary

This artifact is pure real/list algebra. It does not extract a spectrum from a matrix, does not construct a spectral maximum, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
