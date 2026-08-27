import ChallengeDeps

open LeanEval.Algebra
open Polynomial
open scoped Classical

/-- Local Sturm invariant: at a zero of the middle polynomial, the next
negated remainder evaluates to the negative of the preceding polynomial. -/
theorem sturm_remainder_eval_at_root (a b : ℝ[X]) (x : ℝ)
    (hb : b.eval x = 0) :
    (-(a % b)).eval x = -a.eval x := by
  have h := congrArg (fun q : ℝ[X] => q.eval x) (EuclideanDomain.mod_add_div a b)
  have hrem : (a % b).eval x = a.eval x := by
    simpa [hb] using h
  simp [hrem]

/-- VDN separator probe: zeros carry no sign information, so the local
three-term Sturm configuration quotients to its two nonzero neighbours. -/
theorem signChanges_middle_zero (a c : ℝ) :
    signChanges [a, 0, c] = signChanges [a, c] := by
  simp [signChanges]

/-- Finite sign law for the interior-zero Sturm configuration.  Once the
neighbours are known to be opposites, their local contribution is exactly one. -/
theorem signChanges_opposite_neighbours (a : ℝ) (ha : a ≠ 0) :
    signChanges [a, 0, -a] = 1 := by
  simp [signChanges, ha]
  exact mul_neg_self_lt_zero ha
