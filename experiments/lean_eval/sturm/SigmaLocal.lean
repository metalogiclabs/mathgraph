import ChallengeDeps
import TailComposition

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- If the next Sturm remainder vanishes at a point, the following remainder
has value opposite to the current entry. This is the local regularity law
used to quotient an interior zero out of the chain. -/
theorem sturm_next_after_zero (a b : ℝ[X]) (r : ℝ)
    (hb : b.eval r = 0) :
    (-(a % b)).eval r = -a.eval r := by
  have h := congrArg (fun q : ℝ[X] => q.eval r) (EuclideanDomain.mod_add_div a b)
  have hrem : (a % b).eval r = a.eval r := by
    simpa [hb] using h
  simp [hrem]

/-- A nonzero polynomial evaluation is locally nonzero. -/
theorem polynomial_eval_eventually_ne_zero (p : ℝ[X]) (r : ℝ)
    (hp : p.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r, p.eval x ≠ 0 := by
  have hcont : ContinuousAt (fun x : ℝ => p.eval x) r := p.continuousAt
  have hopen : ({0}ᶜ : Set ℝ) ∈ 𝓝 (p.eval r) := by
    exact IsOpen.mem_nhds isOpen_compl_singleton hp
  change (fun x : ℝ => p.eval x) ⁻¹' ({0}ᶜ : Set ℝ) ∈ 𝓝 r
  exact hcont hopen

/-- Two nonzero adjacent Sturm entries have locally constant pair variation. -/
theorem polynomial_pair_signchange_locally_constant
    (a b : ℝ[X]) (r : ℝ) (ha : a.eval r ≠ 0) (hb : b.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      (if a.eval x * b.eval x < 0 then 1 else 0) =
      (if a.eval r * b.eval r < 0 then 1 else 0) := by
  let f : ℝ → ℝ := fun x => a.eval x * b.eval x
  have hf : ContinuousAt f r := a.continuousAt.mul b.continuousAt
  have hfr : f r ≠ 0 := by simpa [f] using mul_ne_zero ha hb
  rcases lt_or_gt_of_ne hfr with hneg | hpos
  · have hmem : Set.Iio (0 : ℝ) ∈ 𝓝 (f r) := IsOpen.mem_nhds isOpen_Iio hneg
    have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
      change f ⁻¹' Set.Iio 0 ∈ 𝓝 r
      exact hf hmem
    filter_upwards [hev] with x hx
    simp [f, hx, hneg]
  · have hmem : Set.Ioi (0 : ℝ) ∈ 𝓝 (f r) := IsOpen.mem_nhds isOpen_Ioi hpos
    have hev : ∀ᶠ x in 𝓝 r, 0 < f x := by
      change f ⁻¹' Set.Ioi 0 ∈ 𝓝 r
      exact hf hmem
    filter_upwards [hev] with x hx
    have hnx : ¬ f x < 0 := not_lt.mpr (le_of_lt hx)
    have hnr : ¬ f r < 0 := not_lt.mpr (le_of_lt hpos)
    simp [f, hnx, hnr]

/-- First bounded tail-composition theorem. For two Euclidean steps, once the
head evaluation is nonzero, sign variation is locally constant. This is the
smallest nontrivial instance containing the interior-zero branch. -/
theorem sturmAux_two_step_variation_locally_constant
    (a b : ℝ[X]) (r : ℝ) (ha : a.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      signChanges ((sturmAux a b 2).map (fun q => q.eval x)) =
      signChanges ((sturmAux a b 2).map (fun q => q.eval r)) := by
  by_cases hbpoly : b = 0
  · simp [sturmAux, hbpoly]
  · rw [show sturmAux a b 2 = a :: sturmAux b (-(a % b)) 1 by simp [sturmAux, hbpoly]]
    let c : ℝ[X] := -(a % b)
    by_cases hcpoly : c = 0
    · have hbc : sturmAux b c 1 = [b] := by simp [sturmAux, c, hcpoly]
      rw [hbc]
      simp [signChanges]
    · have hbc : sturmAux b c 1 = [b, c] := by
        simp [sturmAux, c, hcpoly]
      rw [hbc]
      by_cases hb : b.eval r = 0
      · have hc : c.eval r = -a.eval r := by
          dsimp [c]
          exact sturm_next_after_zero a b r hb
        have hac : a.eval r * c.eval r < 0 := by
          rw [hc]
          have : 0 < a.eval r * a.eval r := mul_self_pos.mpr ha
          nlinarith
        let f : ℝ → ℝ := fun x => a.eval x * c.eval x
        have hf : ContinuousAt f r := a.continuousAt.mul c.continuousAt
        have hmem : Set.Iio (0 : ℝ) ∈ 𝓝 (f r) :=
          IsOpen.mem_nhds isOpen_Iio (by simpa [f] using hac)
        have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
          change f ⁻¹' Set.Iio 0 ∈ 𝓝 r
          exact hf hmem
        filter_upwards [hev] with x hx
        have hxone := signChanges_three_of_opposite_ends
          (a.eval x) (b.eval x) (c.eval x) (by simpa [f] using hx)
        have hrone := signChanges_three_of_opposite_ends
          (a.eval r) (b.eval r) (c.eval r) hac
        simpa using hxone.trans hrone.symm
      · have hb_ev := polynomial_eval_eventually_ne_zero b r hb
        by_cases hc : c.eval r = 0
        · have hnext : c.eval r = 0 := hc
          filter_upwards [hb_ev] with x hbx
          simp [signChanges, hb, hc, hbx]
        · have hab := polynomial_pair_signchange_locally_constant a b r ha hb
          have hbcv := polynomial_pair_signchange_locally_constant b c r hb hc
          filter_upwards [hab, hbcv, hb_ev, polynomial_eval_eventually_ne_zero c r hc] with x habx hbcx hbx hcx
          simp [signChanges, ha, hb, hc, hbx, hcx, habx, hbcx]
