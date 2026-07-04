# Finite H-Tilt Coordinate Raw Evidence Master v1

This document records the external-evidence master theorem for the reusable `HTilt.CoordinateChecklist` core.

## Verified raw inputs

Residual input:

`∀ p ∈ coords, |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B`

Strict-gap input:

`∀ p ∈ coords, p.1 ≤ a - δ`

Scalar side conditions:

- `0 < δ`
- `0 ≤ c`
- `B / (2 * δ) < c`

## Verified outputs

The raw evidence builds:

- `ResidualEnvelope a b B coords`
- `PositiveGapEnvelope a δ coords`
- `CoordinateEnvelopeChecklist c a b B δ coords`

and proves:

`∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b`

## Role in the tower

This is the cleanest pre-spectral API so far. Future spectral or finite-coordinate code does not need to speak the internal checklist-envelope language. It can provide raw residual evidence and raw strict real-part gap evidence, then call this theorem.

## Boundary

This artifact is still pre-spectral. It does not prove that coordinates are eigenvalues, does not prove matrix-spectrum correspondence, does not extract spectral data, does not construct `B` or `δ` from spectral data, does not prove Perron alignment, and does not invoke Perron-Frobenius.
