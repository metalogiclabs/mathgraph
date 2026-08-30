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
    rcases (by omega : n = 1 ∨ n = 2 ∨ n = 3 ∨ n = 4) with h1 | h2 | h3 | h4
    · have hp1 : p.natDegree = 1 := by simpa [h1] using hp
      exact degree_one_solvable p hp1 x hx
    · have hp2 : p.natDegree = 2 := by simpa [h2] using hp
      exact degree_two_solvable p hp2 x hx
    · have hp3 : p.natDegree = 3 := by simpa [h3] using hp
      exact degree_three_solvable p hp3 x hx
    · have hp4 : p.natDegree = 4 := by simpa [h4] using hp
      exact degree_four_solvable p hp4 x hx

end Submission
