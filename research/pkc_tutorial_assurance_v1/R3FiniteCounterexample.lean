import HCP.L6_Requirements

/-!
A separate finite counterexample to an *overstrong reading* of the empirical
R3 obligation. The tutorial itself correctly labels R3 as empirical and
documents only two passing P records and a gate. Nothing below is a JPL bug
or a demonstration of real hardware outside its physical operating range.
This model is an ordinary well-typed hypothetical PairState P.
-/

namespace MathGraphPKCTutorialAssurance
open HCP.L6_Requirements

private def nominalP : PairState PairId.P where
  massA := ⟨3⟩
  massB := ⟨5⟩
  couplingExtension := ⟨6⟩

private def beyondRatedP : PairState PairId.P where
  massA := ⟨3⟩
  massB := ⟨5⟩
  couplingExtension := ⟨7⟩

/-- A rated P record passes the same source-native empirical gate. -/
theorem rated_record_passes : withinRatedRange nominalP = true := by decide

/-- A type-correct P record exceeds the declared model limit: the gate is
a decision procedure, not proof that *every* P state satisfies it. -/
theorem out_of_range_record_refused :
    withinRatedRange beyondRatedP = false := by decide

#print axioms rated_record_passes
#print axioms out_of_range_record_refused

end MathGraphPKCTutorialAssurance
