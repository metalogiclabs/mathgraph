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
    exact Filter.inter_mem (Filter.inter_mem (Filter.inter_mem htail hcross) hdsign) hdev
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
  have htailShapeX :
      (sturmAux d c (p.natDegree + 1)).map (fun q => q.eval x) =
        d.eval x :: (sturmAux d c (p.natDegree + 1)).tail.map (fun q => q.eval x) := by
    rw [sturmAux_eq_cons_tail d c (p.natDegree + 1)]
    rfl
  have htailShapeY :
      (sturmAux d c (p.natDegree + 1)).map (fun q => q.eval y) =
        d.eval y :: (sturmAux d c (p.natDegree + 1)).tail.map (fun q => q.eval y) := by
    rw [sturmAux_eq_cons_tail d c (p.natDegree + 1)]
    rfl
  rw [sigma, sturmChain, hchain]
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
