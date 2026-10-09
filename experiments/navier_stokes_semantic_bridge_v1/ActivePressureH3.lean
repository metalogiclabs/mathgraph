import NavierStokes.R3.PressureTestBounds
import NavierStokes.R3.PressureFunctionals

/-!
V21: the exact *active* NavierStokesR3.Comparison.pressurePair functional is
Fourier H³-bounded for any real integrable stress g.

This discharges ONE of the two concrete quantitative premises of V20's
all-Schwartz-test pressure uniqueness gate, using already proved original
OpenAI pressure-test estimates, not a new assumed constant. The old
R3PressureFourier.pressureL1 functional's own quantitative bound remains
unproved in this file, as does the cross-interface Laplacian bridge V19.

The central bound uses an integrable inverse-square frequency weight in
three dimensions, Cauchy-Schwarz, and source's genuine Fourier Riesz test
symbol bound. No general PDE regularity, (10.19), or NL fidelity asserted.
-/

noncomputable section
namespace MathGraph.ActivePressureH3

open MeasureTheory Filter Set
open NavierStokes.ProblemStatement
open NavierStokesR3.Comparison
open NavierStokesR3.HarmonicTestFunctionals
open NavierStokesR3.RieszTestOperators
open NavierStokesR3.PressureTestBounds
open NavierStokesR3.PressureFunctionals
open scoped ENNReal Topology FourierTransform

/-- Compared to the derivative-weighted first-moment estimate in the
original source, the zeroth Fourier moment costs strictly fewer spatial
moments. It is bounded by the same finite source constant. -/
theorem integral_fourier_norm_le_H3 (ψ : ComplexTest) :
    (∫ ξ : Space, ‖(FourierTransform.fourierCLE ℂ ComplexTest ψ) ξ‖) ≤
      fourierMomentConstant * Real.sqrt (fourierHNormSq 3 ψ) := by
  let f : Space → ℂ := fun ξ => (FourierTransform.fourierCLE ℂ ComplexTest ψ) ξ
  have hf : AEStronglyMeasurable f volume :=
    (FourierTransform.fourierCLE ℂ ComplexTest ψ).continuous.aestronglyMeasurable
  have hw : Integrable (fun ξ : Space =>
      (1 + ‖ξ‖ ^ 2) ^ 3 * ‖f ξ‖ ^ 2) volume :=
    NavierStokesR3.FourierSobolevWeights.integrable_fourierHNormSq_three ψ
  let a : Space → ℝ := fun ξ => (1 + ‖ξ‖ ^ 2)⁻¹
  let b : Space → ℝ := fun ξ => (1 + ‖ξ‖ ^ 2) * ‖f ξ‖
  have ha : AEStronglyMeasurable a volume := by
    exact ((continuous_const.add (continuous_norm.pow 2)).inv₀
      (fun ξ : Space => ne_of_gt
        (by positivity : (0 : ℝ) < 1 + ‖ξ‖ ^ 2))).aestronglyMeasurable
  have hb : AEStronglyMeasurable b volume := by
    exact (by fun_prop : Continuous (fun ξ : Space => (1 + ‖ξ‖ ^ 2))).aestronglyMeasurable.mul hf.norm
  have hb_le (ξ : Space) :
      b ξ ^ 2 ≤ (1 + ‖ξ‖ ^ 2) ^ 3 * ‖f ξ‖ ^ 2 := by
    dsimp [b]
    calc
      ((1 + ‖ξ‖ ^ 2) * ‖f ξ‖) ^ 2 =
          (1 + ‖ξ‖ ^ 2) ^ 2 * ‖f ξ‖ ^ 2 := by ring
      _ ≤ (1 + ‖ξ‖ ^ 2) ^ 3 * ‖f ξ‖ ^ 2 := by
        apply mul_le_mul_of_nonneg_right
          (pow_le_pow_right₀ (le_add_of_nonneg_right (sq_nonneg ‖ξ‖))
            (by decide))
          (sq_nonneg _)
  have hb_int : Integrable (fun ξ => b ξ ^ 2) volume :=
    hw.mono' (hb.pow 2) (Filter.Eventually.of_forall fun ξ => by
      rw [Real.norm_of_nonneg (sq_nonneg _)]
      exact hb_le ξ)
  have ha_lp : MemLp a 2 volume :=
    (memLp_two_iff_integrable_sq ha).mpr integrable_inverse_weight_sq
  have hb_lp : MemLp b 2 volume := (memLp_two_iff_integrable_sq hb).mpr hb_int
  have hcs := integral_mul_le_Lp_mul_Lq_of_nonneg
    (μ := (volume : Measure Space)) (f := a) (g := b)
    Real.HolderConjugate.two_two
    (Filter.Eventually.of_forall (fun ξ => by dsimp [a]; positivity))
    (Filter.Eventually.of_forall (fun ξ => by dsimp [b]; positivity))
    (by simpa using ha_lp) (by simpa using hb_lp)
  simp only [Real.rpow_two, ← Real.sqrt_eq_rpow] at hcs
  have hprod : (fun ξ : Space => a ξ * b ξ) =
      fun ξ : Space => ‖f ξ‖ := by
    funext ξ
    dsimp [a, b]
    have hq : (1 + ‖ξ‖ ^ 2 : ℝ) ≠ 0 := by positivity
    simp [← mul_assoc, hq]
  rw [hprod] at hcs
  exact hcs.trans (mul_le_mul_of_nonneg_left
    (Real.sqrt_le_sqrt (integral_mono hb_int hw hb_le))
    fourierMomentConstant_nonneg)

