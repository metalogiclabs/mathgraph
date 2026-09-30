import Mathlib

namespace CrystalCrossProverTarskiSemanticBoundary

/-- Existing constructor class: explicit_witness. -/
theorem tarski_e6_consumer :
    ∃ x : ℝ, x ^ 2 - 1 = 0 ∧ x > 0 := by
  exact ⟨1, by norm_num, by norm_num⟩

/-- Existing constructor class: quantifier_witness_duality. -/
theorem tarski_e8_consumer :
    ¬ (∃ x : ℝ, x ^ 2 - 1 = 0 ∧ -x ^ 2 > 0) := by
  rintro ⟨x, _hroot, hneg⟩
  nlinarith [sq_nonneg x]

end CrystalCrossProverTarskiSemanticBoundary
