import HTilt.CoordinateChecklist

/-!
# H-Tilt Coordinate Core Import Smoke

This fixture verifies that the reusable `HTilt.CoordinateChecklist` core module
can be imported from outside the Lake project root and used by downstream
fixtures.
-/

namespace HTiltCoordinateCoreImportSmoke

open HTilt.CoordinateChecklist

theorem smoke_master_from_core
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_master
    c a b B δ coords hres hgap delta_pos c_nonneg c_bound

theorem smoke_checklist_from_core
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_from_checklist
    c a b B δ coords checklist

end HTiltCoordinateCoreImportSmoke
