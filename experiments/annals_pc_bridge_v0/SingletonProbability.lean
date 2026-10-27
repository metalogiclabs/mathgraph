import AnnalsChallenge.AnnalsOfMathematics.«2021-194-2-FractionalExpectationThresholds»

/-!
Identify the Bernoulli event probability and the critical threshold under the
actual AnnalsChallenge/Mathlib definitions. The imported paper theorem has `sorry`;
we neither use it as a proof nor claim the original paper is false.
-/

set_option autoImplicit false
set_option maxHeartbeats 200000

namespace MathGraph.AnnalsPCBridgeV0

open ProbabilityTheory unitInterval Set

universe u

def singletonFamily : Set (Set Unit) := {Set.univ}

/-- The sole member is selected precisely when the single element is present. -/
theorem singletonBernoulliProbability (p : I) :
    setBer((Set.univ : Set Unit), p).real singletonFamily = (p : ℝ) := by
  classical
  simpa [singletonFamily] using
    (setBernoulli_real_singleton (u := (Set.univ : Set Unit))
      (s := (Set.univ : Set Unit)) p subset_rfl Set.finite_univ)

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

private theorem natSupOne {ι : Sort u} [Nonempty ι] :
    (⨆ _ : ι, (1 : Nat)) = 1 := by
  classical
  have hbounded : BddAbove (Set.range (fun _ : ι => (1 : Nat))) := by
    refine ⟨1, ?_⟩
    rintro x ⟨i, rfl⟩
    exact le_rfl
  apply le_antisymm
  · exact ciSup_le (fun _ => le_rfl)
  · exact le_ciSup hbounded (Classical.choice (inferInstance : Nonempty ι))

/-- This uses the original source's noncomputable `l`, not a surrogate. -/
theorem singletonLargestMinimalSize :
    FractionalExpectationThresholds.l singletonFamily = 1 := by
  classical
  let w : singletonFamily := ⟨Set.univ, by simp [singletonFamily]⟩
  have hmin : IsMin w := by
    intro a _
    have ha : (a : Set Unit) = Set.univ := by
      simpa [singletonFamily] using a.property
    exact le_of_eq (Subtype.ext ha.symm)
  haveI : Nonempty (IsMin w) := ⟨hmin⟩
  simpa [FractionalExpectationThresholds.l, singletonFamily, w] using
    (natSupOne (ι := IsMin w))

/-- Test target: refute only the *unguarded* inequality, for every real K. -/
theorem singletonUnguardedCounterexample (K : ℝ) :
    ¬ (((FractionalExpectationThresholds.p_c singletonFamily : I) : ℝ) ≤
      K * ((FractionalExpectationThresholds.q_f singletonFamily : I) : ℝ) *
        Real.log (FractionalExpectationThresholds.l singletonFamily : ℝ)) := by
  rfl

#print axioms singletonBernoulliProbability
#print axioms singletonCriticalProbability
#print axioms singletonLargestMinimalSize
#print axioms singletonUnguardedCounterexample

end MathGraph.AnnalsPCBridgeV0
