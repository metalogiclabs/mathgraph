import ChallengeDeps
import TailComposition
import SigmaLocal
import Termination
import Mathlib.Topology.LocallyConstant.Basic

open LeanEval.Algebra
open Polynomial
open Set Filter
open scoped Classical Topology

/-- A nonzero polynomial keeps the sign of its value at the reference point
throughout a sufficiently small neighbourhood. -/
theorem polynomial_eval_same_sign_locally (p : ℝ[X]) (r : ℝ)
    (hp : p.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r, 0 < p.eval x * p.eval r := by
  let f : ℝ → ℝ := fun x => p.eval x * p.eval r
  have hf : ContinuousAt f r := p.continuousAt.mul continuousAt_const
  have hpos : 0 < f r := by
    dsimp [f]
    exact mul_self_pos.mpr hp
  have hmem : Set.Ioi (0 : ℝ) ∈ 𝓝 (f r) := IsOpen.mem_nhds isOpen_Ioi hpos
  change f ⁻¹' Set.Ioi 0 ∈ 𝓝 r
  exact hf hmem

/-- At a simple root, the benchmark variation drops by exactly one when one
crosses the root from left to right.  This is the full-chain lift of the
leading-pair crossing law: the recursive tail is locally constant. -/
theorem squarefree_sigma_local_root_drop
    (p : ℝ[X]) (r : ℝ) (hp : Squarefree p) (hr : p.eval r = 0) :
    ∃ U : Set ℝ, U ∈ 𝓝 r ∧
      ∀ x ∈ U, ∀ y ∈ U, x < r → r < y → sigma p x = sigma p y + 1 := by
  let d : ℝ[X] := p.derivative
  let c : ℝ[X] := -(p % d)
  have hd : d.eval r ≠ 0 := by
    simpa [d] using squarefree_root_derivative_ne_zero p r hp hr
  have hdpoly : d ≠ 0 := by
    intro h
    have : d.eval r = 0 := by simp [h]
    exact hd this
  have hreg := squarefree_sturmChain_regular p r hp
  have htailreg : SturmRegularAt r d c (p.natDegree + 1) := by
    have hstep :
        (¬ (p.eval r = 0 ∧ d.eval r = 0)) ∧
          SturmRegularAt r d c (p.natDegree + 1) := by
      simpa [SturmRegularAt, d, c, hdpoly, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
        using hreg
    exact hstep.2
  have htail := sturmAux_variation_locally_constant
      d c r (p.natDegree + 1) hd htailreg
  have hcross := simple_root_local_crossing_sign p r hr (by simpa [d] using hd)
  have hdsign := polynomial_eval_same_sign_locally d r hd
  have hdev := polynomial_eval_eventually_ne_zero d r hd
  let U : Set ℝ := {x |
    signChanges ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x)) =
      signChanges ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval r)) ∧
    ((x < r → p.eval x * p.derivative.eval r < 0) ∧
      (r < x → 0 < p.eval x * p.derivative.eval r)) ∧
    0 < d.eval x * d.eval r ∧ d.eval x ≠ 0}
  have hU : U ∈ 𝓝 r := by
    filter_upwards [htail, hcross, hdsign, hdev] with x hx1 hx2 hx3 hx4
    exact ⟨hx1, hx2, hx3, hx4⟩
  refine ⟨U, hU, ?_⟩
  intro x hx y hy hxr hry
  have hpxfix : p.eval x * d.eval r < 0 := by simpa [d] using hx.2.1.1 hxr
  have hpyfix : 0 < p.eval y * d.eval r := by simpa [d] using hy.2.1.2 hry
  have hpxd : p.eval x * d.eval x < 0 := by
    have hs := hx.2.2.1
    have hdr2 : 0 < d.eval r * d.eval r := mul_self_pos.mpr hd
    nlinarith [hpxfix, hs, hdr2]
  have hpyd : 0 < p.eval y * d.eval y := by
    have hs := hy.2.2.1
    have hdr2 : 0 < d.eval r * d.eval r := mul_self_pos.mpr hd
    nlinarith [hpyfix, hs, hdr2]
  have hpx : p.eval x ≠ 0 := by
    intro hz
    simp [hz] at hpxd
  have hpy : p.eval y ≠ 0 := by
    intro hz
    simp [hz] at hpyd
  have hchain : sturmAux p d (p.natDegree + 2) =
      p :: sturmAux d c (p.natDegree + 1) := by
    simp [sturmAux, d, c, hdpoly, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
  have hchain' : sturmAux p p.derivative (p.natDegree + 2) =
      p :: sturmAux d c (p.natDegree + 1) := by
    simpa [d] using hchain
  have htailShapeX :
      (sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x) =
        d.eval x :: ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x)).tail := by
    rw [sturmAux_eq_cons_tail d c (p.natDegree + 1)]
    rfl
  have htailShapeY :
      (sturmAux d c (p.natDegree + 1)).map (fun q => q.eval y) =
        d.eval y :: ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval y)).tail := by
    rw [sturmAux_eq_cons_tail d c (p.natDegree + 1)]
    rfl
  change signChanges ((sturmAux p p.derivative (p.natDegree + 2)).map (fun q => q.eval x)) =
    signChanges ((sturmAux p p.derivative (p.natDegree + 2)).map (fun q => q.eval y)) + 1
  rw [hchain']
  simp only [List.map_cons]
  rw [htailShapeX, htailShapeY]
  rw [signChanges_cons_cons_of_ne_zero _ _ _ hpx hx.2.2.2,
      signChanges_cons_cons_of_ne_zero _ _ _ hpy hy.2.2.2]
  have hleft : (if p.eval x * d.eval x < 0 then 1 else 0) = 1 := by simp [hpxd]
  have hright : (if p.eval y * d.eval y < 0 then 1 else 0) = 0 := by
    simp [not_lt.mpr (le_of_lt hpyd)]
  rw [hleft, hright]
  have htx := hx.1
  have hty := hy.1
  rw [htailShapeX] at htx
  rw [htailShapeY] at hty
  omega

/-- At a root itself the leading zero is ignored, so `sigma` equals the
variation of the recursive tail. -/
theorem squarefree_sigma_at_root_eq_tail
    (p : ℝ[X]) (r : ℝ) (hp : Squarefree p) (hr : p.eval r = 0) :
    let d : ℝ[X] := p.derivative
    let c : ℝ[X] := -(p % d)
    sigma p r = signChanges ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval r)) := by
  dsimp
  have hd : p.derivative.eval r ≠ 0 := squarefree_root_derivative_ne_zero p r hp hr
  have hdpoly : p.derivative ≠ 0 := by
    intro h
    have : p.derivative.eval r = 0 := by simp [h]
    exact hd this
  have hchain : sturmAux p p.derivative (p.natDegree + 2) =
      p :: sturmAux p.derivative (-(p % p.derivative)) (p.natDegree + 1) := by
    simp [sturmAux, hdpoly, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
  rw [sigma, sturmChain, hchain]
  simp only [List.map_cons, hr]
  simpa using signChanges_insert_zero ([] : List ℝ)
    ((sturmAux p.derivative (-(p % p.derivative)) (p.natDegree + 1)).map
      (fun q => q.eval r))

/-- Stronger one-point form of the root crossing law.  In one neighbourhood,
points to the left have one extra variation while the root itself and points
to the right have exactly the root variation. -/
theorem squarefree_sigma_local_root_profile
    (p : ℝ[X]) (r : ℝ) (hp : Squarefree p) (hr : p.eval r = 0) :
    ∃ U : Set ℝ, U ∈ 𝓝 r ∧ ∀ x ∈ U,
      (x < r → sigma p x = sigma p r + 1) ∧
      (r ≤ x → sigma p x = sigma p r) := by
  let d : ℝ[X] := p.derivative
  let c : ℝ[X] := -(p % d)
  have hd : d.eval r ≠ 0 := by
    simpa [d] using squarefree_root_derivative_ne_zero p r hp hr
  have hdpoly : d ≠ 0 := by
    intro h
    have : d.eval r = 0 := by simp [h]
    exact hd this
  have hreg := squarefree_sturmChain_regular p r hp
  have htailreg : SturmRegularAt r d c (p.natDegree + 1) := by
    have hstep :
        (¬ (p.eval r = 0 ∧ d.eval r = 0)) ∧
          SturmRegularAt r d c (p.natDegree + 1) := by
      simpa [SturmRegularAt, d, c, hdpoly, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
        using hreg
    exact hstep.2
  have htail := sturmAux_variation_locally_constant
      d c r (p.natDegree + 1) hd htailreg
  have hcross := simple_root_local_crossing_sign p r hr (by simpa [d] using hd)
  have hdsign := polynomial_eval_same_sign_locally d r hd
  have hdev := polynomial_eval_eventually_ne_zero d r hd
  let U : Set ℝ := {x |
    signChanges ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x)) =
      signChanges ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval r)) ∧
    ((x < r → p.eval x * p.derivative.eval r < 0) ∧
      (r < x → 0 < p.eval x * p.derivative.eval r)) ∧
    0 < d.eval x * d.eval r ∧ d.eval x ≠ 0}
  have hU : U ∈ 𝓝 r := by
    filter_upwards [htail, hcross, hdsign, hdev] with x hx1 hx2 hx3 hx4
    exact ⟨hx1, hx2, hx3, hx4⟩
  refine ⟨U, hU, ?_⟩
  intro x hx
  have hchain : sturmAux p d (p.natDegree + 2) =
      p :: sturmAux d c (p.natDegree + 1) := by
    simp [sturmAux, d, c, hdpoly, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
  have htailShapeX :
      (sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x) =
        d.eval x :: ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x)).tail := by
    rw [sturmAux_eq_cons_tail d c (p.natDegree + 1)]
    rfl
  have htailShapeR :
      (sturmAux d c (p.natDegree + 1)).map (fun q => q.eval r) =
        d.eval r :: ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval r)).tail := by
    rw [sturmAux_eq_cons_tail d c (p.natDegree + 1)]
    rfl
  have hroot : sigma p r =
      signChanges ((sturmAux d c (p.natDegree + 1)).map (fun q => q.eval r)) := by
    simpa [d, c] using squarefree_sigma_at_root_eq_tail p r hp hr
  constructor
  · intro hxr
    have hpxfix : p.eval x * d.eval r < 0 := by simpa [d] using hx.2.1.1 hxr
    have hpxd : p.eval x * d.eval x < 0 := by
      have hs := hx.2.2.1
      have hdr2 : 0 < d.eval r * d.eval r := mul_self_pos.mpr hd
      nlinarith [hpxfix, hs, hdr2]
    have hpx : p.eval x ≠ 0 := by
      intro hz
      simp [hz] at hpxd
    rw [sigma, sturmChain, hchain]
    simp only [List.map_cons]
    rw [htailShapeX]
    rw [signChanges_cons_cons_of_ne_zero _ _ _ hpx hx.2.2.2]
    simp [hpxd]
    have htx := hx.1
    rw [htailShapeX] at htx
    rw [hroot]
    omega
  · intro hrx
    rcases hrx.eq_or_lt with rfl | hrx
    · rfl
    · have hpyfix : 0 < p.eval x * d.eval r := by simpa [d] using hx.2.1.2 hrx
      have hpyd : 0 < p.eval x * d.eval x := by
        have hs := hx.2.2.1
        have hdr2 : 0 < d.eval r * d.eval r := mul_self_pos.mpr hd
        nlinarith [hpyfix, hs, hdr2]
      have hpx : p.eval x ≠ 0 := by
        intro hz
        simp [hz] at hpyd
      rw [sigma, sturmChain, hchain]
      simp only [List.map_cons]
      rw [htailShapeX]
      rw [signChanges_cons_cons_of_ne_zero _ _ _ hpx hx.2.2.2]
      have hn : ¬ p.eval x * d.eval x < 0 := not_lt.mpr (le_of_lt hpyd)
      simp [hn]
      have htx := hx.1
      rw [htailShapeX] at htx
      rw [hroot]
      exact htx

