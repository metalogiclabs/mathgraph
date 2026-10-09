import NavierStokes.R3.PressureFlux
import PressureEnvelopeObstruction

/-!
V14 physical-flux zero-control at the ACTUAL upstream pressure integral.

The actual pressure flux is zero when velocity fields coincide on the
time slice: the integrand contains a linear functional evaluated at the
zero velocity difference. This uses real OpenAI R3 types, definitions and
the same integral as exists_uniform_actual_pressure_flux_bound.

However, the formal *upper envelope* in OpenAI's bound can be strictly
positive when its A and B inputs are zero, while the manuscript-style
B-only upper envelope is zero. This is a certified diagnostic separating
an upper-bound expression from the physical quantity it bounds.

It is NOT a counterexample to the PDE statement, a verification of
manuscript (10.19), or a source-NL semantic approval.
-/

noncomputable section

namespace MathGraph.PressureZeroControl

open Set MeasureTheory NavierStokesR3.ProblemStatement
open MathGraph.PressureEnvelopeObstruction
open scoped ContDiff Topology

/-- In the real pressure-flux integrand, an identical velocity time slice
gives identically zero pressure flux independently of any PDE assumptions. -/
theorem actual_pressure_flux_zero_of_equal_velocity_slice
    (u v : VelocityField) (p q : PressureField) (t R : ℝ)
    (h : ∀ x : Space, u (t,x) = v (t,x)) :
    (∫ x : Space,
      (p - q) (t,x) *
        fderiv ℝ (NavierStokesR3.ComparisonCutoffs.weight R) x ((u-v) (t,x))) = 0 := by
  have hz (x : Space) : (u-v) (t,x) = 0 := by
    change u (t,x) - v (t,x) = 0
    exact sub_eq_zero.mpr (h x)
  simp [hz]

/-- Both estimated expressions at the same zero A,B input are different.
This proves nothing about actual nonzero flux, which is zero above. -/
theorem numerical_upper_envelopes_differ_at_zero :
    sourceEnvelope 1 0 = 0 ∧ formalEnvelope 1 0 0 = 1 := by
  constructor
  · norm_num [sourceEnvelope]
  · norm_num [formalEnvelope, NavierStokesR3.WholeSpaceComparisonClosure.pressureEnvelope]

theorem formal_envelope_can_be_positive_at_zero_data :
    sourceEnvelope 1 0 < formalEnvelope 1 0 0 := by
  rw [(numerical_upper_envelopes_differ_at_zero).1,
    (numerical_upper_envelopes_differ_at_zero).2]
  norm_num

end MathGraph.PressureZeroControl

#print axioms MathGraph.PressureZeroControl.actual_pressure_flux_zero_of_equal_velocity_slice
#print axioms MathGraph.PressureZeroControl.numerical_upper_envelopes_differ_at_zero
#print axioms MathGraph.PressureZeroControl.formal_envelope_can_be_positive_at_zero_data
