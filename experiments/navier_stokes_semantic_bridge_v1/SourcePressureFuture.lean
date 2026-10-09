import PressureEnvelopeObstruction
import NavierStokes.R3.ComparisonYoung
import NavierStokes.R3EnergyAbsorption

/-!
V18: The manuscript-style pressure envelope is sufficient for the
*protected downstream energy-rate consequence*, even though V10 proves
it is not numerically interchangeable with the actual OpenAI envelope.

This proves a SCALAR CONDITIONAL result, not original manuscript (10.19),
not any physical Navier-Stokes flux inequality, and not PDE uniqueness.
The sourceEnvelope formula is the pinned V10 primary-source candidate;
it still requires independent NL specification endorsement.

The key is R^{-1}(B+1)(B^{1/2}+R^{-3/4}B^{3/4}), which is uniformly
controlled by R^{-1}(A+1)^{7/4} under the one-way Sobolev observation
B <= S(A+M/R), and 7/4 < 2 enables Young absorption.

This is ROS requirement-relative observational sufficiency:
different intermediate upper bounds can support the same protected future.
-/

noncomputable section

namespace MathGraph.SourcePressureFuture

open MathGraph.PressureEnvelopeObstruction
open scoped Topology

/-- The exact primary-source scalar envelope has only subquadratic
growth (7/4) in B, uniformly for radii R >= 1. -/
theorem source_envelope_le_shifted {R B : ℝ}
    (hR : 1 ≤ R) (hB : 0 ≤ B) :
    sourceEnvelope R B ≤ (2 / R) * (B + 1) ^ (7 / 4 : ℝ) := by
  have hRpos : 0 < R := lt_of_lt_of_le zero_lt_one hR
  have hRpow : R ^ (-(3 / 4 : ℝ)) ≤ 1 :=
    Real.rpow_le_one_of_one_le_of_nonpos hR (by norm_num)
  have hB1 : B ≤ B + 1 := by linarith
  have hX : 1 ≤ B + 1 := by linarith
  have hXpos : 0 < B + 1 := by linarith
  have hhalf : B ^ (1 / 2 : ℝ) ≤ (B + 1) ^ (3 / 4 : ℝ) :=
    (Real.rpow_le_rpow hB hB1 (by norm_num)).trans
      (Real.rpow_le_rpow_of_exponent_le hX (by norm_num))
  have hthree : B ^ (3 / 4 : ℝ) ≤ (B + 1) ^ (3 / 4 : ℝ) :=
    Real.rpow_le_rpow hB hB1 (by norm_num)
  have hterm : R ^ (-(3 / 4 : ℝ)) * B ^ (3 / 4 : ℝ) ≤
      B ^ (3 / 4 : ℝ) :=
    mul_le_of_le_one_left (Real.rpow_nonneg hB _) hRpow
  have hsum : B ^ (1 / 2 : ℝ) +
      R ^ (-(3 / 4 : ℝ)) * B ^ (3 / 4 : ℝ) ≤
      2 * (B + 1) ^ (3 / 4 : ℝ) := by
    linarith
  have hcoef : 0 ≤ (B + 1) / R := div_nonneg (by linarith) hRpos.le
  have hpower : (B + 1) * (B + 1) ^ (3 / 4 : ℝ) =
      (B + 1) ^ (7 / 4 : ℝ) := by
    calc
      _ = (B + 1) ^ (1 : ℝ) * (B + 1) ^ (3 / 4 : ℝ) := by rw [Real.rpow_one]
      _ = (B + 1) ^ ((1 : ℝ) + 3 / 4) := by rw [Real.rpow_add hXpos]
      _ = (B + 1) ^ (7 / 4 : ℝ) := by norm_num
  unfold sourceEnvelope
  calc
    _ ≤ ((B + 1) / R) * (2 * (B + 1) ^ (3 / 4 : ℝ)) :=
      mul_le_mul_of_nonneg_left hsum hcoef
    _ = (2 / R) * ((B + 1) * (B + 1) ^ (3 / 4 : ℝ)) := by ring
    _ = _ := by rw [hpower]

/-- The sole one-way Sobolev relation suffices to control source growth.
No reverse Sobolev bound is introduced. -/
theorem source_envelope_le_gradient_shift {R A B S M : ℝ}
    (hR : 1 ≤ R) (hA : 0 ≤ A) (hB : 0 ≤ B)
    (hS : 0 ≤ S) (hM : 0 ≤ M)
    (hSob : B ≤ S * (A + M / R)) :
    sourceEnvelope R B ≤
      (2 * (1 + S * (1 + M)) ^ (7 / 4 : ℝ)) / R *
        (A + 1) ^ (7 / 4 : ℝ) := by
  let Q : ℝ := 1 + S * (1 + M)
  have hRpos : 0 < R := lt_of_lt_of_le zero_lt_one hR
  have hQ : 0 ≤ Q := by dsimp [Q]; positivity
  have hA1 : 0 ≤ A + 1 := by linarith
  have hMdiv : M / R ≤ M := div_le_self hM hR
  have hBinner : B ≤ S * (A + M) := by
    apply hSob.trans
    exact mul_le_mul_of_nonneg_left (add_le_add_left hMdiv A) hS
  have hq : B + 1 ≤ Q * (A + 1) := by
    apply (add_le_add_right hBinner 1).trans
    dsimp [Q]
    nlinarith [mul_nonneg (mul_nonneg hS hM) hA]
  have hpow : (B + 1) ^ (7 / 4 : ℝ) ≤ Q ^ (7 / 4 : ℝ) *
      (A + 1) ^ (7 / 4 : ℝ) := by
    have h := Real.rpow_le_rpow (by linarith : 0 ≤ B + 1) hq (by norm_num)
    rw [Real.mul_rpow hQ hA1] at h
    exact h
  have hscaled := mul_le_mul_of_nonneg_left hpow
    (show 0 ≤ 2 / R by positivity)
  calc
    sourceEnvelope R B ≤ (2 / R) * (B + 1) ^ (7 / 4 : ℝ) :=
      source_envelope_le_shifted hR hB
    _ ≤ (2 / R) * (Q ^ (7 / 4 : ℝ) * (A + 1) ^ (7 / 4 : ℝ)) :=
      hscaled
    _ = (2 * (1 + S * (1 + M)) ^ (7 / 4 : ℝ)) / R *
        (A + 1) ^ (7 / 4 : ℝ) := by dsimp [Q]; ring

