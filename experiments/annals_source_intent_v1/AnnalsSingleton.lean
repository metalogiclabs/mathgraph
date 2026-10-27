import Lean

/-!
Native Lean 4 certificate for a REDUCED singleton Bernoulli model.
The external AnnalsChallenge theorem uses Mathlib definitions and has `sorry`.
This file makes no claim of proving that theorem or identifying the authors' intent.
-/

set_option autoImplicit false

namespace MathGraph.AnnalsSingleton

/-- For X={x} and F={{x}}, the selected world has Bernoulli weight p. -/
def eventProbability (p : Rat) : Rat := (1 - p) * 0 + p * 1

theorem eventProbabilityEq (p : Rat) : eventProbability p = p := by
  simp [eventProbability]

theorem halfIsThreshold : eventProbability (1 / 2) = (1 / 2 : Rat) := by
  simp [eventProbabilityEq]

/-- A zero logarithm factor: log(1)=0 in the source expression. -/
def zeroLogBound (K q : Rat) : Rat := K * q * 0

theorem zeroLogBoundEq (K q : Rat) : zeroLogBound K q = 0 := by
  simp [zeroLogBound]

/-- Counterexample to the unguarded inequality, for ANY finite rational K,q. -/
theorem unguardedBoundFalse (K q : Rat) :
    ¬ ((1 / 2 : Rat) ≤ zeroLogBound K q) := by
  intro h
  have h0 : (1 / 2 : Rat) ≤ 0 := by simpa [zeroLogBound] using h
  exact (show ¬ ((1 / 2 : Rat) ≤ 0) from by decide) h0

/-- The repaired statement's l(F)≥2 hypothesis excludes the witness l(F)=1. -/
theorem singletonGuardFails : ¬ (2 ≤ (1 : Nat)) := by decide

#print axioms eventProbabilityEq
#print axioms halfIsThreshold
#print axioms zeroLogBoundEq
#print axioms unguardedBoundFalse
#print axioms singletonGuardFails

end MathGraph.AnnalsSingleton