/-- The exact physical-comparison Riesz pressure pairing for an arbitrary
integrable real stress has a uniform (in the Schwartz test) Fourier H³
bound, with explicit nonnegative coefficient ∫|g| · source constant. -/
theorem active_pressurePair_H3_bound
    {g : Space → ℝ} (hg : Integrable g volume) (i j : Fin 3)
    (ψ : ComplexTest) :
    ‖pressurePair i j g ψ‖ ≤
      ((∫ x : Space, ‖g x‖) * fourierMomentConstant) *
        Real.sqrt (fourierHNormSq 3 ψ) := by
  have hBound (x : Space) : ‖rieszTest i j ψ x‖ ≤
      fourierMomentConstant * Real.sqrt (fourierHNormSq 3 ψ) :=
    (norm_rieszTest_le_integral i j ψ x).trans (integral_fourier_norm_le_H3 ψ)
  have hi :=
    norm_l1_pair_le_of_bound hg (integrable_l1_riesz_pair hg i j ψ) hBound
  simpa only [pressurePair, mul_assoc] using hi

/-- Hence the genuine active comparison pressure functional supplies
one of V20's quantitative premises with NO free H³ bound hypothesis. -/
theorem active_pressurePairLinear_has_H3_certificate
    (g : Space → ℝ) (hg : Integrable g volume) (i j : Fin 3) :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ ψ : ComplexTest,
      ‖pressurePairLinear i j g hg ψ‖ ≤
        C * Real.sqrt (fourierHNormSq 3 ψ) := by
  refine ⟨(∫ x : Space, ‖g x‖) * fourierMomentConstant,
    mul_nonneg (integral_nonneg fun _ => norm_nonneg _) fourierMomentConstant_nonneg,
    ?_⟩
  intro ψ
  simpa only [pressurePairLinear_apply] using active_pressurePair_H3_bound hg i j ψ

end MathGraph.ActivePressureH3

#print axioms MathGraph.ActivePressureH3.integral_fourier_norm_le_H3
#print axioms MathGraph.ActivePressureH3.active_pressurePair_H3_bound
#print axioms MathGraph.ActivePressureH3.active_pressurePairLinear_has_H3_certificate
