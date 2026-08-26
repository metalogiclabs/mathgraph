import Mathlib
import CubicUniversal

open Polynomial

private theorem base_mem4 (q : ℚ) : (q : ℂ) ∈ solvableByRad ℚ ℂ := by
  have h := (solvableByRad ℚ ℂ).algebraMap_mem q
  simpa [algebraMap.coe_ratCast] using h

private theorem quadratic_expr_solvable
    (A B y : ℂ)
    (hA : A ∈ solvableByRad ℚ ℂ)
    (hB : B ∈ solvableByRad ℚ ℂ)
    (hy : y ^ 2 + A * y + B = 0) :
    y ∈ solvableByRad ℚ ℂ := by
  have htwo : (2 : ℂ) ∈ solvableByRad ℚ ℂ := base_mem4 2
  have hfour : (4 : ℂ) ∈ solvableByRad ℚ ℂ := base_mem4 4
  have hdisc : A ^ 2 - 4 * B ∈ solvableByRad ℚ ℂ :=
    (solvableByRad ℚ ℂ).sub_mem
      ((solvableByRad ℚ ℂ).pow_mem hA 2)
      ((solvableByRad ℚ ℂ).mul_mem hfour hB)
  let t : ℂ := 2 * y + A
  have ht2 : t ^ 2 = A ^ 2 - 4 * B := by
    dsimp [t]
    linear_combination 4 * hy
  have ht : t ∈ solvableByRad ℚ ℂ := by
    apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
    rw [ht2]
    exact hdisc
  have hyform : y = (t - A) / 2 := by
    dsimp [t]
    ring
  rw [hyform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem ht hA) htwo

