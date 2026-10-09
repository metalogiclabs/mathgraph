import PressureGaussianLimit
import NavierStokes.R3PressureFlux

/-!
V15: Gaussian-regularized pressure *integral pairing* limit.

The existing V11/V12 results transport L² *norm* bounds. The alternate
source pathway of R3StressPressureEstimate proves scalar pairwise bounds
for an L² test factor, which are strictly weaker than a uniform operator
L² bound. This module proves that the corresponding canonical weighted
pressure scalar pairing inherits any uniform all-scale scalar bound.

The pressure operator is the REAL upstream R3PressureCutoff definition.
This does NOT by itself identify the old pressure Fourier distribution
with R3/Comparison.pressurePair, and does not prove the manuscript's (10.19).
-/

noncomputable section

namespace MathGraph.PressureScalarPairingLimit

open Set Filter MeasureTheory
open NavierStokes.ProblemStatement
open NavierStokes.R3PressureCommutator (Cutoff weightedNorm)
open NavierStokes.R3PressureCutoff
open NavierStokes.R3RieszApproximation
open MathGraph.PressureGaussianLimit
open scoped Topology ENNReal

noncomputable def l2Pair
    (h : Lp ℂ 2 (volume : Measure Space)) :
    Lp ℂ 2 (volume : Measure Space) →L[ℂ] ℂ :=
  (((lsmul ℂ ℂ (E := ℂ)).flip.lpPairing (volume : Measure Space) 2 2).flip h)

/-- The continuous L²-L² complex bilinear pairing is exactly the scalar
integral, with multiplication in the usual order. -/
theorem l2Pair_eq_integral
    (F h : Lp ℂ 2 (volume : Measure Space)) :
    l2Pair h F = ∫ x : Space, F x * h x := by
  change ((lsmul ℂ ℂ (E := ℂ)).flip.lpPairing (volume : Measure Space) 2 2) F h = _
  rw [ContinuousLinearMap.lpPairing_eq_integral]
  change (∫ x : Space, h x * F x) = (∫ x : Space, F x * h x)
  simp only [mul_comm]

/-- Strong L² convergence gives convergence of the ACTUAL weighted
canonical pressure paired with any fixed L² test. -/
theorem gaussian_l2_pair_tendsto
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (i j : Fin 3) (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    (h : Lp ℂ 2 (volume : Measure Space)) :
    Tendsto
      (fun n : ℕ => l2Pair h (regularizedWeightedPressure hφ n i j g hw hg₂))
      atTop (𝓝 (l2Pair h (weightedPressure hφ i j g hw hg₂))) := by
  exact (l2Pair h).continuous.tendsto
    (weightedPressure hφ i j g hw hg₂) |>.comp
      (regularized_weighted_pressure_tendsto hφ i j g hw hg₂)

/-- The test pairing against a Gaussian-weighted pressure equals the
actual integral of the pointwise Gaussian pressure with the cutoff factor. -/
theorem gaussian_pair_eq_actual_integral
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (hφg : φ.HasTemperateGrowth) (n : ℕ) (i j : Fin 3)
    (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    (h : Space → ℂ) (hh : MemLp h 2 volume) :
    l2Pair (hh.toLp h) (regularizedWeightedPressure hφ n i j g hw hg₂) =
      ∫ x : Space, powerCutoff φ x * regularized n i j g x * h x := by
  rw [l2Pair_eq_integral]
  apply integral_congr_ae
  filter_upwards [regularizedWeightedPressure_ae hφ hφg n i j g hw hg₂,
    hh.coeFn_toLp] with x hpressure htest
  simp only [hpressure, htest]

theorem canonical_pair_eq_actual_integral
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (i j : Fin 3) (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    (h : Space → ℂ) (hh : MemLp h 2 volume) :
    l2Pair (hh.toLp h) (weightedPressure hφ i j g hw hg₂) =
      ∫ x : Space, (weightedPressure hφ i j g hw hg₂ : Space → ℂ) x * h x := by
  rw [l2Pair_eq_integral]
  apply integral_congr_ae
  filter_upwards [hh.coeFn_toLp] with x htest
  simp only [htest]

/-- A uniform bound on the actual finite-scale Gaussian integral passes
to the canonical weighted Riesz pressure integral. No uniform L² *norm*
estimate is needed: only the bound on this particular L² test pairing. -/
theorem uniform_gaussian_flux_pairing_bound_passes_to_canonical
    {R L : ℝ} {φ : Space → ℝ} (hφ : Cutoff R L φ)
    (hφg : φ.HasTemperateGrowth) (i j : Fin 3)
    (g : Lp ℂ 1 (volume : Measure Space))
    (hw : MemLp (weightedNorm φ g) (3 / 2))
    (hg₂ : MemLp (fun x => powerCutoff φ x * g x) 2)
    (h : Space → ℂ) (hh : MemLp h 2 volume) {C : ℝ}
    (hb : ∀ n : ℕ,
      ‖∫ x : Space, powerCutoff φ x * regularized n i j g x * h x‖ ≤ C) :
    ‖∫ x : Space,
        (weightedPressure hφ i j g hw hg₂ : Space → ℂ) x * h x‖ ≤ C := by
  have hbPair (n : ℕ) :
      ‖l2Pair (hh.toLp h) (regularizedWeightedPressure hφ n i j g hw hg₂)‖ ≤ C := by
    rw [gaussian_pair_eq_actual_integral hφ hφg n i j g hw hg₂ h hh]
    exact hb n
  have hlim := gaussian_l2_pair_tendsto hφ i j g hw hg₂ (hh.toLp h)
  have ht :
      Tendsto
        (fun n => ‖l2Pair (hh.toLp h)
          (regularizedWeightedPressure hφ n i j g hw hg₂)‖)
        atTop (𝓝 ‖l2Pair (hh.toLp h) (weightedPressure hφ i j g hw hg₂)‖) :=
    (continuous_norm.tendsto _).comp hlim
  have hbound : ‖l2Pair (hh.toLp h) (weightedPressure hφ i j g hw hg₂)‖ ≤ C :=
    le_of_tendsto ht (Filter.Eventually.of_forall hbPair)
  simpa only [canonical_pair_eq_actual_integral hφ i j g hw hg₂ h hh] using hbound

end MathGraph.PressureScalarPairingLimit

#print axioms MathGraph.PressureScalarPairingLimit.l2Pair_eq_integral
#print axioms MathGraph.PressureScalarPairingLimit.gaussian_l2_pair_tendsto
#print axioms MathGraph.PressureScalarPairingLimit.gaussian_pair_eq_actual_integral
#print axioms MathGraph.PressureScalarPairingLimit.canonical_pair_eq_actual_integral
#print axioms MathGraph.PressureScalarPairingLimit.uniform_gaussian_flux_pairing_bound_passes_to_canonical