/-- Distinct real roots, forgetting multiplicity. -/
noncomputable def sturmRootFinset (p : ℝ[X]) : Finset ℝ := p.roots.toFinset

/-- Number of distinct real roots at or to the left of `x`. -/
noncomputable def sturmRootCountLE (p : ℝ[X]) (x : ℝ) : ℕ :=
  (sturmRootFinset p).filter (fun r => r ≤ x) |>.card

/-- Away from a member of a finite ordered set, the complete comparison
profile with that set is locally constant. -/
theorem finset_order_profile_eventually (S : Finset ℝ) (r : ℝ) (hr : r ∉ S) :
    ∀ᶠ x in 𝓝 r, ∀ z ∈ S, (z ≤ x ↔ z ≤ r) := by
  induction S using Finset.induction_on with
  | empty => simp
  | @insert z S hz ih =>
      have hrS : r ∉ S := by
        intro hrs
        exact hr (Finset.mem_insert_of_mem hrs)
      have hzr : z ≠ r := by
        intro h
        apply hr
        rw [← h]
        exact Finset.mem_insert_self z S
      have hzprof : ∀ᶠ x in 𝓝 r, (z ≤ x ↔ z ≤ r) := by
        rcases lt_or_gt_of_ne hzr with hlt | hgt
        · have hev : ∀ᶠ x in 𝓝 r, z < x := Ioi_mem_nhds hlt
          filter_upwards [hev] with x hx
          constructor <;> intro
          · exact le_of_lt hlt
          · exact le_of_lt hx
        · have hev : ∀ᶠ x in 𝓝 r, x < z := Iio_mem_nhds hgt
          filter_upwards [hev] with x hx
          have hnx : ¬ z ≤ x := not_le_of_gt hx
          have hnr : ¬ z ≤ r := not_le_of_gt hgt
          simp [hnx, hnr]
      filter_upwards [ih hrS, hzprof] with x hx hzx
      intro w hw
      rcases Finset.mem_insert.mp hw with rfl | hw
      · exact hzx
      · exact hx w hw

