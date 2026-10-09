import FourLossBridge
import ThirdLattice

/-!
V6: compose the source-pinned inverse bridge with the **proved**
two-dimensional exponent-three lattice summability.

The conclusion is the real OpenAI pointwise derivative-word estimate with
w.length + 4 torus input derivatives and a new, explicit finite constant.
It does not silently retain a premise for the source-domain lattice sum.
It is still not a proof of exact natural-language interpretation of the
whole published paper or pressure-flux inequality.
-/

noncomputable section

namespace MathGraph.FourLossComplete

open Set
open NavierStokes.TorusInverse
open NavierStokes.SmoothFamilyTorusInverse
open scoped Topology ContDiff BigOperators

variable {P : Type} [NormedAddCommGroup P] [NormedSpace ℝ P] [FiniteDimensional ℝ P]

/-- Actual source-pinned torus inverse, four input derivatives above output
    derivative-word order; no imported lattice-summability hypothesis. -/
omit [FiniteDimensional ℝ P] in
theorem actual_inverse_four_loss
    (d : Direction) {f : Source P}
    (hf : ContDiff ℝ ∞ f) (hp : Periodic f)
    (w : List Bool) (p : P) (Y : Plane) {C : ℝ}
    (hzero : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖f (p, (x, y))‖ ≤ C)
    (hfirst : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (w.length + 4)
        (slice f p) (x, y)‖ ≤ C)
    (hsecond : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (w.length + 4)
        (NavierStokes.SmoothFourierData.swapFunction (slice f p)) (x, y)‖ ≤ C) :
    ‖derivativeWord w (slice (inverse d f) p) Y‖ ≤
      ((6 * ‖omega⁻¹‖) * ‖omega‖ ^ w.length) *
      ((3 ^ ((w.length + 1) + 3) * C) *
        ∑' k : Frequency, (weight k ^ 3)⁻¹) := by
  exact MathGraph.FourLossBridge.inverse_four_loss_of_summable_third
    MathGraph.ThirdLattice.summable_weight_inv_three
    d hf hp w p Y hzero hfirst hsecond

end MathGraph.FourLossComplete

#print axioms MathGraph.FourLossComplete.actual_inverse_four_loss
