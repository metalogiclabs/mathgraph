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
  classical
  simpa [singletonFamily] using
    (setBernoulli_real_singleton (u := (Set.univ : Set Unit))
      (s := (Set.univ : Set Unit)) p (by exact subset_rfl) Set.finite_univ)

/-- The exact AnnalsChallenge `p_c` chooses the unique half-probability value. -/
theorem singletonCriticalProbability :
    ((FractionalExpectationThresholds.p_c singletonFamily : I) : ℝ) = 1 / 2 := by
  classical
  let half : I := ⟨(1 / 2 : ℝ), by constructor <;> norm_num⟩
  have hex : ∃ p : I,
      setBer((Set.univ : Set Unit), p).real singletonFamily = (2⁻¹ : ℝ) := by
    refine ⟨half, ?_⟩
    rw [singletonBernoulliProbability]
    norm_num [half]
  unfold FractionalExpectationThresholds.p_c
  split_ifs with h
  · have hc := Classical.choose_spec h
    rw [singletonBernoulliProbability] at hc
    simpa using hc
  · exact (h hex).elim

#print axioms singletonBernoulliProbability
#print axioms singletonCriticalProbability

end MathGraph.AnnalsPCBridgeV0