/-- Consequently the prefix count of a finite set is locally constant away
from the set. -/
theorem finset_countLE_eventually_eq_of_not_mem
    (S : Finset ℝ) (r : ℝ) (hr : r ∉ S) :
    ∀ᶠ x in 𝓝 r,
      (S.filter (fun z => z ≤ x)).card = (S.filter (fun z => z ≤ r)).card := by
  filter_upwards [finset_order_profile_eventually S r hr] with x hx
  have heq : S.filter (fun z => z ≤ x) = S.filter (fun z => z ≤ r) := by
    ext z
    by_cases hz : z ∈ S
    · simp [hz, hx z hz]
    · simp [hz]
  exact congrArg Finset.card heq

/-- At a member `r`, the finite prefix count has exactly the complementary
one-step profile needed to cancel the Sturm variation jump. -/
theorem finset_countLE_local_root_profile
    (S : Finset ℝ) (r : ℝ) (hr : r ∈ S) :
    ∃ U : Set ℝ, U ∈ 𝓝 r ∧ ∀ x ∈ U,
      (x < r → (S.filter (fun z => z ≤ x)).card + 1 =
        (S.filter (fun z => z ≤ r)).card) ∧
      (r ≤ x → (S.filter (fun z => z ≤ x)).card =
        (S.filter (fun z => z ≤ r)).card) := by
  let T := S.erase r
  have hrT : r ∉ T := by simp [T]
  let U : Set ℝ := {x | ∀ z ∈ T, (z ≤ x ↔ z ≤ r)}
  have hU : U ∈ 𝓝 r := finset_order_profile_eventually T r hrT
  refine ⟨U, hU, ?_⟩
  intro x hx
  have hT : T.filter (fun z => z ≤ x) = T.filter (fun z => z ≤ r) := by
    ext z
    by_cases hz : z ∈ T
    · simp [hz, hx z hz]
    · simp [hz]
  have hS : S = insert r T := by
    simpa [T] using (Finset.insert_erase hr).symm
  constructor
  · intro hxr
    rw [hS]
    have hrnot : ¬ r ≤ x := not_le_of_gt hxr
    simp [Finset.filter_insert, hrnot, hT, hrT]
  · intro hrx
    rw [hS]
    simp [Finset.filter_insert, hrx, hT, hrT]

