# Finite H-Tilt Coordinate Core Module v1

This document records the refactor of the finite H-Tilt coordinate checklist tower into a reusable Lean core module.

## Core module

`experiments/continuation_claim_audit_lab/lean_project/HTilt/CoordinateChecklist.lean`

Import path:

`HTilt.CoordinateChecklist`

## Lake target

The Lake project now declares a library target named `HTilt`.

## Verified smoke fixture

`examples/verifier_fixtures/lean/htilt_coordinate_core_import_smoke.lean`

The smoke fixture imports the core module and reuses:

- `finite_coordinate_shifted_dominance_master`
- `finite_coordinate_shifted_dominance_from_checklist`

## Role in the tower

Earlier artifacts proved the coordinate checklist theorem family as standalone fixtures. This artifact turns that theorem family into a reusable Lean API for future H-Tilt work.

## Boundary

This artifact does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, realness of a dominant eigenvalue, Perron-root alignment, irreducibility transfer, Perron-Frobenius invocation, convergence, empirical behavior, or interpretive claims.
