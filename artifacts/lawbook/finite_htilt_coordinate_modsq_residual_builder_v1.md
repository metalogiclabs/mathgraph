# finite_htilt_coordinate_modsq_residual_builder_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_coordinate_modsq_residual_builder.lean`

Imports:

`HTilt.CoordinateChecklist`

## Claim

This artifact verifies a raw modulus-square residual builder for the finite H-Tilt coordinate checklist core.

Instead of requiring an already-packaged residual envelope:

`ResidualEnvelope a b B coords`

it accepts the raw pointwise evidence shape:

`∀ p ∈ coords, |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B`

and builds:

`ResidualEnvelope a b B coords`

It also verifies that this builder feeds the imported master theorem, yielding shifted squared-modulus dominance over the finite coordinate list.

## Boundary

This artifact treats coordinates only as finite real pairs. It does not prove that any coordinate is an eigenvalue, does not prove that the coordinate list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
