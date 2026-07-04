# Finite H-Tilt Coordinate List Checklist Builder v1

This document records the direct finite-list builder for the bundled coordinate-envelope checklist.

## Verified theorem family

For a finite coordinate list `coords`, Lean verifies:

- `pointwise_residual_envelope`
- `pointwise_positive_gap_envelope`
- `list_coordinate_envelope_checklist`
- `shiftedSqMod_gt_for_all_coords_of_list_checklist_evidence`

The builder inputs are:

- `∀ p ∈ coords, residual a b p <= B`
- `∀ p ∈ coords, δ <= a - p.1`
- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

The builder constructs:

`CoordinateEnvelopeChecklist c a b B δ coords`

and therefore shifted dominance for every coordinate in `coords`.

## Role in the tower

Nil and cons give base and extension constructors. This artifact compresses that construction into a direct finite-list checklist builder from pointwise evidence.

## Boundary

This artifact does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
