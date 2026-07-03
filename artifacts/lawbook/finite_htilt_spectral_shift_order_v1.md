# finite_htilt_spectral_shift_order_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_spectral_shift_order.lean`

Verified declarations:

- `HTiltSpectralShiftOrder.shiftedSqMod`
- `HTiltSpectralShiftOrder.shiftedSqMod_sub_eq`
- `HTiltSpectralShiftOrder.shiftedSqMod_gt_of_bound`

## Claim

For real `c a b u v`, define:

`shiftedSqMod c a b = (c + a)^2 + b^2`

Then:

`shiftedSqMod c a b - shiftedSqMod c u v = 2*c*(a-u) + ((a^2+b^2) - (u^2+v^2))`

If:

`|(u^2+v^2) - (a^2+b^2)| < 2*c*(a-u)`

then:

`shiftedSqMod c u v < shiftedSqMod c a b`

## Boundary

This artifact proves only a pure real algebraic inequality. It does not prove matrix spectral dominance, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical h-band behavior, or interpretive claims.
