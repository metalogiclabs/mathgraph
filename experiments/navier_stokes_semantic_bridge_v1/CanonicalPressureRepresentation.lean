import PressureGaussianLimit

/-!
V12: a proof-carrying representation interface for canonical weighted pressure.

Uses upstream *actual* weighted-pressure distribution identification plus the
newly kernel checked V11 strong Gaussian L² limit.

A witness of a UNIFORM (all Gaussian scales) L² bound is transported to an
actual L² canonical pressure representative of that distribution. The
assumption is NOT silently inferred from source B_R or from the natural
language paper. Separate physical pressure-gradient identification and
the original (10.19) claim remain UNKNOWN.

Source: OpenAI NavierStokesAndEuler@f9e8bc5... (Apache 2.0) and V11.
-/

noncomputable section

namespace MathGraph.CanonicalPressureRepresentation

open Set Filter MeasureTheory TemperedDistribution
open NavierStokes.ProblemStatement
open NavierStokes.R3PressureCommutator (Cutoff weightedNorm)
open NavierStokes.R3PressureCutoff
open NavierStokes.R3PressureFourier
open MathGraph.PressureGaussianLimit
open scoped Topology ENNReal SchwartzMap

/-- Convergence not just of the L² vector, but also of its actual
    tempered-distribution representation to the *canonical* weighted
    pressure distribution defined by OpenAI's Riesz multiplier. -/
theorem gaussian_tendsto_canonical_pressure_distribution
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (hφg : φ.HasTemperateGrowth) (i j : Fin 3)
    (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2) :
    Tendsto
      (fun n : ℕ =>
        (regularizedWeightedPressure hφ n i j g hw hg₂ : 𝓢'(Space, ℂ)))
      atTop
      (𝓝 (smulLeftCLM ℂ (powerCutoff φ) (pressureL1 i j g))) := by
  have hlim :=
    ((Lp.toTemperedDistributionCLM ℂ (volume : Measure Space) 2).continuous.tendsto
      (weightedPressure hφ i j g hw hg₂)).comp
        (regularized_weighted_pressure_tendsto hφ i j g hw hg₂)
  have hid := weightedPressure_distribution hφ hφg i j g hw hg₂
  simpa only [Function.comp_def, hid] using hlim

/-- Proof-carrying canonical cutoff pressure admission: uniform finite
    Gaussian bounds + verified distribution identification yield a bounded
    actual L² representative. The physical pressure pairing is a distinct
    observation not covered by this record. -/
theorem gaussian_bound_gives_canonical_L2_representative
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (hφg : φ.HasTemperateGrowth) (i j : Fin 3)
    (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    {C : ℝ}
    (hb : ∀ n : ℕ, ‖regularizedWeightedPressure hφ n i j g hw hg₂‖ ≤ C) :
    ∃ F : Lp ℂ 2 (volume : Measure Space),
      smulLeftCLM ℂ (powerCutoff φ) (pressureL1 i j g) =
        (F : 𝓢'(Space, ℂ)) ∧ ‖F‖ ≤ C := by
  refine ⟨weightedPressure hφ i j g hw hg₂, ?_, ?_⟩
  · exact weightedPressure_distribution hφ hφg i j g hw hg₂
  · exact bound_passes_to_actual_weighted_pressure hφ i j g hw hg₂ hb

end MathGraph.CanonicalPressureRepresentation

#print axioms MathGraph.CanonicalPressureRepresentation.gaussian_tendsto_canonical_pressure_distribution
#print axioms MathGraph.CanonicalPressureRepresentation.gaussian_bound_gives_canonical_L2_representative
