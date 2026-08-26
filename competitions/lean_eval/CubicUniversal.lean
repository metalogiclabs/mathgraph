import Mathlib

open Polynomial

private theorem base_mem (q : ℚ) : (q : ℂ) ∈ solvableByRad ℚ ℂ := by
  have h := (solvableByRad ℚ ℂ).algebraMap_mem q
  simpa [algebraMap.coe_ratCast] using h

private theorem degree_two_solvable
    (p : ℚ[X]) (hp : p.natDegree = 2) (x : ℂ) (hx : aeval x p = 0) :
    x ∈ solvableByRad ℚ ℂ := by
  have hdeg : p.degree = (2 : WithBot ℕ) :=
    (degree_eq_iff_natDegree_eq_of_pos (by norm_num : 0 < 2)).2 hp
  have hlead : p.coeff 2 ≠ 0 := coeff_ne_zero_of_eq_degree hdeg
  let a : ℚ := p.coeff 2
  let b : ℚ := p.coeff 1
  let c : ℚ := p.coeff 0
  have hpform : p = C a * X ^ 2 + C b * X + C c := by
    let q : ℚ[X] := C a * X ^ 2 + C b * X + C c
    have hqdeg : q.degree ≤ (2 : WithBot ℕ) := by
      dsimp [q]
      exact degree_quadratic_le
    ext n
    by_cases hn : n ≤ 2
    · interval_cases n <;> simp [q, a, b, c]
    · have hp_lt : p.degree < n := by
        rw [hdeg]
        exact_mod_cast (Nat.lt_of_not_ge hn)
      have hq_lt : q.degree < n :=
        lt_of_le_of_lt hqdeg (by exact_mod_cast (Nat.lt_of_not_ge hn))
      rw [coeff_eq_zero_of_degree_lt hp_lt, coeff_eq_zero_of_degree_lt hq_lt]
  rw [hpform] at hx
  simp [aeval_def] at hx
  let y : ℂ := 2 * (a : ℂ) * x + (b : ℂ)
  let d : ℚ := b ^ 2 - 4 * a * c
  have hy_sq : y ^ 2 = (d : ℂ) := by
    dsimp [y, d]
    push_cast
    linear_combination 4 * (a : ℂ) * hx
  have hy_mem : y ∈ solvableByRad ℚ ℂ := by
    apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
    rw [hy_sq]
    exact base_mem d
  have haC : (a : ℂ) ≠ 0 := by exact_mod_cast hlead
  have hxform : x = (y - (b : ℂ)) / (2 * (a : ℂ)) := by
    dsimp [y]
    field_simp [haC]
    ring
  rw [hxform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem hy_mem (base_mem b))
    ((solvableByRad ℚ ℂ).mul_mem (base_mem 2) (base_mem a))

private theorem cube_root_mem (z u : ℂ)
    (hz : z ∈ solvableByRad ℚ ℂ) (hu : u ^ 3 = z) :
    u ∈ solvableByRad ℚ ℂ := by
  apply solvableByRad.rad_mem (by norm_num : (3 : ℕ) ≠ 0)
  rw [hu]
  exact hz

