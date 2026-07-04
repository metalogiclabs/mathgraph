# Finite H-Tilt Spectrum Coordinate Envelope v1

This document records the pre-spectral coordinate-envelope layer in the finite H-Tilt spectral-alignment tower.

## Verified theorem

Lean treats coordinates as real pairs:

`Coord := ℝ × ℝ`.

For a finite coordinate list `coords`, target coordinate `(a,b)`, residual envelope `B`, positive-gap envelope `δ`, and shift `c`, Lean verifies:

If

`ResidualEnvelope a b B coords`,

`PositiveGapEnvelope a δ coords`,

`0 < δ`,

`0 <= c`,

and

`B / (2*δ) < c`,

then every coordinate in the list is dominated after the shift:

`shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

## Role in the tower

This introduces named envelope predicates for finite coordinate lists. It is the bridge from arbitrary finite competitor algebra toward spectral-coordinate reasoning, while keeping matrix-spectrum claims outside the boundary.

## Boundary

This artifact does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
