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

/-- Squarefreeness protects the Sturm start pair: a real root of `p` cannot
also be a root of `p'`. This is the boundary condition missing from arbitrary
truncated-tail local constancy. -/
theorem squarefree_root_derivative_ne_zero (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) (hr : p.eval r = 0) :
    p.derivative.eval r ≠ 0 := by
  have hsep : p.Separable := (PerfectField.separable_iff_squarefree).2 hp
  exact hsep.eval₂_derivative_ne_zero (RingHom.id ℝ) hr

/-- Equivalent no-common-real-root form for the initial Sturm pair. -/
theorem squarefree_sturm_start_no_common_root (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) :
    ¬ (p.eval r = 0 ∧ p.derivative.eval r = 0) := by
  rintro ⟨hr, hdr⟩
  exact squarefree_root_derivative_ne_zero p r hp hr hdr
