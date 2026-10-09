import NavierStokes.R3.RieszPairing
import PressureSymbolBridge

/-!
# V16: typed physical-comparison Schwartz pairing via certified self-adjointness

Reuses the upstream theorem
  NavierStokesR3.RieszTestOperators.rieszTest_selfAdjoint
and MathGraph V13's pointwise equality of the two Riesz multiplier symbols.

This checks the comparison pressurePair on the domain where the real
stress input admits a complex Schwartz representative, retaining its
pointwise agreement as an explicit hypothesis. It does NOT establish
the general `R3PressureFourier.pressureL1`/physical-pressure distribution
duality, does NOT supply the manuscript's flux inequality, and does
NOT approve any automatic NL semantics.
-/

noncomputable section

namespace MathGraph.PressureSchwartzTranspose

open Set MeasureTheory NavierStokes.ProblemStatement
open NavierStokesR3.Comparison
open NavierStokesR3.RieszTestOperators
open scoped Topology

/-- The actual physical comparison pressure pairing is the transpose
    of the Riesz-test operation for a source with a certified Schwartz
    representative. No Gaussian-regularization assumptions are used. -/
theorem comparison_pressurePair_transpose_on_Schwartz
    (i j : Fin 3) (g : Space → ℝ) (φ ψ : ComplexTest)
    (hφ : ∀ x : Space, φ x = (g x : ℂ)) :
    pressurePair i j g ψ =
      ∫ x : Space, ψ x * rieszTest i j φ x := by
  change (∫ x : Space, (g x : ℂ) * rieszTest i j ψ x) = _
  calc
    _ = ∫ x : Space, rieszTest i j ψ x * φ x := by
      apply integral_congr_ae
      filter_upwards [] with x
      rw [hφ x]
      ring
    _ = _ := rieszTest_selfAdjoint i j ψ φ

/-- In that same explicitly restricted scope, the transpose pairing
    uses the literal complex multiplier of OpenAI's *other* pressure
    formalization (R3PressureFourier). This is a genuine cross-interface
    Fourier-integrand identity, not yet equality of pressure distributions. -/
theorem comparison_pressurePair_transpose_uses_canonical_symbol
    (i j : Fin 3) (g : Space → ℝ) (φ ψ : ComplexTest)
    (hφ : ∀ x : Space, φ x = (g x : ℂ)) :
    pressurePair i j g ψ =
      ∫ x : Space, ψ x *
        FourierTransform.fourierInv
          (fun ξ : Space =>
            NavierStokes.R3PressureFourier.rieszSymbol i j ξ *
              (FourierTransform.fourierCLE ℂ ComplexTest φ) ξ) x := by
  rw [comparison_pressurePair_transpose_on_Schwartz i j g φ ψ hφ]
  simp only [MathGraph.PressureSymbolBridge.comparison_rieszTest_canonical_symbol]

end MathGraph.PressureSchwartzTranspose

#print axioms MathGraph.PressureSchwartzTranspose.comparison_pressurePair_transpose_on_Schwartz
#print axioms MathGraph.PressureSchwartzTranspose.comparison_pressurePair_transpose_uses_canonical_symbol
