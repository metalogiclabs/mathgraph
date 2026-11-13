import PressureScalarPairingLimit
import NavierStokes.R3PressureFlux

/-!
V16: actual quantitative canonical weighted-pressure pairing estimate.

V15 proved exact passage of each uniform Gaussian scalar integral estimate
to the canonical weighted-pressure test integral. The source-pinned OpenAI
R3PressureFlux.regularized_flux_le theorem *already supplies* a fixed
uniform in n estimate for that exact finite-scale integral.

This composition therefore produces a numerical bound for the genuine
canonical weighted pressure pairing without introducing any new premise
about regularization-scale boundedness.

The required hypotheses remain exactly the upstream cutoff, temperate
growth, and L¹/L^(3/2)/L² stress and L² test integrability conditions.
This theorem is NOT the physical comparison pressurePair identity and
does NOT prove source manuscript equation (10.19).
-/

noncomputable section

namespace MathGraph.QuantitativeCanonicalPressure

open Set Filter MeasureTheory
open NavierStokes.ProblemStatement
open NavierStokes.R3PressureCommutator (Cutoff weightedNorm)
open NavierStokes.R3PressureCutoff
open MathGraph.PressureScalarPairingLimit
open scoped Topology ENNReal

/-- The original Gaussian pressure estimate now becomes an estimate of
the actual canonical weighted Riesz pressure's integral against ANY fixed
L² test, under precisely the original integrability premises. -/
theorem canonical_weighted_pressure_integral_bound
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (hφg : φ.HasTemperateGrowth)
    (i j : Fin 3) (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    (h : Space → ℂ) (hh : MemLp h 2 volume) :
    ‖∫ x : Space,
       (weightedPressure hφ i j g hw hg₂ : Space → ℂ) x * h x‖ ≤
      (MeasureTheory.lpNorm
         (fun x => powerCutoff φ x * g x) 2 volume +
        NavierStokes.R3PressureCutoff.errorBound R L φ g) *
        MeasureTheory.lpNorm h 2 volume := by
  apply uniform_gaussian_flux_pairing_bound_passes_to_canonical
    hφ hφg i j g hw hg₂ h hh
  intro n
  exact NavierStokes.R3PressureFlux.regularized_flux_le
    hφ hφg n i j (Lp.memLp g) hw hg₂ hh

end MathGraph.QuantitativeCanonicalPressure

#print axioms MathGraph.QuantitativeCanonicalPressure.canonical_weighted_pressure_integral_bound