/-- Assuming (not asserting!) the source pressure-envelope bound,
its entire contribution is absorbable into any positive fraction δ of
the localized gradient square, uniformly for R>=1. -/
theorem exists_source_pressure_envelope_absorption
    {C S M δ : ℝ} (hC : 0 ≤ C) (hS : 0 ≤ S) (hM : 0 ≤ M)
    (hδ : 0 < δ) :
    ∃ D ≥ 0, ∀ R ≥ 1, ∀ A ≥ 0, ∀ B ≥ 0,
      B ≤ S * (A + M / R) →
      C * sourceEnvelope R B ≤ δ * A ^ 2 + D / R := by
  let K : ℝ := 2 * C * (1 + S * (1 + M)) ^ (7 / 4 : ℝ)
  have hK : 0 ≤ K := by dsimp [K]; positivity
  obtain ⟨D, hD, habs⟩ :=
    NavierStokesR3.ComparisonYoung.exists_scaled_shifted_rpow_absorption
      (C := K) (δ := δ) (p := 7 / 4) hK hδ (by norm_num) (by norm_num)
  refine ⟨D, hD, ?_⟩
  intro R hR A hA B hB hSob
  have hmain := source_envelope_le_gradient_shift
    hR hA hB hS hM hSob
  have hmult := mul_le_mul_of_nonneg_left hmain hC
  have hidentity :
      C * ((2 * (1 + S * (1 + M)) ^ (7 / 4 : ℝ)) / R *
        (A + 1) ^ (7 / 4 : ℝ)) =
      K / R * (A + 1) ^ (7 / 4 : ℝ) := by
    dsimp [K]
    ring
  exact (hmult.trans_eq hidentity).trans (habs A hA R hR)

/-- The manuscript-style envelope, *if assumed*, protects the same
scalar energy-rate conclusion as the formally proved OpenAI envelope.
It does NOT show the two intermediate envelopes are numerically equal. -/
theorem exists_source_pressure_energy_rate
    {C₀ C₁ C₂ S M : ℝ}
    (hC₀ : 0 ≤ C₀) (hC₁ : 0 ≤ C₁) (hC₂ : 0 ≤ C₂)
    (hS : 0 ≤ S) (hM : 0 ≤ M) :
    ∃ D ≥ 0, ∀ R ≥ 1, ∀ A ≥ 0, ∀ B ≥ 0,
      B ≤ S * (A + M / R) →
      ∀ E E' G : ℝ,
        (1 / 2 : ℝ) * E' + A ^ 2 ≤ G * E +
          C₀ / R ^ 2 + C₁ / R * B ^ (3 / 2 : ℝ) +
          C₂ * sourceEnvelope R B →
        E' ≤ 2 * G * E + D / R := by
  obtain ⟨D₁, hD₁, habs₁⟩ :=
    NavierStokes.R3EnergyAbsorption.absorb_sobolev_errors
      (c := C₁) (S := S) (d := M) (ε := 1 / 4)
      hC₁ hS hM (by norm_num)
  obtain ⟨D₂, hD₂, habs₂⟩ :=
    exists_source_pressure_envelope_absorption hC₂ hS hM
      (by norm_num : (0 : ℝ) < 1 / 4)
  refine ⟨2 * (C₀ + D₁ + D₂), by positivity, ?_⟩
  intro R hR A hA B hB hSob E E' G henergy
  have hRpos : 0 < R := lt_of_lt_of_le zero_lt_one hR
  have hR2 : R ≤ R ^ 2 := by nlinarith [sq_nonneg (R - 1)]
  have hC₀small : C₀ / R ^ 2 ≤ C₀ / R :=
    div_le_div_of_nonneg_left hC₀ hRpos hR2
  have hterms : C₁ / R * B ^ (3 / 2 : ℝ) ≤
      C₁ / R * (B ^ (3 / 2 : ℝ) + B + A + 1) := by
    apply mul_le_mul_of_nonneg_left _ (div_nonneg hC₁ hRpos.le)
    linarith
  have hfirst := hterms.trans (habs₁ R hR A hA B hB hSob)
  have hsecond := habs₂ R hR A hA B hB hSob
  have hDrewrite :
      2 * (C₀ + D₁ + D₂) / R =
      2 * (C₀ / R + D₁ / R + D₂ / R) := by ring
  rw [hDrewrite]
  nlinarith only [henergy, hC₀small, hfirst, hsecond, sq_nonneg A]

end MathGraph.SourcePressureFuture

#print axioms MathGraph.SourcePressureFuture.source_envelope_le_shifted
#print axioms MathGraph.SourcePressureFuture.source_envelope_le_gradient_shift
#print axioms MathGraph.SourcePressureFuture.exists_source_pressure_envelope_absorption
#print axioms MathGraph.SourcePressureFuture.exists_source_pressure_energy_rate
