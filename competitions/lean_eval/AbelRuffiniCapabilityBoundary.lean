import Mathlib
import Archive.Wiedijk100Theorems.AbelRuffini

open Polynomial

/-- A square-root step preserves solvability by radicals. -/
theorem squareRadical_mem
    (z : ℂ) (hz : z ∈ solvableByRad ℚ ℂ)
    (s : ℂ) (hs : s ^ 2 = z) :
    s ∈ solvableByRad ℚ ℂ := by
  apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
  rw [hs]
  exact hz

/-- Final nonzero-square-root branch of the depressed-quartic reconstruction. -/
theorem quarticFinalReconstruct
    (P Q R y z s : ℂ)
    (hP : P ∈ solvableByRad ℚ ℂ)
    (hQ : Q ∈ solvableByRad ℚ ℂ)
    (_hR : R ∈ solvableByRad ℚ ℂ)
    (hz : z ∈ solvableByRad ℚ ℂ)
    (hs : s ^ 2 = z)
    (_hs0 : s ≠ 0)
    (hy : y ^ 2 + s * y + (z + P) / 2 - Q / (2 * s) = 0) :
    y ∈ solvableByRad ℚ ℂ := by
  have hs_mem := squareRadical_mem z hz s hs
  have htwo : (2 : ℂ) ∈ solvableByRad ℚ ℂ := by
    have h := (solvableByRad ℚ ℂ).algebraMap_mem (2 : ℚ)
    norm_num at h ⊢
  have hfour : (4 : ℂ) ∈ solvableByRad ℚ ℂ := by
    have h := (solvableByRad ℚ ℂ).algebraMap_mem (4 : ℚ)
    norm_num at h ⊢
  have hsden : (2 * s) ∈ solvableByRad ℚ ℂ :=
    (solvableByRad ℚ ℂ).mul_mem htwo hs_mem
  have hc : ((z + P) / 2 - Q / (2 * s)) ∈ solvableByRad ℚ ℂ := by
    exact (solvableByRad ℚ ℂ).sub_mem
      ((solvableByRad ℚ ℂ).div_mem ((solvableByRad ℚ ℂ).add_mem hz hP) htwo)
      ((solvableByRad ℚ ℂ).div_mem hQ hsden)
  have hdisc :
      (s ^ 2 - 4 * ((z + P) / 2 - Q / (2 * s))) ∈ solvableByRad ℚ ℂ := by
    exact (solvableByRad ℚ ℂ).sub_mem
      ((solvableByRad ℚ ℂ).pow_mem hs_mem 2)
      ((solvableByRad ℚ ℂ).mul_mem hfour hc)
  let t : ℂ := 2 * y + s
  have ht2 : t ^ 2 = s ^ 2 - 4 * ((z + P) / 2 - Q / (2 * s)) := by
    dsimp [t]
    linear_combination 4 * hy
  have ht : t ∈ solvableByRad ℚ ℂ := by
    apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
    rw [ht2]
    exact hdisc
  have hyform : y = (t - s) / 2 := by
    dsimp [t]
    ring
  rw [hyform]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem ht hs_mem) htwo

/-- The degenerate quadratic branch needed when the quartic square-root parameter vanishes. -/
theorem quarticZeroBranch
    (y c : ℂ)
    (hc : c ∈ solvableByRad ℚ ℂ)
    (hy : y ^ 2 + c = 0) :
    y ∈ solvableByRad ℚ ℂ := by
  have hnegc : (-c) ∈ solvableByRad ℚ ℂ := (solvableByRad ℚ ℂ).neg_mem hc
  apply solvableByRad.rad_mem (by norm_num : (2 : ℕ) ≠ 0)
  have : y ^ 2 = -c := by linear_combination hy
  rw [this]
  exact hnegc

/-- Translate a radical-solvable depressed-form root back through the quartic affine change. -/
theorem quarticTranslateBack
    (a b : ℚ) (y x : ℂ)
    (ha : (a : ℂ) ≠ 0)
    (hy : y ∈ solvableByRad ℚ ℂ)
    (hrel : y = 4 * (a : ℂ) * x + (b : ℂ)) :
    x ∈ solvableByRad ℚ ℂ := by
  have hb : (b : ℂ) ∈ solvableByRad ℚ ℂ := by
    have h := (solvableByRad ℚ ℂ).algebraMap_mem b
    simpa [algebraMap.coe_ratCast] using h
  have hden : (4 * (a : ℂ)) ∈ solvableByRad ℚ ℂ := by
    have h := (solvableByRad ℚ ℂ).algebraMap_mem (4 * a)
    simpa [algebraMap.coe_ratCast] using h
  have hx : x = (y - (b : ℂ)) / (4 * (a : ℂ)) := by
    rw [hrel]
    field_simp [ha]
    ring
  rw [hx]
  exact (solvableByRad ℚ ℂ).div_mem
    ((solvableByRad ℚ ℂ).sub_mem hy hb) hden

/-- For every degree at least five there is a polynomial with a complex root not solvable by radicals. -/
theorem highDegreeObstruction (n : ℕ) (hn : 5 ≤ n) :
    ¬ (∀ p : ℚ[X], p.natDegree = n → ∀ x : ℂ,
        aeval x p = 0 → x ∈ solvableByRad ℚ ℂ) := by
  intro hall
  let bad : ℚ[X] := AbelRuffini.Φ ℚ 4 2
  obtain ⟨y, hy⟩ :=
    (IsAlgClosed.splits (bad.map (algebraMap ℚ ℂ))).exists_eval_eq_zero (by
      simp [bad, AbelRuffini.degree_Phi])
  have hyroot : aeval y bad = 0 := by simpa [aeval_def] using hy
  have hynot : y ∉ solvableByRad ℚ ℂ := by
    apply AbelRuffini.not_solvable_by_rad' y
    simpa [bad, aeval_def] using hyroot
  let p : ℚ[X] := bad * X ^ (n - 5)
  have hbad0 : bad ≠ 0 := (AbelRuffini.monic_Phi 4 2).ne_zero
  have hdeg : p.natDegree = n := by
    rw [show p = bad * X ^ (n - 5) by rfl,
      natDegree_mul hbad0 (pow_ne_zero _ X_ne_zero)]
    simp [bad, AbelRuffini.natDegree_Phi]
    omega
  have hroot : aeval y p = 0 := by simp [p, hyroot]
  exact hynot (hall p hdeg y hroot)
