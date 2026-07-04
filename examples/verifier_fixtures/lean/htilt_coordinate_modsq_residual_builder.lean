import HTilt.CoordinateChecklist

/-!
# Finite H-Tilt Coordinate Modulus-Square Residual Builder

This fixture proves a small residual-envelope builder for the reusable
`HTilt.CoordinateChecklist` core.

It treats coordinates only as finite real pairs `(u,v)`. It does not prove that
any coordinate is an eigenvalue or that the coordinate list is a matrix spectrum.

If every coordinate satisfies the raw modulus-square residual bound

`|(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B`,

then the checklist-native `ResidualEnvelope a b B coords` holds.
-/

namespace HTiltCoordinateModSqResidualBuilder

open HTilt.CoordinateChecklist

/--
A raw modulus-square residual bound builds the residual envelope.

This is mostly definitional, but it exposes the external evidence shape expected
from future spectral or finite-coordinate data.
-/
theorem modsq_residual_bound_builds_residual_envelope
    (a b B : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B) :
    ResidualEnvelope a b B coords := by
  intro p hp
  unfold residual
  exact hres p hp

/--
Raw residual builder plugged into the imported master theorem.

If raw modulus-square residual evidence, checklist-native positive-gap evidence,
and the scalar side conditions hold, then shifted dominance follows.
-/
theorem finite_coordinate_shifted_dominance_from_modsq_residual
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_master
    c a b B δ coords
    (modsq_residual_bound_builds_residual_envelope a b B coords hres)
    hgap delta_pos c_nonneg c_bound

end HTiltCoordinateModSqResidualBuilder
