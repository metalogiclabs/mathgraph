import ChallengeDeps

open LeanEval.Algebra
open Polynomial
open Set Filter
open scoped Classical Topology

/-- Inserting a zero anywhere does not affect sign variation. -/
theorem signChanges_insert_zero (xs ys : List ℝ) :
    signChanges (xs ++ 0 :: ys) = signChanges (xs ++ ys) := by
  have hfilter :
      (xs ++ 0 :: ys).filter (· ≠ 0) = (xs ++ ys).filter (· ≠ 0) := by
    simp [List.filter_append]
  simp only [signChanges]
  rw [hfilter]

/-- Analytic sign law at a simple polynomial root. -/
theorem simple_root_local_crossing_sign (p : ℝ[X]) (r : ℝ)
    (hr : p.eval r = 0) (hd : p.derivative.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      ((x < r → p.eval x * p.derivative.eval r < 0) ∧
       (r < x → 0 < p.eval x * p.derivative.eval r)) := by
  let q : ℝ → ℝ := Function.update
    (fun x => (p.eval x - p.eval r) / (x - r))
    r (p.derivative.eval r)
  have hq : ContinuousAt q r := by
    dsimp [q]
    exact (p.hasDerivAt r).continuousAt_div
  have hprod : ContinuousAt (fun x => q x * p.derivative.eval r) r :=
    hq.mul continuousAt_const
  have hpos : 0 < p.derivative.eval r * p.derivative.eval r := mul_self_pos.mpr hd
  have hnhds : Set.Ioi (0 : ℝ) ∈ 𝓝 ((fun x => q x * p.derivative.eval r) r) := by
    simpa [q] using (IsOpen.mem_nhds isOpen_Ioi hpos)
  have hev : ∀ᶠ x in 𝓝 r, 0 < q x * p.derivative.eval r := by
    change (fun x => q x * p.derivative.eval r) ⁻¹' Set.Ioi 0 ∈ 𝓝 r
    exact hprod hnhds
  filter_upwards [hev] with x hx
  constructor
  · intro hxr
    have hne : x ≠ r := ne_of_lt hxr
    have hden : x - r ≠ 0 := sub_ne_zero.mpr hne
    have hqpos : 0 < (p.eval x / (x - r)) * p.derivative.eval r := by
      simpa [q, hne, hr] using hx
    have heq :
        p.eval x * p.derivative.eval r =
          ((p.eval x / (x - r)) * p.derivative.eval r) * (x - r) := by
      field_simp [hden]
    rw [heq]
    exact mul_neg_of_pos_of_neg hqpos (sub_neg.mpr hxr)
  · intro hrx
    have hne : x ≠ r := ne_of_gt hrx
    have hden : x - r ≠ 0 := sub_ne_zero.mpr hne
    have hqpos : 0 < (p.eval x / (x - r)) * p.derivative.eval r := by
      simpa [q, hne, hr] using hx
    have heq :
        p.eval x * p.derivative.eval r =
          ((p.eval x / (x - r)) * p.derivative.eval r) * (x - r) := by
      field_simp [hden]
    rw [heq]
    exact mul_pos hqpos (sub_pos.mpr hrx)
