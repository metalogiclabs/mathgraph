# Finite H-Tilt Coordinate Nil Checklist v1

This document records the nil/base-case constructor for the bundled coordinate-envelope checklist.

## Verified theorem family

For the empty coordinate list `[]`, Lean verifies:

- `nil_residual_envelope`
- `nil_positive_gap_envelope`
- `nil_coordinate_envelope_checklist`
- `shiftedSqMod_gt_for_all_coords_of_nil_checklist_evidence`

The residual and positive-gap envelopes are vacuous for `[]`. Thus scalar side conditions are enough:

- `0 < δ`
- `0 <= c`
- `B/(2*δ) < c`

## Role in the tower

Cons construction gives the extension step. Nil construction gives the base case. Together they form an induction-style finite coordinate-list certificate builder.

## Boundary

This artifact does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
