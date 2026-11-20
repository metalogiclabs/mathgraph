import Mathlib

/-!
# RH definition bridge: independent Dirichlet-series specification

Source boundary: Lean 4.33.1, Mathlib at
0df444a360eaa60ab8c11dca51a86af692955474.

The predicate `IsClassicalZeta` does not mention `riemannZeta` or
`RiemannHypothesis`: it defines zeta extensionally by its Dirichlet
series on Re(s)>1 and analyticity on C\\{1}.  The proof of uniqueness
uses the identity theorem.  The theorem checked here does **not**
prove RH; it proves equivalence of the independently stated RH and
Mathlib's RH.
-/


open Complex Filter Set

namespace RHBridge

/-- The classical Dirichlet series on its half-plane of convergence. -/
noncomputable def zetaSeries (s : ℂ) : ℂ :=
  ∑' n : ℕ, 1 / (n + 1 : ℂ) ^ s

/-- An independent semantic specification for a zeta continuation.
Any two such functions agree outside the pole, by analytic uniqueness. -/
def IsClassicalZeta (f : ℂ → ℂ) : Prop :=
  AnalyticOnNhd ℂ f ({1}ᶜ : Set ℂ) ∧
    ∀ s : ℂ, 1 < s.re → f s = zetaSeries s

/-- A specification of RH which does not reference Mathlib's
`riemannZeta` or `RiemannHypothesis`. -/
def IndependentRH : Prop :=
  ∀ (f : ℂ → ℂ), IsClassicalZeta f →
    ∀ s : ℂ, f s = 0 →
      (¬∃ n : ℕ, s = -2 * (n + 1 : ℂ)) → s ≠ 1 → s.re = 1 / 2

/-- The independently specified function class includes Mathlib zeta. -/
theorem mathlibZetaFits : IsClassicalZeta riemannZeta := by
  constructor
  · exact analyticOn_riemannZeta
  · intro s hs
    exact zeta_eq_tsum_one_div_nat_add_one_cpow hs

/-- Any analytic continuation agreeing with the classical Dirichlet
series agrees with Mathlib zeta away from its pole. -/
theorem zetaUnique {f : ℂ → ℂ} (hf : IsClassicalZeta f)
    {s : ℂ} (hs : s ≠ 1) : f s = riemannZeta s := by
  have hpc : IsPreconnected ({1}ᶜ : Set ℂ) :=
    (isConnected_compl_singleton_of_one_lt_rank
      (rank_real_complex ▸ Nat.one_lt_ofNat) _).isPreconnected
  have htwo : (2 : ℂ) ∈ ({1}ᶜ : Set ℂ) := by simp
  refine AnalyticOnNhd.eqOn_of_preconnected_of_eventuallyEq
    (𝕜 := ℂ) hf.1 analyticOn_riemannZeta hpc htwo ?_ hs
  refine eventually_of_mem
    ((continuous_re.isOpen_preimage _ isOpen_Ioi).mem_nhds
      (by simp : 1 < (2 : ℂ).re)) ?_
  intro t ht
  exact (hf.2 t ht).trans (zeta_eq_tsum_one_div_nat_add_one_cpow ht).symm

/-- The classical Dirichlet-series/analytic-continuation version of RH
is equivalent to the exact Mathlib headline statement. -/
theorem independentRHIffMathlib : IndependentRH ↔ RiemannHypothesis := by
  constructor
  · intro h s hz htriv hpole
    exact h riemannZeta mathlibZetaFits s hz htriv hpole
  · intro h f hf s hz htriv hpole
    have heq : f s = riemannZeta s := zetaUnique hf hpole
    exact h s (heq.symm.trans hz) htriv hpole

#print axioms RHBridge.mathlibZetaFits
#print axioms RHBridge.zetaUnique
#print axioms RHBridge.independentRHIffMathlib

end RHBridge
