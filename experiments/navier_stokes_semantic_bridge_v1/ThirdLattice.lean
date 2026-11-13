import NavierStokes.SmoothFourierData

/-!
Independent source-pinned proof attempt for the exact residual from V5:
  sum_{(m,n) : Z²} (1 + |m| + |n|)^(-3) < infinity.

This is the cheapest consequence of the primary source's four derivative
loss: existing Fourier moment estimate costs three derivatives here and
TorusInverse itself loses one derivative.

No new axiom, arbitrary admitted fact, source-language authority, PDE
correctness or theorem-statement equivalence is asserted.
-/

noncomputable section

namespace MathGraph.ThirdLattice

open NavierStokes.TorusInverse

theorem summable_integer_weight_inv_three_halves :
    Summable (fun n : ℤ => ((1 + |(n : ℝ)|) ^ (3 / 2 : ℝ))⁻¹) := by
  have hbase : Summable (fun n : ℕ => 1 / (n : ℝ) ^ (3 / 2 : ℝ)) :=
    Real.summable_one_div_nat_rpow.mpr (by norm_num)
  have hNat : Summable (fun n : ℕ => 1 / ((n : ℝ) + 1) ^ (3 / 2 : ℝ)) := by
    have h : Summable (fun n : ℕ =>
        1 / ((n + 1 : ℕ) : ℝ) ^ (3 / 2 : ℝ)) :=
      (summable_nat_add_iff 1).mpr hbase
    simpa only [Nat.cast_add, Nat.cast_one] using h
  apply Summable.of_nat_of_neg
  · simpa only [Int.cast_natCast, Nat.abs_cast, add_comm, one_div] using hNat
  · simpa only [Int.cast_neg, Int.cast_natCast, abs_neg, Nat.abs_cast,
      add_comm, one_div] using hNat

theorem weight_inv_three_le_product (k : Frequency) :
    (weight k ^ 3)⁻¹ ≤
      ((1 + |(k.1 : ℝ)|) ^ (3 / 2 : ℝ))⁻¹ *
      ((1 + |(k.2 : ℝ)|) ^ (3 / 2 : ℝ))⁻¹ := by
  let a : ℝ := 1 + |(k.1 : ℝ)|
  let b : ℝ := 1 + |(k.2 : ℝ)|
  have ha : 0 < a := by dsimp [a]; positivity
  have hb : 0 < b := by dsimp [b]; positivity
  have hwa : a ≤ weight k := by
    dsimp [a, weight]
    linarith [abs_nonneg (k.2 : ℝ)]
  have hwb : b ≤ weight k := by
    dsimp [b, weight]
    linarith [abs_nonneg (k.1 : ℝ)]
  have hpa : a ^ (3 / 2 : ℝ) ≤ (weight k) ^ (3 / 2 : ℝ) :=
    Real.rpow_le_rpow ha.le hwa (by norm_num)
  have hpb : b ^ (3 / 2 : ℝ) ≤ (weight k) ^ (3 / 2 : ℝ) :=
    Real.rpow_le_rpow hb.le hwb (by norm_num)
  have hpow : a ^ (3 / 2 : ℝ) * b ^ (3 / 2 : ℝ) ≤ (weight k) ^ 3 := by
    calc
      a ^ (3 / 2 : ℝ) * b ^ (3 / 2 : ℝ) ≤
          (weight k) ^ (3 / 2 : ℝ) * (weight k) ^ (3 / 2 : ℝ) :=
        mul_le_mul hpa hpb (Real.rpow_nonneg hb.le _) (Real.rpow_nonneg (weight_pos k).le _)
      _ = (weight k) ^ ((3 / 2 : ℝ) + (3 / 2 : ℝ)) := by
        rw [Real.rpow_add (weight_pos k)]
      _ = (weight k) ^ 3 := by
        norm_num [Real.rpow_natCast]
  have h := one_div_le_one_div_of_le (by positivity :
    0 < a ^ (3 / 2 : ℝ) * b ^ (3 / 2 : ℝ)) hpow
  simpa only [a, b, one_div, mul_inv_rev, mul_comm] using h

/-- Exact Z² frequency lattice lemma, with exponent 3 (> dimension 2). -/
theorem summable_weight_inv_three :
    Summable (fun k : Frequency => (weight k ^ 3)⁻¹) := by
  have hprod :=
    summable_integer_weight_inv_three_halves.mul_of_nonneg
      summable_integer_weight_inv_three_halves
      (fun n => by positivity) (fun n => by positivity)
  exact Summable.of_nonneg_of_le
    (fun k => inv_nonneg.mpr (pow_nonneg (weight_pos k).le _))
    weight_inv_three_le_product hprod

end MathGraph.ThirdLattice

#print axioms MathGraph.ThirdLattice.summable_integer_weight_inv_three_halves
#print axioms MathGraph.ThirdLattice.weight_inv_three_le_product
#print axioms MathGraph.ThirdLattice.summable_weight_inv_three
