# Finite H-Tilt Coordinate Checklist Projection v1

This document records projection lemmas for the bundled coordinate-envelope checklist.

## Verified theorem family

Lean defines:

`CoordinateEnvelopeChecklist c a b B δ coords`

as a bundled predicate containing:

- `ResidualEnvelope a b B coords`
- `PositiveGapEnvelope a δ coords`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

Lean verifies projection lemmas exposing each component:

- `checklist_residual_envelope`
- `checklist_positive_gap_envelope`
- `checklist_delta_pos`
- `checklist_c_nonneg`
- `checklist_explicit_c_bound`

## Role in the tower

This makes the checklist usable as a reusable certificate object. Later proofs can consume only the component they need without manually unpacking the whole checklist.

## Boundary

This artifact does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
