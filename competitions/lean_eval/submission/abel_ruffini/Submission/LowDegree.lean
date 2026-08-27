import Mathlib

open Polynomial

private theorem baseMem (q : ℚ) : (q : ℂ) ∈ solvableByRad ℚ ℂ := by
  have h := (solvableByRad ℚ ℂ).algebraMap_mem q
  simpa [algebraMap.coe_ratCast] using h

theorem degree_one_solvable
    (p : ℚ[X]) (hp : p.natDegree = 1) (x : ℂ) (hx : aeval x p = 0) :
    x ∈ solvableByRad ℚ ℂ := by
  have hdeg : p.degree = (1 : WithBot ℕ) :=
    (degree_eq_iff_natDegree_eq_of_pos (by norm_num : 0 < 1)).2 hp
  have hlead : p.coeff 1 ≠ 0 := coeff_ne_zero_of_eq_degree hdeg
  let a : ℚ := p.coeff 1
  let b : ℚ := p.coeff 0
  have hpform : p = C a * X + C b := by
    ext n
    by_cases hn : n ≤ 1
    · interval_cases n <;> simp [a, b]
    · have hp_lt : p.degree < n := by
        rw [hdeg]
        exact_mod_cast Nat.lt_of_not_ge hn
      have hp0 : p.coeff n = 0 := coeff_eq_zero_of_degree_lt hp_lt
      rw [hp0]
      have hn1 : n ≠ 1 := by omega
      have hn0 : n ≠ 0 := by omega
      simp [coeff_C, coeff_X, a, b, hn1, hn0]
  rw [hpform] at hx
  simp [aeval_def] at hx
  have haC : (a : ℂ) ≠ 0 := by exact_mod_cast hlead
  have hxform : x = -(b : ℂ) / (a : ℂ) := by
    field_simp [haC]
    linear_combination hx
  rw [hxform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).neg_mem (baseMem b)) (baseMem a)

theorem degree_two_solvable
    (p : ℚ[X]) (hp : p.natDegree = 2) (x : ℂ) (hx : aeval x p = 0) :
    x ∈ solvableByRad ℚ ℂ := by
  have hdeg : p.degree = (2 : WithBot ℕ) :=
    (degree_eq_iff_natDegree_eq_of_pos (by norm_num : 0 < 2)).2 hp
  have hlead : p.coeff 2 ≠ 0 := coeff_ne_zero_of_eq_degree hdeg
  let a : ℚ := p.coeff 2
  let b : ℚ := p.coeff 1
  let c : ℚ := p.coeff 0
  have hpform : p = C a * X ^ 2 + C b * X + C c := by
    ext n
    by_cases hn : n ≤ 2
    · interval_cases n <;> simp [a, b, c]
    · have hp_lt : p.degree < n := by
        rw [hdeg]
        exact_mod_cast Nat.lt_of_not_ge hn
      have hp0 : p.coeff n = 0 := coeff_eq_zero_of_degree_lt hp_lt
      rw [hp0]
      have hn2 : n ≠ 2 := by omega
      have hn1 : n ≠ 1 := by omega
      have hn0 : n ≠ 0 := by omega
      simp [coeff_C, coeff_X, coeff_X_pow, a, b, c, hn2, hn1, hn0]
  rw [hpform] at hx
  simp [aeval_def] at hx
  let disc : ℚ := b ^ 2 - 4 * a * c
  let t : ℂ := 2 * (a : ℂ) * x + (b : ℂ)
  have ht2 : t ^ 2 = (disc : ℂ) := by
    dsimp [t, disc]
    push_cast
    linear_combination 4 * (a : ℂ) * hx
  have ht : t ∈ solvableByRad ℚ ℂ := by
    apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
    rw [ht2]
    exact baseMem disc
  have haC : (a : ℂ) ≠ 0 := by exact_mod_cast hlead
  have hxform : x = (t - (b : ℂ)) / (2 * (a : ℂ)) := by
    dsimp [t]
    field_simp [haC]
    ring
  have hden : (2 * (a : ℂ)) ∈ solvableByRad ℚ ℂ := by
    exact (solvableByRad ℚ ℂ).mul_mem (baseMem 2) (baseMem a)
  rw [hxform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem ht (baseMem b)) hden
