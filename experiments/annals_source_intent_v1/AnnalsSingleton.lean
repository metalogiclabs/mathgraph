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
  simp [eventProbability, Rat.zero_add]

theorem halfIsThreshold : eventProbability (1 / 2) = (1 / 2 : Rat) := by
  simp [eventProbabilityEq]

/-- A zero logarithm factor: log(1)=0 in the source expression. -/
def zeroLogBound (K q : Int) : Int := K * q * 0

theorem zeroLogBoundEq (K q : Int) : zeroLogBound K q = 0 := by
  simp [zeroLogBound]

/-- Multiply the reduced 1/2 ≤ K*q*0 obstruction by 2.
    Integer-scaled model: 1 ≤ 2*0 is impossible for arbitrary K,q. -/
theorem unguardedBoundFalse (K q : Int) :
    ¬ ((1 : Int) ≤ 2 * zeroLogBound K q) := by
  simpa [zeroLogBound] using (show ¬ ((1 : Int) ≤ 0) from by decide)

/-- The repaired statement's l(F)≥2 hypothesis excludes the witness l(F)=1. -/
theorem singletonGuardFails : ¬ (2 ≤ (1 : Nat)) := by decide

#print axioms eventProbabilityEq
#print axioms halfIsThreshold
#print axioms zeroLogBoundEq
#print axioms unguardedBoundFalse
#print axioms singletonGuardFails

end MathGraph.AnnalsSingleton
