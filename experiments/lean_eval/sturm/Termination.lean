import ChallengeDeps
import TailComposition
import SigmaLocal

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- Structural completion certificate: if fuel reaches zero, the next
polynomial has already become zero. -/
noncomputable def SturmComplete : ℝ[X] → ℝ[X] → ℕ → Prop
  | _, b, 0 => b = 0
  | a, b, n + 1 =>
      if b = 0 then True else SturmComplete b (-(a % b)) n

/-- Completion plus the pointwise no-common-zero invariant is exactly the
missing boundary information needed by `SturmRegularAt`. -/
theorem sturmRegularAt_of_no_common_zero_of_complete
    (a b : ℝ[X]) (r : ℝ) (n : ℕ)
    (hab : ¬ (a.eval r = 0 ∧ b.eval r = 0))
    (hcomplete : SturmComplete a b n) :
    SturmRegularAt r a b n := by
  induction n generalizing a b with
  | zero =>
      simp only [SturmComplete] at hcomplete
      simp only [SturmRegularAt]
      intro ha
      apply hab
      constructor
      · exact ha
      · simp [hcomplete]
  | succ n ih =>
      by_cases hbpoly : b = 0
      · simp [SturmRegularAt, hbpoly]
        intro ha
        exact hab ⟨ha, by simp [hbpoly]⟩
      · simp only [SturmComplete, hbpoly, if_false] at hcomplete
        simp only [SturmRegularAt, hbpoly, if_false]
        refine ⟨hab, ?_⟩
        exact ih b (-(a % b))
          (sturm_step_no_common_zero a b r hab) hcomplete
