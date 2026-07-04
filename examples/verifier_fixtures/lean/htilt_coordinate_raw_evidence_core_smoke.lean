import HTilt.CoordinateChecklist

/-! Import smoke tests for the reusable raw-evidence coordinate API. -/

namespace HTiltCoordinateRawEvidenceCoreSmoke

open HTilt.CoordinateChecklist

theorem smoke_raw_evidence_dominance_from_core
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords, shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_from_raw_evidence
    c a b B δ coords hres hgap delta_pos c_nonneg c_bound

theorem smoke_raw_evidence_checklist_from_core
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    CoordinateEnvelopeChecklist c a b B δ coords := by
  exact coordinate_envelope_checklist_from_raw_evidence
    c a b B δ coords hres hgap delta_pos c_nonneg c_bound

end HTiltCoordinateRawEvidenceCoreSmoke
