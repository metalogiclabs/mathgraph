import NavierStokes.R3PressureFourier
import NavierStokes.R3.ComparisonFourierSetup

/-!
V13: exact original Fourier multiplier-symbol correspondence.

Two upstream pressure representations in the same OpenAI commit:
(1) NavierStokes.R3PressureFourier.pressureL1 is the inverse transform of
    the complex L1 Fourier source multiplied by R3PressureFourier.rieszSymbol.
(2) NavierStokesR3.Comparison.pressurePair is built from testing stress
    against Comparison.rieszTest, using a real-valued Fourier symbol.

The symbols are definitionally identical after scalar embedding.
This proof does NOT equate the corresponding distributions or their
pairings: Fourier duality / normalization, physical pressure identification
and manuscript equation (10.19) remain separate independent obligations.
-/

noncomputable section

namespace MathGraph.PressureSymbolBridge

open NavierStokes.ProblemStatement
open scoped Topology

/-- The complex Riesz symbol used by the L1 pressure construction is
    exactly the complexification of the real comparison-test symbol. -/
theorem canonical_and_comparison_symbol_equal (i j : Fin 3) (ξ : Space) :
    NavierStokes.R3PressureFourier.rieszSymbol i j ξ =
      (NavierStokesR3.Comparison.rieszSymbol i j ξ : ℂ) := by
  rfl

/-- Consequently, the Riesz-transformed Schwartz test in the physical
    pressure comparison uses exactly the source-pinned complex Fourier
    multiplier. This says nothing about distribution/test duality. -/
theorem comparison_rieszTest_canonical_symbol
    (i j : Fin 3) (ψ : NavierStokesR3.Comparison.ComplexTest) :
    NavierStokesR3.Comparison.rieszTest i j ψ =
      FourierTransform.fourierInv
        (fun ξ : Space =>
          NavierStokes.R3PressureFourier.rieszSymbol i j ξ *
            (FourierTransform.fourierCLE ℂ NavierStokesR3.Comparison.ComplexTest ψ) ξ) := by
  rfl

end MathGraph.PressureSymbolBridge

#print axioms MathGraph.PressureSymbolBridge.canonical_and_comparison_symbol_equal
#print axioms MathGraph.PressureSymbolBridge.comparison_rieszTest_canonical_symbol
