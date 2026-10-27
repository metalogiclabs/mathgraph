import Lean

/-!
 A separate native Lean verification boundary for the deliberately simple
 source-intent / formal-scope mismatch. The English interpretation of the
 source is NOT machine-verified. No axioms, sorry, or external oracle.
-/

set_option autoImplicit false

namespace MathGraph.ProofIntentV1

def targetProperty (n : Nat) : Prop := n + n > n + 1

/-- An entirely valid theorem with a stronger scope than the intended claim. -/
theorem validGuardThree (n : Nat) (h : 3 ≤ n) : targetProperty n := by
  have h' : 1 < n := lt_of_lt_of_le (by decide : 1 < 3) h
  exact Nat.add_lt_add_left h' n

/-- Machine-proved proposed repair for the threshold-guard family. -/
theorem repairGuardTwo (n : Nat) (h : 2 ≤ n) : targetProperty n := by
  have h' : 1 < n := lt_of_lt_of_le (by decide : 1 < 2) h
  exact Nat.add_lt_add_left h' n

/-- The source claim with the omitted lower bound really is false. -/
theorem counterexampleOne : ¬ targetProperty 1 := by
  decide

theorem intendedClaimFalse : ¬ (∀ n : Nat, 1 ≤ n → targetProperty n) := by
  intro h
  exact counterexampleOne (h 1 (by decide))

/-- Standard roundtrip theorem, intentionally fulfilled by identity. -/
def compress (xs : List Bool) : List Bool := xs
def decompress (xs : List Bool) : List Bool := xs

theorem identityRoundtrip (xs : List Bool) :
    decompress (compress xs) = xs := rfl

/-- Its unrelated size requirement fails on a concrete compressible input. -/
theorem compressionBenefitFails :
    ¬ (List.length (compress (List.replicate 4 true)) < 4) := by
  decide

#print axioms validGuardThree
#print axioms repairGuardTwo
#print axioms intendedClaimFalse
#print axioms identityRoundtrip
#print axioms compressionBenefitFails

end MathGraph.ProofIntentV1
