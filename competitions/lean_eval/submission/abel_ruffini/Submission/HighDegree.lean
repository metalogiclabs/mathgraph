import Mathlib
import Archive.Wiedijk100Theorems.AbelRuffini

open Polynomial

theorem high_degree_obstruction (n : ℕ) (hn : 5 ≤ n) :
    ¬ (∀ p : ℚ[X], p.natDegree = n → ∀ x : ℂ,
        aeval x p = 0 → x ∈ solvableByRad ℚ ℂ) := by
  intro hall
  let bad : ℚ[X] := AbelRuffini.Φ ℚ 4 2
  obtain ⟨y, hy⟩ :=
    (IsAlgClosed.splits (bad.map (algebraMap ℚ ℂ))).exists_eval_eq_zero (by
      simp [bad, AbelRuffini.degree_Phi])
  have hyroot : aeval y bad = 0 := by simpa [aeval_def] using hy
  have hynot : y ∉ solvableByRad ℚ ℂ := by
    apply AbelRuffini.not_solvable_by_rad' y
    simpa [bad, aeval_def] using hyroot
  let p : ℚ[X] := bad * X ^ (n - 5)
  have hbad0 : bad ≠ 0 := (AbelRuffini.monic_Phi 4 2).ne_zero
  have hdeg : p.natDegree = n := by
    rw [show p = bad * X ^ (n - 5) by rfl,
      natDegree_mul hbad0 (pow_ne_zero _ X_ne_zero)]
    simp [bad, AbelRuffini.natDegree_Phi]
    omega
  have hroot : aeval y p = 0 := by simp [p, hyroot]
  exact hynot (hall p hdeg y hroot)
