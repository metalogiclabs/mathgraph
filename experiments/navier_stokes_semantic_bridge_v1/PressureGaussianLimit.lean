import NavierStokes.R3PressureCutoff

/-!
# V11: certified Gaussian-to-true weighted pressure limit

The original OpenAI pressure development contains, separately:
1. convergence in L² of the Gaussian-regularized Riesz operator, and
2. convergence in L² of its weighted cutoff commutator.

This file composes those two proved statements at the actual *weighted*
pressure interface, and proves sound passage of a UNIFORM numerical
bound to the limit. This is not the physical Navier-Stokes
PressureRecovery pressurePair interface. A separate authority bridge is
needed before promoting any physical pressure-flux or manuscript claim.

No extra axiom, fixed polynomial energy estimate, or semantic signoff.
-/

noncomputable section

namespace MathGraph.PressureGaussianLimit

open Set Filter MeasureTheory
open NavierStokes.ProblemStatement
open NavierStokes.R3PressureFourier
open NavierStokes.R3PressureCommutator (Cutoff weightedNorm)
open NavierStokes.R3PressureCutoff
open NavierStokes.R3RieszApproximation
open scoped Topology ENNReal

/-- Strong L² limit of the actual Gaussian-regularized weighted Riesz
component, using only the two previously verified upstream strong limits. -/
theorem regularized_weighted_pressure_tendsto
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (i j : Fin 3) (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2) :
    Tendsto (fun n => regularizedWeightedPressure hφ n i j g hw hg₂)
      atTop (𝓝 (weightedPressure hφ i j g hw hg₂)) := by
  change Tendsto
    (fun n => operatorL2 n i j (hg₂.toLp (fun x => powerCutoff φ x * g x)) +
      regularizedCommutatorLp hφ n i j g hw)
    atTop (𝓝 (pressureL2 i j (hg₂.toLp (fun x => powerCutoff φ x * g x)) +
      commutatorLp hφ i j g hw))
  exact (operatorL2_tendsto i j (hg₂.toLp (fun x => powerCutoff φ x * g x))).add
    (regularizedCommutatorLp_tendsto hφ i j g hw)

/-- A uniform bound of ALL Gaussian scales passes to the genuine weighted
L² pressure. This does not manufacture the bound; it needs a proof at all n. -/
theorem bound_passes_to_actual_weighted_pressure
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (i j : Fin 3) (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    {C : ℝ}
    (hb : ∀ n : ℕ, ‖regularizedWeightedPressure hφ n i j g hw hg₂‖ ≤ C) :
    ‖weightedPressure hφ i j g hw hg₂‖ ≤ C := by
  have ht :
      Tendsto (fun n => ‖regularizedWeightedPressure hφ n i j g hw hg₂‖)
        atTop (𝓝 ‖weightedPressure hφ i j g hw hg₂‖) :=
    (continuous_norm.tendsto _).comp
      (regularized_weighted_pressure_tendsto hφ i j g hw hg₂)
  exact le_of_tendsto ht (Filter.Eventually.of_forall hb)

end MathGraph.PressureGaussianLimit

#print axioms MathGraph.PressureGaussianLimit.regularized_weighted_pressure_tendsto
#print axioms MathGraph.PressureGaussianLimit.bound_passes_to_actual_weighted_pressure
