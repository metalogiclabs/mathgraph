import HTilt.CoordinateChecklist
import Mathlib.Tactic.NormNum

/-!
# Finite H-Tilt / StrCC Certificate Bridge

This fixture records the bridge interpretation of the reusable
`RawCoordinateDominanceCertificate` core object.

The certificate can be read as a finite-coordinate continuation certificate:
raw residual evidence + raw strict-gap evidence + scalar side conditions
certify shifted dominance of a target coordinate against a finite competitor
list.

This is a downstream bridge/smoke artifact only. It is pre-spectral
finite-coordinate real/list algebra. It does not claim eigenvalues, spectra,
matrix-spectrum correspondence, Perron-Frobenius, convergence, or empirical
interpretation.
-/

namespace HTiltStrCCCertificateBridge

open HTilt.CoordinateChecklist

/-- A StrCC-style local survivor certificate represented by the core object. -/
abbrev FiniteCoordinateContinuationCertificate :=
  RawCoordinateDominanceCertificate

/-- The certified survivor property extracted from a finite certificate. -/
def CertifiedFiniteSurvivor
    (cert : FiniteCoordinateContinuationCertificate) : Prop :=
  ∀ p ∈ cert.coords,
    shiftedSqMod cert.c p.1 p.2 < shiftedSqMod cert.c cert.a cert.b

/-- Every continuation certificate yields the certified finite survivor property. -/
theorem finite_coordinate_certificate_yields_survivor
    (cert : FiniteCoordinateContinuationCertificate) :
    CertifiedFiniteSurvivor cert := by
  exact cert.shifted_dominance

/-- Every continuation certificate also yields its coordinate checklist. -/
theorem finite_coordinate_certificate_yields_checklist
    (cert : FiniteCoordinateContinuationCertificate) :
    CoordinateEnvelopeChecklist cert.c cert.a cert.b cert.B cert.δ cert.coords := by
  exact cert.to_checklist

/-- Concrete singleton bridge certificate. -/
def singletonBridgeCert : FiniteCoordinateContinuationCertificate where
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

theorem singleton_bridge_yields_survivor :
    CertifiedFiniteSurvivor singletonBridgeCert := by
  exact finite_coordinate_certificate_yields_survivor singletonBridgeCert

theorem singleton_bridge_yields_checklist :
    CoordinateEnvelopeChecklist
      singletonBridgeCert.c singletonBridgeCert.a singletonBridgeCert.b
      singletonBridgeCert.B singletonBridgeCert.δ singletonBridgeCert.coords := by
  exact finite_coordinate_certificate_yields_checklist singletonBridgeCert

end HTiltStrCCCertificateBridge
