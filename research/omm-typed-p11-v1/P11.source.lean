/-
Mathathon Round 1, Problem 11: official Lean statement, prepared by AI. It may contain errors.

Source (Lech Mazur, ProofAtlas, Apache License 2.0):
  https://www.proofatlas.ai/sources/positive-density-log-time-collatz/commits/830b9d3f38f2a8da8cd921bf6a9310dd69336fd0/CollatzPositiveDensity.lean
Adapted: the definitions `step`, `fastConvergent` and `countBelow` are copied unchanged. In the
source, the theorem `positive_density` uses the explicit constants `densityConstant` and `cutoff`,
which are defined deep inside the proof development. Here they are replaced by `∃ c > 0, ∃ X₀`.
So the statement is Theorem 1.1 of L. Mazur, "Explicit positive-density Collatz convergence in
logarithmic time" (2026), without the explicit values of c and X₀: the positive integers that reach
1 within (523/50) log n Collatz steps have positive lower natural density. The source's import is
replaced by `import Mathlib`.
-/

import Mathlib

namespace CollatzPositiveDensity

def step (n : ℕ) : ℕ := if Even n then n / 2 else 3 * n + 1

def fastConvergent (C : ℝ) (n : ℕ) : Prop :=
  0 < n ∧ ∃ k : ℕ, (k : ℝ) ≤ C * Real.log (n : ℝ) ∧ step^[k] n = 1

noncomputable def countBelow (C : ℝ) (X : ℕ) : ℕ := by
  classical
  exact Nat.count (fastConvergent C) X

/-- **Mazur's theorem** (2026). There are `c > 0` and `X₀` such that for every `X ≥ X₀`, at least
`c * X` of the integers `1 ≤ n < X` reach `1` within `(523/50) * log n` steps of the Collatz map. -/
theorem exists_positive_density :
    ∃ c : ℝ, 0 < c ∧ ∃ X₀ : ℕ, ∀ X : ℕ, X₀ ≤ X →
      c * X ≤ (countBelow (523 / 50) X : ℝ) := by
  sorry

end CollatzPositiveDensity
