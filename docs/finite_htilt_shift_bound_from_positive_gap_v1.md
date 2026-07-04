# Finite H-Tilt Shift Bound From Positive Gap v1

This document records the positive-gap scalar bound in the finite H-Tilt spectral-alignment tower.

## Verified theorem

For a target real-coordinate mode `(a,b)`, finite competitors `(u,v)`, real shift `c`, residual envelope `B`, and gap lower bound `δ`, Lean verifies:

If

`δ <= a - u`

for every competitor,

`|(u^2+v^2) - (a^2+b^2)| <= B`

for every competitor,

`0 <= c`,

and

`B < 2*c*δ`,

then every competitor is dominated after the shift:

`shiftedSqMod c u v < shiftedSqMod c a b`.

## Role in the tower

This converts the finite-list shared-envelope theorem into a single scalar shift condition. It is the last purely real/list algebra bridge before introducing actual finite spectra.

## Boundary

This artifact does not prove actual spectrum extraction, construction of `B`, construction of `δ`, strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
