# finite_htilt_shift_bound_explicit_c_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_shift_bound_explicit_c.lean`

Verified declarations:

- `HTiltShiftBoundExplicitC.shiftedSqMod`
- `HTiltShiftBoundExplicitC.shiftedSqMod_sub_eq`
- `HTiltShiftBoundExplicitC.shiftedSqMod_gt_of_bound`
- `HTiltShiftBoundExplicitC.shiftedSqMod_gt_for_all_competitors_of_shared_bound`
- `HTiltShiftBoundExplicitC.shiftedSqMod_gt_for_all_competitors_of_positive_gap`
- `HTiltShiftBoundExplicitC.shiftedSqMod_gt_for_all_competitors_of_explicit_c_bound`

## Claim

For a target real-coordinate mode `(a,b)`, finite competitors `(u,v)`, residual envelope `B`, and positive gap lower bound `δ`:

If

`0 < δ`,

`0 <= c`,

`B / (2*δ) < c`,

every residual satisfies

`|(u^2+v^2) - (a^2+b^2)| <= B`,

and every competitor satisfies

`δ <= a - u`,

then every listed competitor has strictly smaller shifted squared modulus:

`shiftedSqMod c u v < shiftedSqMod c a b`.

## Boundary

This artifact is pure real/list algebra. It does not extract a spectrum from a matrix, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
