import HTilt.CoordinateChecklist
import Mathlib.Tactic.NormNum

/-!
# Finite H-Tilt Coordinate Certificate Core Smoke

This fixture checks that `RawCoordinateDominanceCertificate` is now exported by
the reusable `HTilt.CoordinateChecklist` core.
-/

namespace HTiltCoordinateCertificateCoreSmoke

open HTilt.CoordinateChecklist

def singletonCert : RawCoordinateDominanceCertificate where
  c := 3
  a := 2
  b := 0
  B := 4
  δ := 1
  coords := [((0 : ℝ), (0 : ℝ))]
  rawResidual := by
    intro p hp
    have hp0 : p = ((0 : ℝ), (0 : ℝ)) := by simpa using hp
    rw [hp0]
    norm_num
  rawGap := by
    intro p hp
    have hp0 : p = ((0 : ℝ), (0 : ℝ)) := by simpa using hp
    rw [hp0]
    norm_num
  delta_pos := by norm_num
  c_nonneg := by norm_num
  c_bound := by norm_num

theorem singleton_certificate_builds_checklist :
    CoordinateEnvelopeChecklist
      singletonCert.c singletonCert.a singletonCert.b singletonCert.B
        singletonCert.δ singletonCert.coords := by
  exact singletonCert.to_checklist

theorem singleton_certificate_shifted_dominance :
    ∀ p ∈ singletonCert.coords,
      shiftedSqMod singletonCert.c p.1 p.2 <
        shiftedSqMod singletonCert.c singletonCert.a singletonCert.b := by
  exact singletonCert.shifted_dominance

end HTiltCoordinateCertificateCoreSmoke
