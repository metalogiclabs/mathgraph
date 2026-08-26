-- trigger quartic-universal verification
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
  have hresdeg_le : resolvent.natDegree ≤ 3 := by
    rw [natDegree_le_iff_coeff_eq_zero]
    intro N hN
    have hN3 : N ≠ 3 := by omega
    have hN2 : N ≠ 2 := by omega
    have hN1 : N ≠ 1 := by omega
    have hN0 : N ≠ 0 := by omega
    simp only [resolvent, coeff_add, coeff_sub, coeff_C_mul, coeff_X_pow, coeff_X, coeff_C]
    simp [hN3, hN2, hN1, hN0]
  have hrescoeff : resolvent.coeff 3 = 1 := by
    simp only [resolvent, coeff_add, coeff_sub, coeff_C_mul, coeff_X_pow, coeff_X, coeff_C]
    norm_num
  have hresdeg : resolvent.natDegree = 3 := by
    apply natDegree_eq_of_le_of_coeff_ne_zero hresdeg_le
    simpa [hrescoeff]
  have hresDegree : resolvent.degree = (3 : WithBot ℕ) :=
    (degree_eq_iff_natDegree_eq_of_pos (by norm_num : 0 < 3)).2 hresdeg
  obtain ⟨z, hzroot'⟩ :=
    IsAlgClosed.exists_aeval_eq_zero (k := ℂ) resolvent (by
      rw [hresDegree]
      norm_num)
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
    have hq2 : (Q : ℂ) ^ 2 = 0 := by
      rw [hzP] at hres
      linear_combination -hres
    have hQ0c : (Q : ℂ) = 0 := (sq_eq_zero_iff).mp hq2
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
    have hfacIdentity :
        (y ^ 2 + s * y + z / 2 - (Q : ℂ) / (2 * s)) *
          (y ^ 2 - s * y + z / 2 + (Q : ℂ) / (2 * s)) =
        y ^ 4 + (P : ℂ) * y ^ 2 + (Q : ℂ) * y + (R : ℂ) := by
      field_simp [hs0]
      rw [hs2]
      ring_nf
      rw [hQsq]
      ring
    have hfac:
        (y ^ 2 + s * y + z / 2 - (Q : ℂ) / (2 * s)) *
          (y ^ 2 - s * y + z / 2 + (Q : ℂ) / (2 * s)) = 0 := by
      rw [hfacIdentity, hy]
    rcases mul_eq_zero.mp hfac with hplus | hminus
    · apply quadratic_expr_solvable s (z / 2 - (Q : ℂ) / (2 * s)) y hs_mem
      · exact (solvableByRad ℚ ℂ).sub_mem
          ((solvableByRad ℚ ℂ).div_mem hzmem (base_mem4 2))
          ((solvableByRad ℚ ℂ).div_mem (base_mem4 Q)
            ((solvableByRad ℚ ℂ).mul_mem (base_mem4 2) hs_mem))
      · convert hplus using 1 <;> ring
    · apply quadratic_expr_solvable (-s) (z / 2 + (Q : ℂ) / (2 * s)) y
      · exact (solvableByRad ℚ ℂ).neg_mem hs_mem
      · exact (solvableByRad ℚ ℂ).add_mem
          ((solvableByRad ℚ ℂ).div_mem hzmem (base_mem4 2))
          ((solvableByRad ℚ ℂ).div_mem (base_mem4 Q)
            ((solvableByRad ℚ ℂ).mul_mem (base_mem4 2) hs_mem))
      · convert hminus using 1 <;> ring

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
    ext n
    by_cases hn : n ≤ 4
    · interval_cases n <;> simp [q, a, b, c, d, e]
    · have hp_lt : p.degree < n := by
        rw [hdeg]
        exact_mod_cast Nat.lt_of_not_ge hn
      rw [coeff_eq_zero_of_degree_lt hp_lt]
      have hn4 : n ≠ 4 := by omega
      have hn3 : n ≠ 3 := by omega
      have hn2 : n ≠ 2 := by omega
      have hn1 : n ≠ 1 := by omega
      have hn0 : n ≠ 0 := by omega
      simp only [q, coeff_add, coeff_C_mul, coeff_X_pow, coeff_X, coeff_C]
      simp [hn4, hn3, hn2, hn1, hn0]
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
