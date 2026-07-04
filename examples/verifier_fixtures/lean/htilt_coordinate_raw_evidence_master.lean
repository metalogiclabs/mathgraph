import HTilt.CoordinateChecklist

/-!
# Finite H-Tilt Coordinate Raw Evidence Master

This fixture proves the external-evidence version of the finite coordinate
dominance theorem.

It accepts raw finite-coordinate evidence:

* raw modulus-square residual evidence,
* raw strict real-part gap evidence,

and feeds both into the reusable `HTilt.CoordinateChecklist` core.

This is still pre-spectral. Coordinates are only finite real pairs.
-/

namespace HTiltCoordinateRawEvidenceMaster

open HTilt.CoordinateChecklist

/-- Raw modulus-square residual evidence builds the residual envelope. -/
theorem raw_modsq_residual_builds_residual_envelope
    (a b B : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B) :
    ResidualEnvelope a b B coords := by
  intro p hp
  unfold residual
  exact hres p hp

/-- Raw strict real-part gap evidence builds the positive-gap envelope. -/
theorem raw_strict_gap_builds_positive_gap_envelope
    (a δ : ℝ)
    (coords : List Coord)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ) :
    PositiveGapEnvelope a δ coords := by
  intro p hp
  have h := hgap p hp
  linarith

/--
Raw external finite-coordinate evidence implies shifted dominance.

Inputs:

* raw modulus-square residual evidence,
* raw strict real-part gap evidence,
* scalar side conditions.

Output:

* shifted squared-modulus dominance over every coordinate in the finite list.
-/
theorem finite_coordinate_shifted_dominance_from_raw_evidence
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_master
    c a b B δ coords
    (raw_modsq_residual_builds_residual_envelope a b B coords hres)
    (raw_strict_gap_builds_positive_gap_envelope a δ coords hgap)
    delta_pos c_nonneg c_bound

/--
Raw external finite-coordinate evidence can also build the bundled checklist.
-/
theorem coordinate_envelope_checklist_from_raw_evidence
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    CoordinateEnvelopeChecklist c a b B δ coords := by
  exact list_coordinate_envelope_checklist
    c a b B δ coords
    (raw_modsq_residual_builds_residual_envelope a b B coords hres)
    (raw_strict_gap_builds_positive_gap_envelope a δ coords hgap)
    delta_pos c_nonneg c_bound

end HTiltCoordinateRawEvidenceMaster
