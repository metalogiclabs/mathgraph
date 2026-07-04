# Finite H-Tilt Coordinate Gap Envelope From Witness v1

This document records a witness-facing gap API for the reusable `HTilt.CoordinateChecklist` core.

## Verified witness interface

Input:

`∀ p ∈ coords, p.1 ≤ a - δ`

Output:

`PositiveGapEnvelope a δ coords`

## Verified wrappers

The artifact also verifies that raw residual witnesses and strict-gap witnesses build the bundled checklist and prove shifted squared-modulus dominance through the reusable core API.

## Boundary

This artifact is still pre-spectral. It does not prove eigenvalue existence, matrix-spectrum correspondence, spectrum extraction, Perron-root alignment, Perron-Frobenius, convergence, or empirical claims.
