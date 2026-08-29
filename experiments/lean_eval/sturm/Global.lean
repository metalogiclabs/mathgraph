import ChallengeDeps
import TailComposition
import SigmaLocal
import Termination
import Final
import Mathlib.Topology.LocallyConstant.Basic

open LeanEval.Algebra
open Polynomial
open Set Filter
open scoped Classical Topology

/-- The compensated Sturm quantity: sign variation plus the number of distinct
real roots already crossed.  Its local jumps cancel exactly. -/
noncomputable def sturmCompensated (p : ℝ[X]) (x : ℝ) : ℕ :=
  sigma p x + sturmRootCountLE p x

/-- For a nonzero squarefree polynomial, the compensated quantity is locally
constant at every real point, including roots. -/
theorem squarefree_sturmCompensated_isLocallyConstant
    (p : ℝ[X]) (hp : Squarefree p) (hp0 : p ≠ 0) :
    IsLocallyConstant (sturmCompensated p) := by
  rw [IsLocallyConstant.iff_eventually_eq]
  intro r
  by_cases hr : p.eval r = 0
  · rcases squarefree_sigma_local_root_profile p r hp hr with ⟨U, hU, hsig⟩
    rcases sturmRootCountLE_local_root_profile p r hp0 hr with ⟨V, hV, hcnt⟩
    filter_upwards [hU, hV] with x hxU hxV
    unfold sturmCompensated
    by_cases hxr : x < r
    · have hs := (hsig x hxU).1 hxr
      have hc := (hcnt x hxV).1 hxr
      omega
    · have hrx : r ≤ x := le_of_not_gt hxr
      rw [(hsig x hxU).2 hrx, (hcnt x hxV).2 hrx]
  · have hsig := squarefree_sigma_locally_constant_at_nonroot p r hp hr
    have hcnt := sturmRootCountLE_locally_constant_at_nonroot p r hp0 hr
    filter_upwards [hsig, hcnt] with x hs hc
    simp [sturmCompensated, hs, hc]

/-- Therefore the compensated quantity is globally constant on the real
line, by connectedness. -/
theorem squarefree_sturmCompensated_eq
    (p : ℝ[X]) (hp : Squarefree p) (hp0 : p ≠ 0) (a b : ℝ) :
    sturmCompensated p a = sturmCompensated p b := by
  exact (squarefree_sturmCompensated_isLocallyConstant p hp hp0)
    .apply_eq_of_preconnectedSpace a b
