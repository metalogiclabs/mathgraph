# Finite H-Tilt Coordinate Modulus-Square Residual Builder v1

This document records a residual-evidence adapter theorem for the reusable `HTilt.CoordinateChecklist` core.

## Verified builder

Input shape:

`∀ p ∈ coords, |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B`

Output shape:

`ResidualEnvelope a b B coords`

This is useful because the checklist core consumes `ResidualEnvelope`, while future spectral or coordinate data will more naturally produce raw modulus-square residual bounds.

## Verified dominance wrapper

The artifact also verifies that raw residual evidence, positive-gap evidence, and scalar side conditions feed the imported master theorem to produce shifted squared-modulus dominance over every coordinate in the finite list.

## Boundary

This artifact is still pre-spectral. It does not prove that coordinates are eigenvalues, does not prove matrix-spectrum correspondence, does not extract spectral data, does not prove Perron alignment, and does not invoke Perron-Frobenius.
