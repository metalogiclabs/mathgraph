# finite_htilt_coordinate_core_module_v1

Status: VERIFIED_PROOF

Core Lean module:

`experiments/continuation_claim_audit_lab/lean_project/HTilt/CoordinateChecklist.lean`

Import path:

`HTilt.CoordinateChecklist`

Import smoke fixture:

`examples/verifier_fixtures/lean/htilt_coordinate_core_import_smoke.lean`

## Claim

The finite H-Tilt coordinate checklist tower has been factored into a reusable Lake library module.

The Lake project now declares a Lean library target named `HTilt`.

Lean verifies that:

- `HTilt/CoordinateChecklist.lean` compiles as a library module.
- A downstream fixture can import `HTilt.CoordinateChecklist`.
- The downstream fixture can reuse `finite_coordinate_shifted_dominance_master`.
- The downstream fixture can reuse `finite_coordinate_shifted_dominance_from_checklist`.

## Boundary

This artifact is a reusable-module refactor. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
