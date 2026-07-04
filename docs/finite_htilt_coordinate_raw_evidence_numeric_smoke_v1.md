# Finite H-Tilt Coordinate Raw Evidence Numeric Smoke v1

This document records a concrete singleton smoke theorem for the reusable `HTilt.CoordinateChecklist` core.

## Concrete values

- target coordinate: `(2, 0)`
- competitor list: `[(0, 0)]`
- residual bound: `B = 4`
- strict gap: `δ = 1`
- shift: `c = 3`

## Verified checks

Residual:

`|(0^2 + 0^2) - (2^2 + 0^2)| ≤ 4`

Gap:

`0 ≤ 2 - 1`

Scalar bound:

`4 / (2 * 1) < 3`

Dominance:

`shiftedSqMod 3 0 0 < shiftedSqMod 3 2 0`

Numerically this is `9 < 25`.

## Boundary

This is a finite-coordinate arithmetic smoke theorem only. It does not prove eigenvalue existence, matrix-spectrum correspondence, spectrum extraction, Perron-root alignment, Perron-Frobenius, convergence, or empirical claims.
