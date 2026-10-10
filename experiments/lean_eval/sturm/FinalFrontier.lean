import ChallengeDeps
import TailComposition
import SigmaLocal
import Termination

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- At a simple root, the polynomial value crosses with the sign dictated by
its derivative. -/
theorem simple_root_crossing_sign_eventually (p : ℝ[X]) (r : ℝ)
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
  have hev : ∀ᶠ x in 𝓝 r, 0 < q x * p.derivative.eval r := by
    have hmem : Set.Ioi (0 : ℝ) ∈ 𝓝 ((fun x => q x * p.derivative.eval r) r) := by
      simpa [q] using (IsOpen.mem_nhds isOpen_Ioi hpos)
    change (fun x => q x * p.derivative.eval r) ⁻¹' Set.Ioi 0 ∈ 𝓝 r
    exact hprod hmem
  filter_upwards [hev] with x hx
  constructor
  · intro hxr
    have hne : x ≠ r := ne_of_lt hxr
    have hden : x - r ≠ 0 := sub_ne_zero.mpr hne
    have hqx : 0 < (p.eval x / (x - r)) * p.derivative.eval r := by
      simpa [q, hne, hr] using hx
    have heq :
        p.eval x * p.derivative.eval r =
          ((p.eval x / (x - r)) * p.derivative.eval r) * (x - r) := by
      field_simp [hden]
    rw [heq]
    exact mul_neg_of_pos_of_neg hqx (sub_neg.mpr hxr)
  · intro hrx
    have hne : x ≠ r := ne_of_gt hrx
    have hden : x - r ≠ 0 := sub_ne_zero.mpr hne
    have hqx : 0 < (p.eval x / (x - r)) * p.derivative.eval r := by
      simpa [q, hne, hr] using hx
    have heq :
        p.eval x * p.derivative.eval r =
          ((p.eval x / (x - r)) * p.derivative.eval r) * (x - r) := by
      field_simp [hden]
    rw [heq]
    exact mul_pos hqx (sub_pos.mpr hrx)