private theorem depressed_quartic_root_solvable
    (P Q R : ℚ) (y : ℂ)
    (hy : y ^ 4 + (P : ℂ) * y ^ 2 + (Q : ℂ) * y + (R : ℂ) = 0) :
    y ∈ solvableByRad ℚ ℂ := by
  let resolvent : ℚ[X] :=
    X ^ 3 - C P * X ^ 2 - C (4 * R) * X + C (4 * P * R - Q ^ 2)
  have hresdeg : resolvent.natDegree = 3 := by
    dsimp [resolvent]
    norm_num [natDegree_add_eq_left_of_natDegree_lt]
  obtain ⟨z, hzroot⟩ :=
    (IsAlgClosed.splits (resolvent.map (algebraMap ℚ ℂ))).exists_eval_eq_zero (by
      intro hzero
      have : resolvent = 0 := by
        apply map_injective (algebraMap ℚ ℂ)
        simpa using hzero
      rw [this] at hresdeg
      simp at hresdeg)
  have hzroot' : aeval z resolvent = 0 := by
    simpa [aeval_def] using hzroot
  have hzmem : z ∈ solvableByRad ℚ ℂ :=
    degree_three_solvable resolvent hresdeg z hzroot'
  have hres :
      z ^ 3 - (P : ℂ) * z ^ 2 - 4 * (R : ℂ) * z +
          (4 * (P : ℂ) * (R : ℂ) - (Q : ℂ) ^ 2) = 0 := by
    simpa [resolvent, aeval_def] using hzroot'
  obtain ⟨s, hs2⟩ :=
    IsAlgClosed.exists_pow_nat_eq (z - (P : ℂ)) (by norm_num : 0 < 2)
  have hs_mem : s ∈ solvableByRad ℚ ℂ := by
    apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
    rw [hs2]
    exact (solvableByRad ℚ ℂ).sub_mem hzmem (base_mem4 P)
  by_cases hs0 : s = 0
  · have hzP : z = (P : ℂ) := by
      have : z - (P : ℂ) = 0 := by
        rw [← hs2, hs0]
        norm_num
      exact sub_eq_zero.mp this
    have hQ0c : (Q : ℂ) = 0 := by
      rw [hzP] at hres
      have hq2 : (Q : ℂ) ^ 2 = 0 := by linear_combination hres
      exact (sq_eq_zero_iff).mp hq2
    have hQ0 : Q = 0 := by exact_mod_cast hQ0c
    subst Q
    have ht : y ^ 2 ∈ solvableByRad ℚ ℂ := by
      apply quadratic_expr_solvable (P : ℂ) (R : ℂ) (y ^ 2)
      · exact base_mem4 P
      · exact base_mem4 R
      · linear_combination hy
    apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
    exact ht
  · have hQsq : (Q : ℂ) ^ 2 = (z - (P : ℂ)) * (z ^ 2 - 4 * (R : ℂ)) := by
      linear_combination -hres
    have hfac :
        (y ^ 2 + s * y + z / 2 - (Q : ℂ) / (2 * s)) *
          (y ^ 2 - s * y + z / 2 + (Q : ℂ) / (2 * s)) = 0 := by
      have hs2' : s ^ 2 = z - (P : ℂ) := hs2
      field_simp [hs0]
      rw [show s ^ 2 = z - (P : ℂ) from hs2']
      rw [hQsq]
      linear_combination 4 * (z - (P : ℂ)) * hy
    rcases mul_eq_zero.mp hfac with hplus | hminus
    · apply quadratic_expr_solvable s (z / 2 - (Q : ℂ) / (2 * s)) y hs_mem
      · exact (solvableByRad ℚ ℂ).sub_mem
          ((solvableByRad ℚ ℂ).div_mem hzmem (base_mem4 2))
          ((solvableByRad ℚ ℂ).div_mem (base_mem4 Q)
            ((solvableByRad ℚ ℂ).mul_mem (base_mem4 2) hs_mem))
      · exact hplus
    · apply quadratic_expr_solvable (-s) (z / 2 + (Q : ℂ) / (2 * s)) y
      · exact (solvableByRad ℚ ℂ).neg_mem hs_mem
      · exact (solvableByRad ℚ ℂ).add_mem
          ((solvableByRad ℚ ℂ).div_mem hzmem (base_mem4 2))
          ((solvableByRad ℚ ℂ).div_mem (base_mem4 Q)
            ((solvableByRad ℚ ℂ).mul_mem (base_mem4 2) hs_mem))
      · simpa [neg_mul] using hminus

theorem degree_four_solvable
    (p : ℚ[X]) (hp : p.natDegree = 4) (x : ℂ) (hx : aeval x p = 0) :
    x ∈ solvableByRad ℚ ℂ := by
  have hdeg : p.degree = (4 : WithBot ℕ) :=
    (degree_eq_iff_natDegree_eq_of_pos (by norm_num : 0 < 4)).2 hp
  have hlead : p.coeff 4 ≠ 0 := coeff_ne_zero_of_eq_degree hdeg
  let a : ℚ := p.coeff 4
  let b : ℚ := p.coeff 3
  let c : ℚ := p.coeff 2
  let d : ℚ := p.coeff 1
  let e : ℚ := p.coeff 0
  have hpform :
      p = C a * X ^ 4 + C b * X ^ 3 + C c * X ^ 2 + C d * X + C e := by
    let q : ℚ[X] := C a * X ^ 4 + C b * X ^ 3 + C c * X ^ 2 + C d * X + C e
    have hqdeg : q.degree ≤ (4 : WithBot ℕ) := by
      dsimp [q]
      exact degree_quartic_le
    ext n
    by_cases hn : n ≤ 4
    · interval_cases n <;> simp [q, a, b, c, d, e]
    · have hp_lt : p.degree < n := by
        rw [hdeg]
        exact_mod_cast Nat.lt_of_not_ge hn
      have hq_lt : q.degree < n :=
        lt_of_le_of_lt hqdeg (by exact_mod_cast Nat.lt_of_not_ge hn)
      rw [coeff_eq_zero_of_degree_lt hp_lt, coeff_eq_zero_of_degree_lt hq_lt]
  rw [hpform] at hx
  simp [aeval_def] at hx
  let y : ℂ := 4 * (a : ℂ) * x + (b : ℂ)
  let P : ℚ := 16 * a * c - 6 * b ^ 2
  let Q : ℚ := 64 * a ^ 2 * d - 32 * a * b * c + 8 * b ^ 3
  let R : ℚ := 256 * a ^ 3 * e - 64 * a ^ 2 * b * d + 16 * a * b ^ 2 * c - 3 * b ^ 4
  have hy : y ^ 4 + (P : ℂ) * y ^ 2 + (Q : ℂ) * y + (R : ℂ) = 0 := by
    dsimp [y, P, Q, R]
    push_cast
    linear_combination 256 * (a : ℂ) ^ 3 * hx
  have hymem := depressed_quartic_root_solvable P Q R y hy
  have haC : (a : ℂ) ≠ 0 := by exact_mod_cast hlead
  have hxform : x = (y - (b : ℂ)) / (4 * (a : ℂ)) := by
    dsimp [y]
    field_simp [haC]
    ring
  rw [hxform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem hymem (base_mem4 b))
    ((solvableByRad ℚ ℂ).mul_mem (base_mem4 4) (base_mem4 a))
