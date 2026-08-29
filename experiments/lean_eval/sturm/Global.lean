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

/-- Distinct roots strictly inside an interval, represented structurally as a
finset. -/
noncomputable def sturmRootFinsetIoo (p : ℝ[X]) (a b : ℝ) : Finset ℝ :=
  (sturmRootFinset p).filter (fun r => a < r ∧ r < b)

/-- The benchmark set of interval roots has exactly the cardinality of the
structural root finset. -/
theorem interval_root_ncard_eq_finset_card
    (p : ℝ[X]) (a b : ℝ) (hp0 : p ≠ 0) :
    {x : ℝ | a < x ∧ x < b ∧ p.eval x = 0}.ncard =
      (sturmRootFinsetIoo p a b).card := by
  have hset :
      {x : ℝ | a < x ∧ x < b ∧ p.eval x = 0} =
        (↑(sturmRootFinsetIoo p a b) : Set ℝ) := by
    ext x
    simp only [Set.mem_setOf_eq, Set.mem_setOf_eq, Finset.mem_coe,
      sturmRootFinsetIoo, Finset.mem_filter, sturmRootFinset,
      Multiset.mem_toFinset]
    rw [Polynomial.mem_roots hp0]
    simp [Polynomial.IsRoot.def, and_left_comm, and_assoc, and_comm]
  rw [hset]
  exact Set.ncard_coe_finset _

/-- Prefix root counts differ by exactly the number of roots in `(a,b)` when
both endpoints are nonroots. -/
theorem sturmRootCountLE_sub_eq_interval_card
    (p : ℝ[X]) (a b : ℝ) (hp0 : p ≠ 0)
    (ha : p.eval a ≠ 0) (hb : p.eval b ≠ 0) (hab : a < b) :
    sturmRootCountLE p b - sturmRootCountLE p a =
      (sturmRootFinsetIoo p a b).card := by
  let S := sturmRootFinset p
  let A := S.filter (fun r => r ≤ a)
  let B := S.filter (fun r => r ≤ b)
  have hsub : A ⊆ B := by
    intro r hrA
    have hra : r ≤ a := (Finset.mem_filter.mp hrA).2
    have hrS : r ∈ S := (Finset.mem_filter.mp hrA).1
    exact Finset.mem_filter.mpr ⟨hrS, hra.trans hab.le⟩
  have hdiff : B \ A = sturmRootFinsetIoo p a b := by
    ext r
    simp only [Finset.mem_sdiff, Finset.mem_filter, A, B, S, sturmRootFinsetIoo]
    constructor
    · rintro ⟨⟨hrS, hrb⟩, hnotA⟩
      have hna : ¬ r ≤ a := by
        intro hra
        exact hnotA ⟨hrS, hra⟩
      have har : a < r := lt_of_not_ge hna
      have hrb' : r < b := by
        rcases hrb.eq_or_lt with rfl | hlt
        · have hroot : IsRoot p b := (Polynomial.mem_roots hp0).1 (by
            simpa [sturmRootFinset] using hrS)
          exact (hb (by simpa [Polynomial.IsRoot.def] using hroot)).elim
        · exact hlt
      exact ⟨hrS, har, hrb'⟩
    · rintro ⟨hrS, har, hrb⟩
      refine ⟨⟨hrS, hrb.le⟩, ?_⟩
      intro hA
      exact (not_le_of_gt har) hA.2
  have hcard := Finset.card_sdiff hsub
  rw [hdiff] at hcard
  simpa [sturmRootCountLE, A, B, S] using hcard

/-- Final assembly: the compensated invariant converts its global constancy
into the exact interval root count. -/
theorem sturm_final
    (p : ℝ[X]) (a b : ℝ)
    (hp : Squarefree p)
    (ha : p.eval a ≠ 0)
    (hb : p.eval b ≠ 0)
    (hab : a < b) :
    {x : ℝ | a < x ∧ x < b ∧ p.eval x = 0}.ncard = sigma p a - sigma p b := by
  have hp0 : p ≠ 0 := by
    intro h
    apply ha
    simp [h]
  have hglobal := squarefree_sturmCompensated_eq p hp hp0 a b
  have hcount := sturmRootCountLE_sub_eq_interval_card p a b hp0 ha hb hab
  have hset := interval_root_ncard_eq_finset_card p a b hp0
  unfold sturmCompensated at hglobal
  omega
