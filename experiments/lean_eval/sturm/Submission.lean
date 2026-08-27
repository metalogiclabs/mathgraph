import ChallengeDeps

open LeanEval.Algebra
open Polynomial
open scoped Classical

/-- First decisive probe for LeanEval `sturm`: push only the existing imported
surface and expose the residual after unfolding the public variation wrapper. -/
theorem sturm_probe (p : ℝ[X]) (hp : Squarefree p) {a b : ℝ} (hab : a < b)
    (ha : p.eval a ≠ 0) (hb : p.eval b ≠ 0) :
    ((p.roots.toFinset).filter (fun x => a < x ∧ x < b)).card =
      sigma p a - sigma p b := by
  classical
  simp only [sigma]
  aesop
