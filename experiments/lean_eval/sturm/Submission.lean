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
three-term Sturm configuration quotients to its two neighbours. -/
theorem signChanges_middle_zero (a c : ℝ) :
    signChanges [a, 0, c] = signChanges [a, c] := by
  by_cases ha : a = 0 <;> by_cases hc : c = 0 <;> simp [signChanges, ha, hc]

/-- Finite sign law for the interior-zero Sturm configuration. Once the
neighbours are known to be opposites, their local contribution is exactly one. -/
theorem signChanges_opposite_neighbours (a : ℝ) (ha : a ≠ 0) :
    signChanges [a, 0, -a] = 1 := by
  have hpos : 0 < a * a := mul_self_pos.mpr ha
  have hneg : a * (-a) < 0 := by
    nlinarith
  simp [signChanges, ha, hneg]

/-- Context-composition separator: inserting a zero anywhere in a list does
not change sign variation. This lifts the zero quotient through arbitrary
Sturm-chain context without introducing a new sign state. -/
theorem signChanges_insert_zero (xs ys : List ℝ) :
    signChanges (xs ++ 0 :: ys) = signChanges (xs ++ ys) := by
  have hfilter :
      (xs ++ 0 :: ys).filter (· ≠ 0) = (xs ++ ys).filter (· ≠ 0) := by
    simp [List.filter_append]
  simp only [signChanges]
  rw [hfilter]
