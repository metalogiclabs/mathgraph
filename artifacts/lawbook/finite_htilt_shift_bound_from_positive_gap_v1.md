# finite_htilt_shift_bound_from_positive_gap_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_shift_bound_from_positive_gap.lean`

Verified declarations:

- `HTiltShiftBoundFromPositiveGap.shiftedSqMod`
- `HTiltShiftBoundFromPositiveGap.shiftedSqMod_sub_eq`
- `HTiltShiftBoundFromPositiveGap.shiftedSqMod_gt_of_bound`
- `HTiltShiftBoundFromPositiveGap.shiftedSqMod_gt_for_all_competitors_of_shared_bound`
- `HTiltShiftBoundFromPositiveGap.shiftedSqMod_gt_for_all_competitors_of_positive_gap`

## Claim

For a target real-coordinate mode `(a,b)`, real shift `c`, finite competitors `(u,v)`, residual envelope `B`, and positive-gap lower bound `δ`:

If every competitor satisfies

`δ <= a - u`

and every residual satisfies

`|(u^2+v^2) - (a^2+b^2)| <= B`

and

`0 <= c`

and

`B < 2*c*δ`

then every listed competitor has strictly smaller shifted squared modulus:

`shiftedSqMod c u v < shiftedSqMod c a b`.

## Boundary

This artifact is pure real/list algebra. It does not extract a spectrum from a matrix, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
