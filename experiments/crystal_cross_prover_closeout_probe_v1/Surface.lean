import Mathlib

namespace CrystalCrossProverCloseoutProbe

open Set

theorem d_cubic_consumer (c : ℝ) : ∃ x : ℝ, x ^ 3 - 3 * x + c = 0 := by
  let M : ℝ := |c| + 2
  let f : ℝ → ℝ := fun x => x ^ 3 - 3 * x + c
  have hM2 : 2 ≤ M := by
    dsimp [M]
    have h := abs_nonneg c
    linarith
  have hM0 : 0 ≤ M := by linarith
  have hquad : 0 ≤ M ^ 2 - 4 := by
    nlinarith
  have hprod : 0 ≤ M * (M ^ 2 - 4) := mul_nonneg hM0 hquad
  have hgrowth : M ≤ M ^ 3 - 3 * M := by
    nlinarith [hprod]
  have hc_hi : c ≤ |c| := le_abs_self c
  have hc_lo : -|c| ≤ c := neg_abs_le c
  have hleft : f (-M) ≤ 0 := by
    dsimp [f]
    nlinarith [hgrowth, hc_hi]
  have hright : 0 ≤ f M := by
    dsimp [f]
    nlinarith [hgrowth, hc_lo]
  have hcont : Continuous f := by
    fun_prop
  obtain ⟨x, hxmem, hx0⟩ :=
    intermediate_value_Icc (by linarith : -M ≤ M) hcont.continuousOn
      (show (0 : ℝ) ∈ Icc (f (-M)) (f M) by exact ⟨hleft, hright⟩)
  refine ⟨x, ?_⟩
  simpa [f] using hx0

theorem d_meet_consumer :
    ∃ x : ℝ, ∃ y : ℝ, x ^ 2 + y ^ 2 = 1 ∧ y = x ^ 2 := by
  let y : ℝ := (Real.sqrt 5 - 1) / 2
  have hs5 : (Real.sqrt 5) ^ 2 = 5 := Real.sq_sqrt (by norm_num)
  have hs5_nonneg : 0 ≤ Real.sqrt 5 := Real.sqrt_nonneg 5
  have hs5_ge_one : 1 ≤ Real.sqrt 5 := by
    nlinarith
  have hy0 : 0 ≤ y := by
    dsimp [y]
    linarith
  have hyquad : y ^ 2 + y = 1 := by
    dsimp [y]
    nlinarith
  let x : ℝ := Real.sqrt y
  have hx2 : x ^ 2 = y := by
    dsimp [x]
    exact Real.sq_sqrt hy0
  refine ⟨x, y, ?_, ?_⟩
  · nlinarith
  · exact hx2.symm

theorem d_no_inverse_consumer :
    ¬ (∀ x : ℝ, ∃ y : ℝ, x * y = 1) := by
  intro h
  rcases h 0 with ⟨y, hy⟩
  norm_num at hy

theorem s_disc_consumer (b c : ℝ) :
    (∀ z : ℝ, z ^ 2 + b * z + c > 0) → b ^ 2 < 4 * c := by
  intro h
  have hz := h (-b / 2)
  nlinarith [sq_nonneg b]

theorem s_alt_goal_consumer (a : ℝ) :
    a > 0 → ∀ z : ℝ, ∃ w : ℝ, w * a > z := by
  intro ha z
  refine ⟨z / a + 1, ?_⟩
  have hane : a ≠ 0 := ne_of_gt ha
  have hmul : (z / a + 1) * a = z + a := by
    field_simp [hane]
  rw [hmul]
  linarith

theorem s_alt_hyp_consumer (c : ℝ) :
    (∀ z : ℝ, ∃ w : ℝ, w > z ∧ w * c > 1) → c > 0 := by
  intro h
  obtain ⟨w, hw0, hwc⟩ := h 0
  by_contra hc
  have hc0 : c ≤ 0 := le_of_not_gt hc
  have hw_nonneg : 0 ≤ w := le_of_lt hw0
  have hprod : w * c ≤ 0 := mul_nonpos_of_nonneg_of_nonpos hw_nonneg hc0
  linarith

theorem s_posreal_adapter (x : {x : ℝ // 0 < x}) :
    (x : ℝ) + 1 > 1 := by
  linarith [x.property]

theorem s_sqrtpos_adapter (y : {y : ℝ // 0 ≤ y}) :
    Real.sqrt (y : ℝ) + 1 ≥ 1 := by
  nlinarith [Real.sqrt_nonneg (y : ℝ)]

theorem s_two_consumer (a : ℝ) :
    (∃ u v : ℝ, u * u + v * v = a) → a ≥ 0 := by
  rintro ⟨u, v, huv⟩
  nlinarith [sq_nonneg u, sq_nonneg v]

theorem d_inverse_countermodel :
    ¬ (∀ x : ℝ, ∃ y : ℝ, x * y = 1) := by
  exact d_no_inverse_consumer

theorem t_amgm3_countermodel :
    ¬ (∀ x y : ℝ, x ^ 2 + y ^ 2 ≥ 3 * x * y) := by
  intro h
  have h11 := h 1 1
  norm_num at h11

end CrystalCrossProverCloseoutProbe
