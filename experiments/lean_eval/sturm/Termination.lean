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

/-- A nonzero constant divisor makes the next Euclidean remainder zero. -/
theorem sturm_remainder_zero_of_natDegree_eq_zero
    (a b : ℝ[X]) (hb : b ≠ 0) (hdeg : b.natDegree = 0) :
    -(a % b) = 0 := by
  have hbC : C (b.coeff 0) = b := (eq_C_of_natDegree_eq_zero hdeg).symm
  have hbc : b.coeff 0 ≠ 0 := by
    intro hc
    apply hb
    rw [← hbC, hc]
    simp
  rw [← hbC]
  simp [hbc]

/-- Degree is invariant under negation. -/
theorem natDegree_neg_eq (p : ℝ[X]) : (-p).natDegree = p.natDegree := by
  simp

/-- Pure Euclidean termination bound.  If the current divisor has degree
strictly below the available fuel, the negated-remainder Sturm recursion
must encounter polynomial zero before fuel is exhausted. -/
theorem sturmComplete_of_natDegree_lt
    (a b : ℝ[X]) (n : ℕ) (hdeg : b.natDegree < n) :
    SturmComplete a b n := by
  induction n using Nat.strong_induction_on generalizing a b with
  | h n ih =>
      cases n with
      | zero => omega
      | succ n =>
          by_cases hb : b = 0
          · simp [SturmComplete, hb]
          · simp only [SturmComplete, hb, if_false]
            by_cases hbdeg : b.natDegree = 0
            · have hzero := sturm_remainder_zero_of_natDegree_eq_zero a b hb hbdeg
              rw [hzero]
              cases n with
              | zero => simp [SturmComplete]
              | succ n => simp [SturmComplete]
            · have hrem : (a % b).natDegree < b.natDegree :=
                Polynomial.natDegree_mod_lt a hbdeg
              have hnext : (-(a % b)).natDegree < n := by
                rw [natDegree_neg_eq]
                omega
              exact ih n (Nat.lt_succ_self n) b (-(a % b)) hnext

/-- The benchmark's fuel budget is more than enough for the actual Sturm
chain.  This is a purely algebraic fact and does not require squarefreeness. -/
theorem sturmChain_complete (p : ℝ[X]) :
    SturmComplete p p.derivative (p.natDegree + 2) := by
  apply sturmComplete_of_natDegree_lt
  have hderiv : p.derivative.natDegree ≤ p.natDegree := by
    exact (natDegree_derivative_le p).trans (Nat.sub_le _ _)
  omega

/-- Consequently a squarefree Sturm chain has the exact terminal-safe
regularity interface needed by the generic local-variation theorem. -/
theorem squarefree_sturmChain_regular (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) :
    SturmRegularAt r p p.derivative (p.natDegree + 2) := by
  exact sturmRegularAt_of_no_common_zero_of_complete
    p p.derivative r (p.natDegree + 2)
    (squarefree_sturm_start_no_common_root p r hp)
    (sturmChain_complete p)
