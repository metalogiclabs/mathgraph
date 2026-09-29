import PFR.ForMathlib.FiniteRange.Defs
import Definitions.Def_RepTheory_TestFunctionAction

open MeasureTheory

/-- Canonical semantic waist for PFR's project-local finite-range wrapper. -/
theorem crystal_finiteRange_iff_range_finite {Ω G : Type*} (X : Ω → G) :
    FiniteRange X ↔ (Set.range X).Finite := by
  constructor
  · intro h
    exact h.finite
  · intro h
    exact ⟨h⟩

/-- A theorem stated with PFR's project-local wrapper is consumable by
Anthropic's independently written API, whose premise is the canonical
`(Set.range F).Finite` proposition. -/
theorem pfr_finiteRange_consumed_by_anthropic
    (𝕜 : Type*) [CommRing 𝕜] [Algebra ℝ 𝕜]
    {X : Type*} [MeasurableSpace X]
    {V : Type*} [AddCommGroup V] [Module 𝕜 V]
    (μ : Measure X) {F : X → V} [hF : FiniteRange F] :
    ∃ h : (Set.range F).Finite,
      TestFunctionAction.finiteRangeIntegral 𝕜 μ F =
        ∑ w ∈ h.toFinset,
          TestFunctionAction.measureCoeff 𝕜 μ (F ⁻¹' {w}) • w := by
  let h : (Set.range F).Finite := hF.finite
  exact ⟨h, TestFunctionAction.finiteRangeIntegral_of_finite 𝕜 μ h⟩

/-- Concrete inherited PFR capability: constant functions acquire PFR's
`FiniteRange` instance and cross the same bridge without restating finiteness. -/
theorem pfr_constant_consumed_by_anthropic
    (𝕜 : Type*) [CommRing 𝕜] [Algebra ℝ 𝕜]
    {X : Type*} [MeasurableSpace X]
    {V : Type*} [AddCommGroup V] [Module 𝕜 V]
    (μ : Measure X) (c : V) :
    ∃ h : (Set.range (fun _ : X => c)).Finite,
      TestFunctionAction.finiteRangeIntegral 𝕜 μ (fun _ : X => c) =
        ∑ w ∈ h.toFinset,
          TestFunctionAction.measureCoeff 𝕜 μ ((fun _ : X => c) ⁻¹' {w}) • w := by
  letI : FiniteRange (fun _ : X => c) := inferInstance
  exact pfr_finiteRange_consumed_by_anthropic 𝕜 μ
