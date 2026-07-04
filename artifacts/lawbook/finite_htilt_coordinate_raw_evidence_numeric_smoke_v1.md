# finite_htilt_coordinate_raw_evidence_numeric_smoke_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_raw_evidence_numeric_smoke.lean`

Imports:

`HTilt.CoordinateChecklist`

## Claim

This artifact verifies a concrete singleton raw-evidence smoke theorem for the reusable finite H-Tilt coordinate checklist core.

The example uses:

- target coordinate `(2, 0)`
- competitor list `[(0, 0)]`
- residual bound `B = 4`
- strict gap `δ = 1`
- shift `c = 3`

The raw residual check is:

`|(0^2 + 0^2) - (2^2 + 0^2)| ≤ 4`

The raw gap check is:

`0 ≤ 2 - 1`

The scalar side condition is:

`4 / (2 * 1) < 3`

Lean then proves:

`∀ p ∈ [((0 : ℝ), (0 : ℝ))], shiftedSqMod 3 p.1 p.2 < shiftedSqMod 3 2 0`

This reduces numerically to `9 < 25`.

## Boundary

This is only a concrete finite-coordinate smoke theorem. It does not prove that coordinates are eigenvalues, does not prove matrix-spectrum correspondence, does not extract spectral data, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