/-- The polynomial root prefix count is locally constant at every nonroot. -/
theorem sturmRootCountLE_locally_constant_at_nonroot
    (p : ℝ[X]) (r : ℝ) (hp0 : p ≠ 0) (hr : p.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r, sturmRootCountLE p x = sturmRootCountLE p r := by
  have hrmem : r ∉ sturmRootFinset p := by
    intro hmem
    have hroot : IsRoot p r := by
      exact (Polynomial.mem_roots hp0).1 (by simpa [sturmRootFinset] using hmem)
    exact hr (by simpa [Polynomial.IsRoot.def] using hroot)
  simpa [sturmRootCountLE] using
    finset_countLE_eventually_eq_of_not_mem (sturmRootFinset p) r hrmem

/-- At an actual root, the polynomial root-prefix count has the one-step
profile complementary to `sigma`. -/
theorem sturmRootCountLE_local_root_profile
    (p : ℝ[X]) (r : ℝ) (hp0 : p ≠ 0) (hr : p.eval r = 0) :
    ∃ U : Set ℝ, U ∈ 𝓝 r ∧ ∀ x ∈ U,
      (x < r → sturmRootCountLE p x + 1 = sturmRootCountLE p r) ∧
      (r ≤ x → sturmRootCountLE p x = sturmRootCountLE p r) := by
  have hrmem : r ∈ sturmRootFinset p := by
    have hroot : IsRoot p r := by simpa [Polynomial.IsRoot.def] using hr
    have : r ∈ p.roots := (Polynomial.mem_roots hp0).2 hroot
    simpa [sturmRootFinset] using this
  simpa [sturmRootCountLE] using
    finset_countLE_local_root_profile (sturmRootFinset p) r hrmem