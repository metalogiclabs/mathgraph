# Finite H-Tilt Coordinate Checklist Master v1

This document records the canonical compressed theorem for the pre-spectral coordinate checklist tower.

## Verified master theorem

For a finite coordinate list `coords`, Lean verifies that the following inputs:

- `∀ p ∈ coords, residual a b p <= B`
- `∀ p ∈ coords, δ <= a - p.1`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

imply:

`∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`.

Lean also verifies a bundled checklist form:

`CoordinateEnvelopeChecklist c a b B δ coords`

implies the same shifted-dominance conclusion.

## Role in the tower

This is the headline Lawbook theorem for the pre-spectral finite-coordinate layer. Earlier artifacts introduced the algebraic inequality, envelopes, checklist, projections, constructors, nil/cons builders, and direct list builder. This artifact compresses those bricks into a single citeable theorem.

## Boundary

This artifact does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
