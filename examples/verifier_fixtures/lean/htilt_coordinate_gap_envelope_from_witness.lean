import HTilt.CoordinateChecklist

/-!
# Finite H-Tilt Coordinate Gap Envelope From Witness

This fixture exposes a witness-facing gap API over the reusable
`HTilt.CoordinateChecklist` core.

It treats coordinates only as finite real pairs. It does not prove that any
coordinate is an eigenvalue or that a coordinate list is a matrix spectrum.
-/

namespace HTiltCoordinateGapEnvelopeFromWitness

open HTilt.CoordinateChecklist

/--
A supplied strict-gap witness builds the checklist-native positive-gap envelope.

Input shape:

`∀ p ∈ coords, p.1 ≤ a - δ`

Output shape:

`PositiveGapEnvelope a δ coords`
-/
theorem positive_gap_envelope_from_delta_witness
    (a δ : ℝ)
    (coords : List Coord)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ) :
    PositiveGapEnvelope a δ coords := by
  exact raw_strict_gap_builds_positive_gap_envelope a δ coords hgap

/--
Raw residual evidence and a supplied strict-gap witness build the bundled
coordinate-envelope checklist.
-/
theorem checklist_from_raw_witnesses
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
  exact coordinate_envelope_checklist_from_raw_evidence
    c a b B δ coords hres hgap delta_pos c_nonneg c_bound

/--
Raw residual evidence and a supplied strict-gap witness imply shifted dominance
through the reusable core API.
-/
theorem dominance_from_raw_witnesses
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
  exact finite_coordinate_shifted_dominance_from_raw_evidence
    c a b B δ coords hres hgap delta_pos c_nonneg c_bound

end HTiltCoordinateGapEnvelopeFromWitness
