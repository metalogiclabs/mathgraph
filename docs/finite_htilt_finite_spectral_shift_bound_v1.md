# Finite H-Tilt Finite Spectral Shift Bound v1

This document records the finite-list lift of the spectral-shift order theorem.

## Verified theorem

For a target real-coordinate mode `(a,b)`, real shift `c`, and a finite list of competitors `(u,v)`, Lean verifies:

If each competitor satisfies

`|(u^2+v^2) - (a^2+b^2)| < 2*c*(a-u)`

then each competitor has strictly smaller shifted squared modulus:

`shiftedSqMod c u v < shiftedSqMod c a b`.

Lean also verifies a shared-envelope version. If a scalar `B` satisfies

`|(u^2+v^2) - (a^2+b^2)| <= B`

for every listed competitor, and

`B < 2*c*(a-u)`

for every listed competitor, then every listed competitor is dominated after the shift.

## Role in the tower

This turns the single-pair spectral-shift inequality into a finite competitor interface. It is the safe algebraic boundary before talking about actual spectra of matrices.

## Boundary

This artifact does not prove actual spectrum extraction, finite-spectrum maximum construction, strict spectral abscissa, realness of the dominant mode, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