private theorem depressed_cubic_root_solvable
    (P Q : ℚ) (y : ℂ)
    (hy : y ^ 3 + (P : ℂ) * y + (Q : ℂ) = 0) :
    y ∈ solvableByRad ℚ ℂ := by
  by_cases hP : P = 0
  · subst P
    apply solvableByRad.rad_mem (by norm_num : (3 : ℕ) ≠ 0)
    have : y ^ 3 = -(Q : ℂ) := by linear_combination hy
    rw [this]
    exact (solvableByRad ℚ ℂ).neg_mem (base_mem Q)
  · let disc : ℚ := Q ^ 2 + 4 * (P ^ 3 / 27)
    let f : ℚ[X] := X ^ 2 - C disc
    have hfdeg : f.natDegree = 2 := by
      simp [f, disc]
    obtain ⟨s, hsroot⟩ :=
      (IsAlgClosed.splits (f.map (algebraMap ℚ ℂ))).exists_eval_eq_zero (by
        simp [f])
    have hs2 : s ^ 2 = (disc : ℂ) := by
      simpa [f, aeval_def] using hsroot
    have hs_mem : s ∈ solvableByRad ℚ ℂ := by
      apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
      rw [hs2]
      exact base_mem disc
    let A : ℂ := (-(Q : ℂ) + s) / 2
    let B : ℂ := (-(Q : ℂ) - s) / 2
    have hAB : A * B = -((P : ℂ) ^ 3) / 27 := by
      dsimp [A, B, disc] at *
      push_cast at hs2
      field_simp
      nlinarith [hs2]
    have hA_mem : A ∈ solvableByRad ℚ ℂ := by
      exact (solvableByRad ℚ ℂ).div_mem
        ((solvableByRad ℚ ℂ).add_mem ((solvableByRad ℚ ℂ).neg_mem (base_mem Q)) hs_mem)
        (base_mem 2)
    let g : ℂ[X] := X ^ 3 - C A
    obtain ⟨u, huroot⟩ := (IsAlgClosed.splits g).exists_eval_eq_zero (by simp [g])
    have hu3 : u ^ 3 = A := by simpa [g, aeval_def] using huroot
    have hu_mem : u ∈ solvableByRad ℚ ℂ := cube_root_mem A u hA_mem hu3
    have hA0 : A ≠ 0 := by
      intro hA
      have : ((P : ℂ) ^ 3) = 0 := by
        have := hAB
        rw [hA, zero_mul] at this
        field_simp at this
        linarith
      have : (P : ℂ) = 0 := pow_eq_zero this
      exact hP (by exact_mod_cast this)
    have hu0 : u ≠ 0 := by
      intro hu
      rw [hu, zero_pow (by norm_num : 3 ≠ 0)] at hu3
      exact hA0 hu3.symm
    let v : ℂ := -(P : ℂ) / (3 * u)
    have huv : u * v = -(P : ℂ) / 3 := by
      dsimp [v]
      field_simp [hu0]
      ring
    have hv3 : v ^ 3 = B := by
      have hprod : u ^ 3 * v ^ 3 = A * B := by rw [← mul_pow, huv, hu3]
      rw [hu3, hAB] at hprod
      apply (mul_left_cancel₀ hA0)
      rw [← hu3]
      calc
        u ^ 3 * v ^ 3 = -((P : ℂ) ^ 3) / 27 := hprod
        _ = A * B := hAB.symm
        _ = u ^ 3 * B := by rw [hu3]
    have hB_mem : B ∈ solvableByRad ℚ ℂ := by rw [← hv3]; exact (solvableByRad ℚ ℂ).pow_mem ((solvableByRad ℚ ℂ).div_mem ((solvableByRad ℚ ℂ).neg_mem (base_mem P)) ((solvableByRad ℚ ℂ).mul_mem (base_mem 3) hu_mem)) 3
    have hv_mem : v ∈ solvableByRad ℚ ℂ := cube_root_mem B v hB_mem hv3
    let wpoly : ℚ[X] := X ^ 2 + X + 1
    have hwdeg : wpoly.natDegree = 2 := by simp [wpoly]
    obtain ⟨w, hwroot⟩ :=
      (IsAlgClosed.splits (wpoly.map (algebraMap ℚ ℂ))).exists_eval_eq_zero (by simp [wpoly])
    have hw : w ^ 2 + w + 1 = 0 := by simpa [wpoly, aeval_def] using hwroot
    have hw_mem : w ∈ solvableByRad ℚ ℂ := degree_two_solvable wpoly hwdeg w (by simpa [aeval_def] using hwroot)
    have hsum : u ^ 3 + v ^ 3 = -(Q : ℂ) := by
      rw [hu3, hv3]
      dsimp [A, B]
      ring
    have hfactor :
        (y - (u + v)) *
          (y - (u * w + v * w ^ 2)) *
          (y - (u * w ^ 2 + v * w)) = 0 := by
      have hw3 : w ^ 3 = 1 := by
        calc
          w ^ 3 - 1 = (w - 1) * (w ^ 2 + w + 1) := by ring
          _ = 0 := by rw [hw]; ring
        linarith
      have hpoly :
          (y - (u + v)) *
            (y - (u * w + v * w ^ 2)) *
            (y - (u * w ^ 2 + v * w)) =
            y ^ 3 - 3 * (u * v) * y - (u ^ 3 + v ^ 3) := by
        nlinarith [hw, hw3]
      rw [hpoly, huv, hsum]
      linear_combination hy
    rcases mul_eq_zero.mp hfactor with h12 | h3
    · rcases mul_eq_zero.mp h12 with h1 | h2
      · have : y = u + v := sub_eq_zero.mp h1
        rw [this]
        exact (solvableByRad ℚ ℂ).add_mem hu_mem hv_mem
      · have : y = u * w + v * w ^ 2 := sub_eq_zero.mp h2
        rw [this]
        exact (solvableByRad ℚ ℂ).add_mem
          ((solvableByRad ℚ ℂ).mul_mem hu_mem hw_mem)
          ((solvableByRad ℚ ℂ).mul_mem hv_mem ((solvableByRad ℚ ℂ).pow_mem hw_mem 2))
    · have : y = u * w ^ 2 + v * w := sub_eq_zero.mp h3
      rw [this]
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
    have hqdeg : q.degree ≤ (3 : WithBot ℕ) := by dsimp [q]; exact degree_cubic_le
    ext n
    by_cases hn : n ≤ 3
    · interval_cases n <;> simp [q, a, b, c, d]
    · have hp_lt : p.degree < n := by rw [hdeg]; exact_mod_cast (Nat.lt_of_not_ge hn)
      have hq_lt : q.degree < n := lt_of_le_of_lt hqdeg (by exact_mod_cast (Nat.lt_of_not_ge hn))
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
