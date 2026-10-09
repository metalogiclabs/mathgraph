import PressureScalarPairingLimit
import NavierStokes.R3StressPressureEstimate

/-!
V17: real B-dependent canonical weighted-pressure bound from the original
source-pinned Gaussian stress estimate.

This imports BOTH the V15 verified L² scalar pairing limit and OpenAI's
existing R3StressPressureEstimate.regularized_flux_bound. The latter
proves an index-independent Gaussian integral bound. Hence the limit
is now quantitative for the same actual canonical weighted pressure.

All original upstream prerequisites are RETAINED: in particular U
must belong to L², L⁶ and L∞, W to L², and fourthWeight φ W to L⁶,
with explicit pointwise stress domination, measurable representatives,
and the test-factor L² bound.

This theorem concerns the *legacy* canonical weighted Fourier pressure,
NOT the active physical R3/Comparison.pressurePair; source equation
(10.19) remains unverified and may have different assumptions and B
exponents. The additive +1 in the polynomial bound is explicitly
retained (it does not reproduce the source's vanishing B=0 formula).
-/

noncomputable section

namespace MathGraph.LegacyCanonicalPressure

open Set Filter MeasureTheory
open NavierStokes.ProblemStatement
open NavierStokes.R3PressureCommutator (Cutoff weightedNorm)
open NavierStokes.R3PressureCutoff
open MathGraph.PressureScalarPairingLimit
open scoped ENNReal Topology

/-- Real quantitative canonical weighted Riesz pressure bound from
OpenAI's already proved Gaussian stress bound, with no new uniform
Gaussian estimate assumed. -/
theorem legacy_canonical_weighted_stress_bound
    {R L : ℝ} {φ U W : Space → ℝ}
    (hφ : Cutoff R L φ) (hφg : φ.HasTemperateGrowth)
    (hWm : Measurable W) (hU0 : ∀ x, 0 ≤ U x) (hW0 : ∀ x, 0 ≤ W x)
    (hU₂ : MemLp U 2) (hU₆ : MemLp U 6) (hUi : MemLp U ⊤)
    (hW₂ : MemLp W 2)
    (hB₆ : MemLp (NavierStokes.R3WeightedLp.fourthWeight φ W) 6)
    (g : Lp ℂ 1 (volume : Measure Space))
    (hgm : Measurable (g : Space → ℂ))
    (hbound : ∀ x, ‖(g : Space → ℂ) x‖ ≤ W x ^ 2 + 2 * (U x * W x))
    (h : Space → ℂ) (hh : MemLp h 2)
    {M V B : ℝ}
    (hM : 0 ≤ M) (hV : 0 ≤ V) (hB : 0 ≤ B)
    (bW : MeasureTheory.lpNorm W 2 volume ≤ M)
    (bU₂ : MeasureTheory.lpNorm U 2 volume ≤ V)
    (bU₆ : MeasureTheory.lpNorm U 6 volume ≤ V)
    (bUi : MeasureTheory.lpNorm U ⊤ volume ≤ V)
    (bB : MeasureTheory.lpNorm
      (NavierStokes.R3WeightedLp.fourthWeight φ W) 6 volume ≤ B)
    (bh : MeasureTheory.lpNorm h 2 volume ≤ 8 * L / R * M)
    (i j : Fin 3) :
    ‖∫ x : Space,
        (weightedPressure hφ i j g
          (NavierStokes.R3WeightedLp.stress_weight_five hφ hWm hgm
            hU0 hW0 hU₆ hW₂ hB₆ hbound).1
          (NavierStokes.R3WeightedLp.stress_weight_six hφ hWm hgm
            hU0 hW0 hUi hW₂ hB₆ hbound).1 : Space → ℂ) x * h x‖ ≤
        NavierStokes.R3StressPressureEstimate.rawBound R L M V B := by
  have hw := (NavierStokes.R3WeightedLp.stress_weight_five
    hφ hWm hgm hU0 hW0 hU₆ hW₂ hB₆ hbound).1
  have hg₂ := (NavierStokes.R3WeightedLp.stress_weight_six
    hφ hWm hgm hU0 hW0 hUi hW₂ hB₆ hbound).1
  apply uniform_gaussian_flux_pairing_bound_passes_to_canonical
    hφ hφg i j g hw hg₂ h hh
  intro n
  exact NavierStokes.R3StressPressureEstimate.regularized_flux_bound
    hφ hφg hWm hgm hU0 hW0 hU₂ hU₆ hUi hW₂ hB₆ hh
    hbound hM hV hB bW bU₂ bU₆ bUi bB bh n i j

/-- Upstream radius/energy simplification: same quantitative actual
legacy pressure but only polynomial dependence on B (plus one). -/
theorem legacy_canonical_weighted_polynomial_bound
    {R L : ℝ} {φ U W : Space → ℝ}
    (hφ : Cutoff R L φ) (hφg : φ.HasTemperateGrowth)
    (hR : 1 ≤ R)
    (hWm : Measurable W) (hU0 : ∀ x, 0 ≤ U x) (hW0 : ∀ x, 0 ≤ W x)
    (hU₂ : MemLp U 2) (hU₆ : MemLp U 6) (hUi : MemLp U ⊤)
    (hW₂ : MemLp W 2)
    (hB₆ : MemLp (NavierStokes.R3WeightedLp.fourthWeight φ W) 6)
    (g : Lp ℂ 1 (volume : Measure Space))
    (hgm : Measurable (g : Space → ℂ))
    (hbound : ∀ x, ‖(g : Space → ℂ) x‖ ≤ W x ^ 2 + 2 * (U x * W x))
    (h : Space → ℂ) (hh : MemLp h 2)
    {M V B : ℝ}
    (hM : 0 ≤ M) (hV : 0 ≤ V) (hB : 0 ≤ B)
    (bW : MeasureTheory.lpNorm W 2 volume ≤ M)
    (bU₂ : MeasureTheory.lpNorm U 2 volume ≤ V)
    (bU₆ : MeasureTheory.lpNorm U 6 volume ≤ V)
    (bUi : MeasureTheory.lpNorm U ⊤ volume ≤ V)
    (bB : MeasureTheory.lpNorm
      (NavierStokes.R3WeightedLp.fourthWeight φ W) 6 volume ≤ B)
    (bh : MeasureTheory.lpNorm h 2 volume ≤ 8 * L / R * M)
    (i j : Fin 3) :
    ‖∫ x : Space,
        (weightedPressure hφ i j g
          (NavierStokes.R3WeightedLp.stress_weight_five hφ hWm hgm
            hU0 hW0 hU₆ hW₂ hB₆ hbound).1
          (NavierStokes.R3WeightedLp.stress_weight_six hφ hWm hgm
            hU0 hW0 hUi hW₂ hB₆ hbound).1 : Space → ℂ) x * h x‖ ≤
      NavierStokes.R3StressPressureEstimate.coefficient L M V / R *
        (B ^ (3 / 2 : ℝ) + B + 1) := by
  exact (legacy_canonical_weighted_stress_bound hφ hφg hWm
    hU0 hW0 hU₂ hU₆ hUi hW₂ hB₆ g hgm hbound h hh
    hM hV hB bW bU₂ bU₆ bUi bB bh i j).trans
    (NavierStokes.R3StressPressureEstimate.rawBound_le hR
      (le_trans zero_le_one hφ.constant_ge_one) hM hV hB)

end MathGraph.LegacyCanonicalPressure

#print axioms MathGraph.LegacyCanonicalPressure.legacy_canonical_weighted_stress_bound
#print axioms MathGraph.LegacyCanonicalPressure.legacy_canonical_weighted_polynomial_bound
