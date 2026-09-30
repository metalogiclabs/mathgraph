import Mathlib

namespace CrystalCrossProverHeldout5SgnSelector

/-- Frozen selector chose explicit_witness before sgn_examples was opened. -/
theorem sgn_g1_consumer :
    ∃ x : ℝ, x ^ 2 - 1 = 0 ∧ x > 0 := by
  exact ⟨1, by norm_num, by norm_num⟩

/-- Frozen selector chose quantifier_witness_duality before sgn_examples was opened. -/
theorem sgn_g2_consumer :
    ¬ (∃ x : ℝ, x ^ 2 + 1 = 0 ∧ x > 0) := by
  rintro ⟨x, hx, _hpos⟩
  nlinarith [sq_nonneg x]

end CrystalCrossProverHeldout5SgnSelector
