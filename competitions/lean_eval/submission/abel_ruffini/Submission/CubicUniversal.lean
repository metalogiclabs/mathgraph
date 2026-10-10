import Mathlib

open Polynomial

private theorem base_mem (q : ℚ) : (q : ℂ) ∈ solvableByRad ℚ ℂ := by
  have h := (solvableByRad ℚ ℂ).algebraMap_mem q
  simpa [algebraMap.coe_ratCast] using h

private theorem cubic_factor_identity (Y U V W : ℂ)
    (hW : 1 + W + W ^ 2 = 0) :
    (Y - (U + V)) *
        (Y - (U * W + V * W ^ 2)) *
        (Y - (U * W ^ 2 + V * W)) =
      Y ^ 3 - 3 * (U * V) * Y - (U ^ 3 + V ^ 3) := by
  linear_combination
    (-(U + V - Y) *
      (U ^ 2 * W - U ^ 2 + U * V * W ^ 2 - U * V * W + U * V -
       U * Y + V ^ 2 * W - V ^ 2 - V * Y)) * hW

private theorem depressed_cubic_root_solvable
    (P Q : ℚ) (y : ℂ)
    (hy : y ^ 3 + (P : ℂ) * y + (Q : ℂ) = 0) :
    y ∈ solvableByRad ℚ ℂ := by
  by_cases hP : P = 0
  · subst P
    apply solvableByRad.rad_mem (by norm_num : (3 : ℕ) ≠ 0)
    have hy3 : y ^ 3 = -(Q : ℂ) := by linear_combination hy
    rw [hy3]
    exact (solvableByRad ℚ ℂ).neg_mem (base_mem Q)
  · let disc : ℚ := Q ^ 2 + 4 * (P ^ 3 / 27)
    obtain ⟨s, hs2⟩ := IsAlgClosed.exists_pow_nat_eq (disc : ℂ) (by norm_num : 0 < 2)
    have hs2' : s ^ 2 = (Q : ℂ) ^ 2 + 4 * ((P : ℂ) ^ 3 / 27) := by
      rw [hs2]
      dsimp [disc]
      push_cast
      ring
    have hs_mem : s ∈ solvableByRad ℚ ℂ := by
      apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
      rw [hs2]
      exact base_mem disc
    let A : ℂ := (-(Q : ℂ) + s) / 2
    let B : ℂ := (-(Q : ℂ) - s) / 2
    have hAB : A * B = -((P : ℂ) ^ 3) / 27 := by
      dsimp [A, B]
      field_simp
      calc
        (-((Q : ℂ)) + s) * (-((Q : ℂ)) - s) * 27 =
            (((Q : ℂ) ^ 2 - s ^ 2) * 27) := by ring
        _ = -(2 ^ 2 * (P : ℂ) ^ 3) := by rw [hs2']; ring
    have hA_mem : A ∈ solvableByRad ℚ ℂ := by
      exact (solvableByRad ℚ ℂ).div_mem
        ((solvableByRad ℚ ℂ).add_mem
          ((solvableByRad ℚ ℂ).neg_mem (base_mem Q)) hs_mem)
        (base_mem 2)
    obtain ⟨u, hu3⟩ := IsAlgClosed.exists_pow_nat_eq A (by norm_num : 0 < 3)
    have hu_mem : u ∈ solvableByRad ℚ ℂ := by
      apply solvableByRad.rad_mem (by norm_num : (3 : ℕ) ≠ 0)
      rw [hu3]
      exact hA_mem
    have hA0 : A ≠ 0 := by
      intro hA
      have hP3zero : (P : ℂ) ^ 3 = 0 := by
        calc
          (P : ℂ) ^ 3 = -27 * (A * B) := by rw [hAB]; ring
          _ = 0 := by rw [hA]; ring
      have hPc : (P : ℂ) ≠ 0 := by exact_mod_cast hP
      exact (pow_ne_zero 3 hPc) hP3zero
    have hu0 : u ≠ 0 := by
      intro hu
      rw [hu, zero_pow (by norm_num : 3 ≠ 0)] at hu3
      exact hA0 hu3.symm
    let v : ℂ := -(P : ℂ) / (3 * u)
    have huv : u * v = -(P : ℂ) / 3 := by
      dsimp [v]
      field_simp [hu0]
    have hv3 : v ^ 3 = B := by
      have hl : A * v ^ 3 = -((P : ℂ) ^ 3) / 27 := by
        rw [← hu3, ← mul_pow, huv]
        ring
      exact mul_left_cancel₀ hA0 (hl.trans hAB.symm)
    have hv_mem : v ∈ solvableByRad ℚ ℂ := by
      dsimp [v]
      exact (solvableByRad ℚ ℂ).div_mem
        ((solvableByRad ℚ ℂ).neg_mem (base_mem P))
        ((solvableByRad ℚ ℂ).mul_mem (base_mem 3) hu_mem)
    obtain ⟨r, hr2⟩ := IsAlgClosed.exists_pow_nat_eq (-3 : ℂ) (by norm_num : 0 < 2)
    have hr_mem : r ∈ solvableByRad ℚ ℂ := by
      apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
      rw [hr2]
      simpa using (solvableByRad ℚ ℂ).neg_mem (base_mem 3)
    let w : ℂ := (-1 + r) / 2
    have hw_mem : w ∈ solvableByRad ℚ ℂ := by
      dsimp [w]
      exact (solvableByRad ℚ ℂ).div_mem
        ((solvableByRad ℚ ℂ).add_mem
          ((solvableByRad ℚ ℂ).neg_mem (by simpa using base_mem (1 : ℚ))) hr_mem)
        (base_mem 2)
    have hw : 1 + w + w ^ 2 = 0 := by
      have hnum : ((-1 + r : ℂ) ^ 2 + 2 * (-1 + r) + 4) = 0 := by
        calc
          ((-1 + r : ℂ) ^ 2 + 2 * (-1 + r) + 4) = r ^ 2 + 3 := by ring
          _ = 0 := by rw [hr2]; norm_num
      dsimp [w]
      field_simp
      ring_nf at hnum ⊢
      exact hnum
    have hw3 : w ^ 3 = 1 := by
      have hw' : w ^ 2 + w + 1 = 0 := by linear_combination hw
      have hzero : w ^ 3 - 1 = 0 := by
        calc
          w ^ 3 - 1 = (w - 1) * (w ^ 2 + w + 1) := by ring
          _ = 0 := by rw [hw']; ring
      exact sub_eq_zero.mp hzero
    have hsum : u ^ 3 + v ^ 3 = -(Q : ℂ) := by
      rw [hu3, hv3]
      dsimp [A, B]
      ring
    have hfactor :
        (y - (u + v)) *
          (y - (u * w + v * w ^ 2)) *
          (y - (u * w ^ 2 + v * w)) = 0 := by
      rw [cubic_factor_identity y u v w hw, huv, hsum]
      linear_combination hy
    rcases mul_eq_zero.mp hfactor with h12 | h3
    · rcases mul_eq_zero.mp h12 with h1 | h2
      · rw [sub_eq_zero.mp h1]
        exact (solvableByRad ℚ ℂ).add_mem hu_mem hv_mem
      · rw [sub_eq_zero.mp h2]
        exact (solvableByRad ℚ ℂ).add_mem
          ((solvableByRad ℚ ℂ).mul_mem hu_mem hw_mem)
          ((solvableByRad ℚ ℂ).mul_mem hv_mem ((solvableByRad ℚ ℂ).pow_mem hw_mem 2))
    · rw [sub_eq_zero.mp h3]
      exact (solvableByRad ℚ ℂ).add_mem
        ((solvableByRad ℚ ℂ).mul_mem hu_mem ((solvableByRad ℚ ℂ).pow_mem hw_mem 2))
        ((solvableByRad ℚ ℂ).mul_mem hv_mem hw_mem)

theorem degree_three_solvable
    (p : ℚ[X]) (hp : p.natDegree = 3) (x : ℂ) (hx : aeval x p = 0) :
    x ∈ solvableByRad ℚ ℂ := by
  have hdeg : p.degree = (3 : WithBot ℕ) :=
    (degree_eq_iff_natDegree_eq_of_pos (by norm_num : 0 < 3)).2 hp
  have hlead : p.coeff 3 ≠ 0 := coeff_ne_zero_of_eq_degree hdeg
  let a : ℚ := p.coeff 3
  let b : ℚ := p.coeff 2
  let c : ℚ := p.coeff 1
  let d : ℚ := p.coeff 0
  have hpform : p = C a * X ^ 3 + C b * X ^ 2 + C c * X + C d := by
    let q : ℚ[X] := C a * X ^ 3 + C b * X ^ 2 + C c * X + C d
    have hqdeg : q.degree ≤ (3 : WithBot ℕ) := by
      dsimp [q]
      exact degree_cubic_le
    ext n
    by_cases hn : n ≤ 3
    · interval_cases n <;> simp [q, a, b, c, d]
    · have hp_lt : p.degree < n := by
        rw [hdeg]
        exact_mod_cast Nat.lt_of_not_ge hn
      have hq_lt : q.degree < n :=
        lt_of_le_of_lt hqdeg (by exact_mod_cast Nat.lt_of_not_ge hn)
      rw [coeff_eq_zero_of_degree_lt hp_lt, coeff_eq_zero_of_degree_lt hq_lt]
  rw [hpform] at hx
  simp [aeval_def] at hx
  let y : ℂ := 3 * (a : ℂ) * x + (b : ℂ)
  let P : ℚ := 3 * (3 * a * c - b ^ 2)
  let Q : ℚ := 27 * a ^ 2 * d - 9 * a * b * c + 2 * b ^ 3
  have hy : y ^ 3 + (P : ℂ) * y + (Q : ℂ) = 0 := by
    dsimp [y, P, Q]
    push_cast
    linear_combination 27 * (a : ℂ) ^ 2 * hx
  have hymem := depressed_cubic_root_solvable P Q y hy
  have haC : (a : ℂ) ≠ 0 := by exact_mod_cast hlead
  have hxform : x = (y - (b : ℂ)) / (3 * (a : ℂ)) := by
    dsimp [y]
    field_simp [haC]
    ring
  rw [hxform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem hymem (base_mem b))
    ((solvableByRad ℚ ℂ).mul_mem (base_mem 3) (base_mem a))
