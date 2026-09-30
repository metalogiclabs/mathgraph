import Mathlib

namespace CrystalCrossProverHeldout2ConstructorReuse

/-- Existing constructor class: explicit_witness. -/
theorem ex_quad_consumer :
    ∃ x : ℝ, ∀ y : ℝ, y ^ 2 + x * y + 1 > 0 := by
  refine ⟨0, ?_⟩
  intro y
  nlinarith [sq_nonneg y]

/-- Existing constructor class: quadratic_implication. -/
theorem ex_disc2_consumer (x y : ℝ) :
    x ^ 2 + y ^ 2 ≤ 1 → x + y ≤ 2 := by
  intro h
  nlinarith [sq_nonneg (x - 1), sq_nonneg (y - 1)]

/-- Existing constructor class: sum_of_squares. -/
theorem ex_quartic_consumer (x y : ℝ) :
    x ^ 4 + y ^ 4 + 1 > x * y := by
  nlinarith [
    sq_nonneg (x ^ 2 - y ^ 2),
    sq_nonneg (x * y - (1 / 4 : ℝ))
  ]

/-- Existing constructor class: explicit_witness. -/
theorem ex_ell_consumer (x : ℝ) :
    ∃ y : ℝ, x ^ 2 + x * y + y ^ 2 ≥ 3 ∧ y > x := by
  refine ⟨x + 4, ?_, by linarith⟩
  nlinarith [sq_nonneg (x + 2)]

/-- Existing constructor class: algebraic_root_witness. -/
theorem ex_two_consumer (x : ℝ) :
    ∃ y : ℝ, y ^ 2 = x ^ 2 + 1 ∧ y > 0 ∧ y ^ 2 - x ^ 2 ≤ 1 := by
  have hrad : 0 < x ^ 2 + 1 := by
    nlinarith [sq_nonneg x]
  refine ⟨Real.sqrt (x ^ 2 + 1), ?_, ?_, ?_⟩
  · exact Real.sq_sqrt hrad.le
  · exact Real.sqrt_pos.2 hrad
  · rw [Real.sq_sqrt hrad.le]
    linarith

end CrystalCrossProverHeldout2ConstructorReuse
