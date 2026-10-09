import NavierStokes.R3PressureFourier
import NavierStokes.R3.RieszTestOperators

/-!
# V19: Laplacian-test compatibility of the actual two Riesz pressure APIs

OpenAI maintains two different Riesz pressure representations:
* R3PressureFourier.pressureL1, as a tempered distribution
* R3/Comparison.pressurePair, as an actual integral with a Schwartz test.

We compare ONLY their Laplacian-test observations for real integrable g.
This deliberately avoids claiming full equality of the distribution and
functional on every Schwartz test, much less a physical pressure estimate.

The source-PDF interpretation, pressure-flux equation (10.19) and
Navier-Stokes main theorem are not proven by this interface certificate.
-/

noncomputable section
namespace MathGraph.PressureLaplacianBridge

open Set Filter MeasureTheory ContinuousLinearMap TemperedDistribution
open NavierStokes.ProblemStatement
open NavierStokesR3.Comparison
open NavierStokesR3.HarmonicTestFunctionals
open scoped Topology SchwartzMap ContDiff FourierTransform BigOperators Laplacian LineDeriv

/-- The harmonic-test Laplacian agrees with the genuine Schwartz Laplacian,
not just by equating unverified human-readable names. -/
theorem source_and_comparison_test_laplacians_agree
    (ψ : ComplexTest) :
    laplacianCLM ψ = Δ ψ := by
  rw [SchwartzMap.laplacian_eq_sum (EuclideanSpace.basisFun (Fin 3) ℝ) ψ]
  simp [laplacianCLM, partialCLM,
    NavierStokes.ProblemStatement.coordinateVector,
    EuclideanSpace.basisFun_apply,
    LineDeriv.lineDerivOpCLM_apply]

/-- Mixed partials have the same protected observation in either order.
We prove this via the ORIGINAL Fourier multipliers and injectivity, rather
than making a hidden commutativity assumption. -/
theorem comparison_test_partials_commute
    (i j : Fin 3) (ψ : ComplexTest) :
    partialCLM i (partialCLM j ψ) =
      partialCLM j (partialCLM i ψ) := by
  apply (FourierTransform.fourierCLE ℂ ComplexTest).injective
  ext ξ
  simp only [fourier_partialCLM_apply]
  ring

/-- The genuine old L1 pressure distribution, tested against a Schwartz
Laplacian, is fixed by its actually proved Poisson identity. -/
theorem old_pressure_poisson_laplacian_test
    (i j : Fin 3) (f : Lp ℂ 1 (volume : Measure Space))
    (ψ : ComplexTest) :
    (NavierStokes.R3PressureFourier.pressureL1 i j f) (Δ ψ) =
      - (f : 𝓢'(Space, ℂ)) (partialCLM j (partialCLM i ψ)) := by
  have h := congrArg (fun F : 𝓢'(Space, ℂ) => F ψ)
    (NavierStokes.R3PressureFourier.pressureL1_poisson i j f)
  simpa [TemperedDistribution.laplacian_apply_apply,
    TemperedDistribution.lineDerivOp_apply_apply,
    partialCLM, LineDeriv.lineDerivOpCLM_apply] using h

/-- Entire Laplacian-test input transport: actual integrable real stress g,
its explicit complex L1 realization and the full Schwartz test. No spectral
uniqueness is inferred. -/
theorem actual_old_and_comparison_pressure_agree_on_laplacian_tests
    (g : Space → ℝ) (hg : Integrable g volume)
    (i j : Fin 3) (ψ : ComplexTest) :
    (NavierStokes.R3PressureFourier.pressureL1 i j
      ((memLp_one_iff_integrable.mpr (Complex.ofRealCLM.integrable_comp hg)).toLp
        (fun x : Space => (g x : ℂ))))
      (laplacianCLM ψ) =
      pressurePair i j g (laplacianCLM ψ) := by
  let fg : Space → ℂ := fun x => (g x : ℂ)
  have hgc : Integrable fg volume := Complex.ofRealCLM.integrable_comp hg
  have hl1 : MemLp fg 1 volume := memLp_one_iff_integrable.mpr hgc
  have hinput : (hl1.toLp fg : Space → ℂ) =ᵐ[volume] fg := hl1.coeFn_toLp
  conv_lhs => rw [source_and_comparison_test_laplacians_agree]
  rw [old_pressure_poisson_laplacian_test]
  rw [NavierStokesR3.RieszTestOperators.pressurePair_laplacianCLM]
  rw [comparison_test_partials_commute i j ψ]
  congr 1
  rw [Lp.toTemperedDistribution_apply]
  apply integral_congr_ae
  filter_upwards [hinput] with x hx
  simp only [smul_eq_mul]
  calc
    (partialCLM j (partialCLM i ψ)) x *
        (hl1.toLp fg : Space → ℂ) x =
          (hl1.toLp fg : Space → ℂ) x *
          (partialCLM j (partialCLM i ψ)) x := mul_comm _ _
    _ = fg x * (partialCLM j (partialCLM i ψ)) x := by rw [hx]

end MathGraph.PressureLaplacianBridge

#print axioms MathGraph.PressureLaplacianBridge.source_and_comparison_test_laplacians_agree
#print axioms MathGraph.PressureLaplacianBridge.comparison_test_partials_commute
#print axioms MathGraph.PressureLaplacianBridge.old_pressure_poisson_laplacian_test
#print axioms MathGraph.PressureLaplacianBridge.actual_old_and_comparison_pressure_agree_on_laplacian_tests
