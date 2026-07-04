# Finite H-Tilt Explicit Shift Bound v1

This document records the explicit scalar shift rule in the finite H-Tilt spectral-alignment tower.

## Verified theorem

For a target real-coordinate mode `(a,b)`, finite competitors `(u,v)`, real shift `c`, residual envelope `B`, and positive gap lower bound `δ`, Lean verifies:

If

`0 < δ`,

`0 <= c`,

`B / (2*δ) < c`,

`|(u^2+v^2) - (a^2+b^2)| <= B`

for every competitor, and

`δ <= a - u`

for every competitor, then every competitor is dominated after the shift:

`shiftedSqMod c u v < shiftedSqMod c a b`.

## Role in the tower

This converts the positive-gap scalar condition `B < 2*c*δ` into the explicit computable choice rule `c > B/(2δ)`.

## Boundary

This artifact does not prove actual spectrum extraction, construction of `B`, construction of `δ`, strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
