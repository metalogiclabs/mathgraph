import AnnalsChallenge.AnnalsOfMathematics.«2021-194-2-FractionalExpectationThresholds»

/-!
RED candidate: identify the Bernoulli event probability under the *actual*
AnnalsChallenge/Mathlib definitions. The imported paper theorem has `sorry`;
we neither use it as a proof nor claim the original paper is false.
-/

set_option autoImplicit false
set_option maxHeartbeats 200000

namespace MathGraph.AnnalsPCBridgeV0

open ProbabilityTheory unitInterval Set

def singletonFamily : Set (Set Unit) := {Set.univ}

/-- The sole member is selected precisely when the single element is present. -/
theorem singletonBernoulliProbability (p : I) :
    setBer((Set.univ : Set Unit), p).real singletonFamily = (p : ℝ) := by
  rfl

#print axioms singletonBernoulliProbability

end MathGraph.AnnalsPCBridgeV0
