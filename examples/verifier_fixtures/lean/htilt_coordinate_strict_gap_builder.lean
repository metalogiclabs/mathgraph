import HTilt.CoordinateChecklist

/-!
# Finite H-Tilt Coordinate Strict Gap Builder

This fixture proves a small builder lemma for the pre-spectral coordinate
checklist core.

It treats coordinates only as finite real pairs `(u,v)`. It does not prove that
any coordinate is an eigenvalue or that the coordinate list is a matrix spectrum.

If every competitor real part satisfies `p.1 ≤ a - δ`, then the positive-gap
envelope `PositiveGapEnvelope a δ coords` holds.
-/

namespace HTiltCoordinateStrictGapBuilder

open HTilt.CoordinateChecklist

/--
A pointwise strict-real-gap style bound builds the positive-gap envelope.

The input shape `p.1 ≤ a - δ` is closer to spectral-gap language.
The envelope shape is `δ ≤ a - p.1`.
-/
theorem strict_gap_bound_builds_positive_gap_envelope
    (a δ : ℝ)
    (coords : List Coord)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ) :
    PositiveGapEnvelope a δ coords := by
  intro p hp
  have h := hgap p hp
  linarith

/--
Strict-gap builder plugged into the imported master theorem.

If every coordinate has residual at most `B`, every coordinate real part is at
most `a - δ`, and the scalar side conditions hold, then shifted dominance follows.
-/
theorem finite_coordinate_shifted_dominance_from_strict_gap
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_master
    c a b B δ coords hres
    (strict_gap_bound_builds_positive_gap_envelope a δ coords hgap)
    delta_pos c_nonneg c_bound

end HTiltCoordinateStrictGapBuilder
