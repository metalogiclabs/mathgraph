import Mathlib
import Submission.LowDegree
import Submission.CubicUniversal
import Submission.QuarticUniversal
import Submission.HighDegree

open Polynomial

namespace Submission

theorem abel_ruffini (n : ℕ) (_hn : 1 ≤ n) :
    (∀ p : ℚ[X], p.natDegree = n → ∀ x : ℂ, aeval x p = 0 →
        x ∈ solvableByRad ℚ ℂ) ↔ n ≤ 4 := by
  constructor
  · intro hall
    by_contra hn4
    have hn5 : 5 ≤ n := by omega
    exact high_degree_obstruction n hn5 hall
  · intro hn4 p hp x hx
    have hn1 : 1 ≤ n := _hn
    rcases (by omega : n = 1 ∨ n = 2 ∨ n = 3 ∨ n = 4) with h1 | h2 | h3 | h4
    · subst n
      exact degree_one_solvable p hp x hx
    · subst n
      exact degree_two_solvable p hp x hx
    · subst n
      exact degree_three_solvable p hp x hx
    · subst n
      exact degree_four_solvable p hp x hx

end Submission
