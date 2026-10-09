import NavierStokes.R3.HarmonicTestFunctionals

/-!
# V20: the minimal protected-future certificate for two pressure functionals

The source-pinned OpenAI harmonic uniqueness theorem explicitly needs:
* the two complex-linear Schwartz functionals' difference is bounded by
  a multiple of sqrt(fourierHNormSq 3 ψ) for EVERY Schwartz test ψ;
* the difference is zero on every actual harmonic-test Laplacian.

This file proves that those obligations suffice for equality ON ALL TESTS,
and that two separately H³-bounded functionals suffice for the difference
bound. No mathematical statement is changed or unproved assumption hidden.

V19 is independently testing the Poisson/Laplacian condition for old vs
comparison Riesz pressure. V20 does NOT discharge either individual H³
bound for the actual two concrete pressure operators. That is the remaining
named proof obligation; the original manuscript's B-only inequality
(10.19) and NL semantic approval remain UNKNOWN.
-/

noncomputable section

namespace MathGraph.PressureHarmonicCriterion

open MeasureTheory
open NavierStokesR3.Comparison
open NavierStokesR3.HarmonicTestFunctionals

/-- If the difference is H³-bounded and both functional observations of
the Laplacian agree, the actual OpenAI harmonic uniqueness result removes
the possible nonzero harmonic pressure ambiguity. -/
theorem all_tests_agree_of_protected_laplacian_and_bound
    (F G : ComplexTest →ₗ[ℂ] ℂ) {C : ℝ}
    (hC : 0 ≤ C)
    (hbound : ∀ ψ : ComplexTest,
      ‖F ψ - G ψ‖ ≤ C * Real.sqrt (fourierHNormSq 3 ψ))
    (hlap : ∀ ψ : ComplexTest,
      F (laplacianCLM ψ) = G (laplacianCLM ψ)) :
    F = G := by
  let H : ComplexTest →ₗ[ℂ] ℂ := F - G
  have hH : ∀ ψ : ComplexTest,
      ‖H ψ‖ ≤ C * Real.sqrt (fourierHNormSq 3 ψ) := by
    intro ψ
    simpa only [H, LinearMap.sub_apply] using hbound ψ
  have hL : ∀ ψ : ComplexTest, H (laplacianCLM ψ) = 0 := by
    intro ψ
    change F (laplacianCLM ψ) - G (laplacianCLM ψ) = 0
    exact sub_eq_zero.mpr (hlap ψ)
  have hz : H = 0 :=
    eq_zero_of_harmonic H hC hH hL
  exact sub_eq_zero.mp hz

/-- A pair of individually H³-bounded observations is enough to
supply the difference H³ bound, without additional Fourier analysis. -/
theorem all_tests_agree_of_individual_bounds
    (F G : ComplexTest →ₗ[ℂ] ℂ)
    {C₁ C₂ : ℝ} (hC₁ : 0 ≤ C₁) (hC₂ : 0 ≤ C₂)
    (hF : ∀ ψ : ComplexTest,
      ‖F ψ‖ ≤ C₁ * Real.sqrt (fourierHNormSq 3 ψ))
    (hG : ∀ ψ : ComplexTest,
      ‖G ψ‖ ≤ C₂ * Real.sqrt (fourierHNormSq 3 ψ))
    (hlap : ∀ ψ : ComplexTest,
      F (laplacianCLM ψ) = G (laplacianCLM ψ)) :
    F = G := by
  apply all_tests_agree_of_protected_laplacian_and_bound
    F G (add_nonneg hC₁ hC₂)
  · intro ψ
    calc
      ‖F ψ - G ψ‖ ≤ ‖F ψ‖ + ‖G ψ‖ := norm_sub_le _ _
      _ ≤ C₁ * Real.sqrt (fourierHNormSq 3 ψ) +
          C₂ * Real.sqrt (fourierHNormSq 3 ψ) := add_le_add (hF ψ) (hG ψ)
      _ = (C₁ + C₂) * Real.sqrt (fourierHNormSq 3 ψ) := by ring
  · exact hlap

end MathGraph.PressureHarmonicCriterion

#print axioms MathGraph.PressureHarmonicCriterion.all_tests_agree_of_protected_laplacian_and_bound
#print axioms MathGraph.PressureHarmonicCriterion.all_tests_agree_of_individual_bounds