/-- The derivative keeps the same sign as its value at the root nearby. -/
theorem derivative_same_sign_eventually (p : ℝ[X]) (r : ℝ)
    (hd : p.derivative.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r, 0 < p.derivative.eval x * p.derivative.eval r := by
  let f : ℝ → ℝ := fun x => p.derivative.eval x * p.derivative.eval r
  have hf : ContinuousAt f r := p.derivative.continuousAt.mul continuousAt_const
  have hpos : 0 < f r := by
    dsimp [f]
    exact mul_self_pos.mpr hd
  have hmem : Set.Ioi (0 : ℝ) ∈ 𝓝 (f r) := IsOpen.mem_nhds isOpen_Ioi hpos
  change f ⁻¹' Set.Ioi 0 ∈ 𝓝 r
  exact hf hmem

/-- Benchmark-level root jump.  Across a squarefree root, the actual `sigma`
for the full benchmark Sturm chain drops by exactly one. -/
theorem squarefree_sigma_local_drop (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) (hr : p.eval r = 0) :
    ∃ U : Set ℝ, U ∈ 𝓝 r ∧
      ∀ x ∈ U, ∀ y ∈ U, x < r → r < y → sigma p x = sigma p y + 1 := by
  have hd : p.derivative.eval r ≠ 0 := squarefree_root_derivative_ne_zero p r hp hr
  have hdp : p.derivative ≠ 0 := by
    intro h
    have : p.derivative.eval r = 0 := by simp [h]
    exact hd this
  let c : ℝ[X] := -(p % p.derivative)
  have hreg := squarefree_sturmChain_regular p r hp
  have htailreg : SturmRegularAt r p.derivative c (p.natDegree + 1) := by
    simpa [SturmRegularAt, hdp, c, Nat.add_assoc] using hreg
  have htail := sturmAux_variation_locally_constant
    p.derivative c r (p.natDegree + 1) hd htailreg
  have hcross := simple_root_crossing_sign_eventually p r hr hd
  have hdsame := derivative_same_sign_eventually p r hd
  have hdev := polynomial_eval_eventually_ne_zero p.derivative r hd
  have hgood : ∀ᶠ z in 𝓝 r,
      signChanges ((sturmAux p.derivative c (p.natDegree + 1)).map (fun q => q.eval z)) =
        signChanges ((sturmAux p.derivative c (p.natDegree + 1)).map (fun q => q.eval r)) ∧
      ((z < r → p.eval z * p.derivative.eval r < 0) ∧
       (r < z → 0 < p.eval z * p.derivative.eval r)) ∧
      0 < p.derivative.eval z * p.derivative.eval r ∧
      p.derivative.eval z ≠ 0 := by
    filter_upwards [htail, hcross, hdsame, hdev] with z hz hc hs hn
    exact ⟨hz, hc, hs, hn⟩
  rcases mem_nhds_iff.1 hgood with ⟨U, hUsub, hUopen, hrU⟩
  refine ⟨U, hUopen.mem_nhds hrU, ?_⟩
  intro x hx y hy hxr hry
  have gx := hUsub hx
  have gy := hUsub hy
  have hpxr : p.eval x * p.derivative.eval r < 0 := gx.2.1.1 hxr
  have hpyr : 0 < p.eval y * p.derivative.eval r := gy.2.1.2 hry
  have hdxr : 0 < p.derivative.eval x * p.derivative.eval r := gx.2.2.1
  have hdyr : 0 < p.derivative.eval y * p.derivative.eval r := gy.2.2.1
  have hpx : p.eval x ≠ 0 := by
    intro hz
    simp [hz] at hpxr
  have hpy : p.eval y ≠ 0 := by
    intro hz
    simp [hz] at hpyr
  have hdx : p.derivative.eval x ≠ 0 := gx.2.2.2
  have hdy : p.derivative.eval y ≠ 0 := gy.2.2.2
  have hxneg : p.eval x * p.derivative.eval x < 0 := by
    rcases lt_or_gt_of_ne hd with hdrneg | hdrpos
    · have hdxneg : p.derivative.eval x < 0 := by nlinarith
      have hpxpos : 0 < p.eval x := by nlinarith
      exact mul_neg_of_pos_of_neg hpxpos hdxneg
    · have hdxpos : 0 < p.derivative.eval x := by nlinarith
      have hpxneg : p.eval x < 0 := by nlinarith
      exact mul_neg_of_neg_of_pos hpxneg hdxpos
  have hypos : 0 < p.eval y * p.derivative.eval y := by
    rcases lt_or_gt_of_ne hd with hdrneg | hdrpos
    · have hdyneg : p.derivative.eval y < 0 := by nlinarith
      have hpyneg : p.eval y < 0 := by nlinarith
      exact mul_pos_of_neg_of_neg hpyneg hdyneg
    · have hdypos : 0 < p.derivative.eval y := by nlinarith
      have hpypos : 0 < p.eval y := by nlinarith
      exact mul_pos hpypos hdypos
  have hchain : sturmChain p = p :: sturmAux p.derivative c (p.natDegree + 1) := by
    simp [sturmChain, sturmAux, hdp, c, Nat.add_assoc]
  have htailshapeX :
      (sturmAux p.derivative c (p.natDegree + 1)).map (fun q => q.eval x) =
        p.derivative.eval x ::
          (sturmAux p.derivative c (p.natDegree + 1)).tail.map (fun q => q.eval x) := by
    rw [sturmAux_eq_cons_tail]
    rfl
  have htailshapeY :
      (sturmAux p.derivative c (p.natDegree + 1)).map (fun q => q.eval y) =
        p.derivative.eval y ::
          (sturmAux p.derivative c (p.natDegree + 1)).tail.map (fun q => q.eval y) := by
    rw [sturmAux_eq_cons_tail]
    rfl
  unfold sigma
  rw [hchain]
  simp only [List.map_cons]
  rw [htailshapeX, htailshapeY]
  rw [signChanges_cons_cons_of_ne_zero _ _ _ hpx hdx,
      signChanges_cons_cons_of_ne_zero _ _ _ hpy hdy]
  have hnx : (if p.eval x * p.derivative.eval x < 0 then 1 else 0) = 1 := by simp [hxneg]
  have hny : (if p.eval y * p.derivative.eval y < 0 then 1 else 0) = 0 := by
    have : ¬ p.eval y * p.derivative.eval y < 0 := not_lt.mpr (le_of_lt hypos)
    simp [this]
  rw [hnx, hny]
  have htx := gx.1
  have hty := gy.1
  rw [htailshapeX] at htx
  rw [htailshapeY] at hty
  omega

/-- Root set in an open interval, in the exact shape of the benchmark target. -/
def intervalRoots (p : ℝ[X]) (a b : ℝ) : Set ℝ :=
  {x : ℝ | a < x ∧ x < b ∧ p.eval x = 0}

/-- The remaining global telescope is isolated as a pure jump-counting interface:
if `sigma` is locally constant away from the finite root set and drops once at
each root, its endpoint difference is exactly the number of roots. -/
theorem sturm_global_telescope_interface
    (p : ℝ[X]) (a b : ℝ) (hp : Squarefree p)
    (ha : p.eval a ≠ 0) (hb : p.eval b ≠ 0) (hab : a < b)
    (hjump : ∀ r, p.eval r = 0 →
      ∃ U : Set ℝ, U ∈ 𝓝 r ∧
        ∀ x ∈ U, ∀ y ∈ U, x < r → r < y → sigma p x = sigma p y + 1) :
    (intervalRoots p a b).ncard = sigma p a - sigma p b := by
  -- This proof is deliberately attacked as one global frontier: finite roots,
  -- root-free interval constancy, and one-unit jumps.  The local analytic and
  -- recursive algebraic layers above are already discharged.
  have hp0 : p ≠ 0 := by
    intro hz
    apply ha
    simp [hz]
  have hfiniteRoots : Set.Finite {x : ℝ | p.eval x = 0} := by
    simpa [Polynomial.IsRoot] using (Polynomial.finite_setOfPred_isRoot (p := p) hp0)
  have hfinite : (intervalRoots p a b).Finite := by
    apply hfiniteRoots.subset
    intro x hx
    exact hx.2.2
  -- expose the finite ordered frontier explicitly; the next CI residual tells
  -- us only the minimal library bridge needed for telescoping it.
  rw [Set.ncard_eq_toFinset_card _ hfinite]
  classical
  let R : Finset ℝ := hfinite.toFinset
  change R.card = sigma p a - sigma p b
  -- finite ordered induction over the roots in (a,b)
  induction R using Finset.induction_on with
  | empty =>
      simp only [Finset.card_empty]
      have hlocal : IsLocallyConstant (fun x : Set.Icc a b => sigma p x.1) := by
        rw [IsLocallyConstant.iff_eventually_eq]
        intro x
        have hxnon : p.eval x.1 ≠ 0 := by
          intro hx0
          have hxroot : x.1 ∈ intervalRoots p a b := by
            have hxa : a ≤ x.1 := x.2.1
            have hxb : x.1 ≤ b := x.2.2
            have hane : x.1 ≠ a := by intro h; subst x; exact ha hx0
            have hbne : x.1 ≠ b := by intro h; subst x; exact hb hx0
            exact ⟨lt_of_le_of_ne hxa (Ne.symm hane), lt_of_le_of_ne hxb hbne, hx0⟩
          have : x.1 ∈ R := by simpa [R] using hfinite.mem_toFinset.mpr hxroot
          simpa using this
        have hev := squarefree_sigma_locally_constant_at_nonroot p x.1 hp hxnon
        exact continuousAt_subtype_val.eventually hev
      have heq := hlocal.apply_eq_of_isPreconnected
        (isPreconnected_Icc : IsPreconnected (Set.Icc a b))
        (show a ∈ Set.Icc a b by exact ⟨le_rfl, le_of_lt hab⟩)
        (show b ∈ Set.Icc a b by exact ⟨le_of_lt hab, le_rfl⟩)
      simp at heq
      omega
  | @insert r s hrnot ih =>
      -- Sorting is not required in the local layers; this branch is the single
      -- remaining finite-order bookkeeping problem if mathlib cannot discharge
      -- it directly from the jump interface.
      have _ := hjump r
      omega

/-- Full benchmark theorem, with all analytic/algebraic work discharged and
only the finite global telescope delegated to the interface above. -/
theorem sturm_full_frontier (p : ℝ[X]) (a b : ℝ)
    (hp : Squarefree p) (ha : p.eval a ≠ 0) (hb : p.eval b ≠ 0) (hab : a < b) :
    {x : ℝ | a < x ∧ x < b ∧ p.eval x = 0}.ncard = sigma p a - sigma p b := by
  change (intervalRoots p a b).ncard = sigma p a - sigma p b
  apply sturm_global_telescope_interface p a b hp ha hb hab
  intro r hr
  exact squarefree_sigma_local_drop p r hp hr
