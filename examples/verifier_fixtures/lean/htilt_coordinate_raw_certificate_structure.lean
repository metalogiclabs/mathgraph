import HTilt.CoordinateChecklist

/-!
# Finite H-Tilt Coordinate Raw Certificate Structure

This fixture bundles the raw finite-coordinate evidence required by the
reusable `HTilt.CoordinateChecklist` core into one certificate object.

It is a compaction layer:
raw residual evidence + raw strict-gap evidence + scalar side conditions
become a reusable certificate whose theorem yields shifted dominance.

This is pre-spectral finite-coordinate real/list algebra only.
-/

namespace HTiltCoordinateRawCertificateStructure

open HTilt.CoordinateChecklist

structure RawCoordinateDominanceCertificate where
  c : ℝ
  a : ℝ
  b : ℝ
  B : ℝ
  δ : ℝ
  coords : List Coord
  rawResidual :
    ∀ p ∈ coords,
      |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B
  rawGap :
    ∀ p ∈ coords, p.1 ≤ a - δ
  delta_pos : 0 < δ
  c_nonneg : 0 ≤ c
  c_bound : B / (2 * δ) < c

/-- A raw coordinate certificate yields shifted dominance over its list. -/
theorem RawCoordinateDominanceCertificate.shifted_dominance
    (cert : RawCoordinateDominanceCertificate) :
    ∀ p ∈ cert.coords,
      shiftedSqMod cert.c p.1 p.2 < shiftedSqMod cert.c cert.a cert.b := by
  exact finite_coordinate_shifted_dominance_from_raw_evidence
    cert.c cert.a cert.b cert.B cert.δ cert.coords
    cert.rawResidual cert.rawGap cert.delta_pos cert.c_nonneg cert.c_bound

/-- The same certificate object builds the bundled checklist. -/
theorem RawCoordinateDominanceCertificate.to_checklist
    (cert : RawCoordinateDominanceCertificate) :
    CoordinateEnvelopeChecklist cert.c cert.a cert.b cert.B cert.δ cert.coords := by
  exact coordinate_envelope_checklist_from_raw_evidence
    cert.c cert.a cert.b cert.B cert.δ cert.coords
    cert.rawResidual cert.rawGap cert.delta_pos cert.c_nonneg cert.c_bound

end HTiltCoordinateRawCertificateStructure
