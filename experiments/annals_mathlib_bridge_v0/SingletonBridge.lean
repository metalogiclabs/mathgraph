import AnnalsChallenge.AnnalsOfMathematics.«2021-194-2-FractionalExpectationThresholds»

/-!
Research candidate (not certified unless native CI succeeds): bind the singleton
witness to the exact `l` definition at AnnalsChallenge@e32eb1411db0...
This imports a file whose original theorem and K contain `sorry`; we assert
NO warrant for either imported statement.
-/

set_option autoImplicit false
set_option maxHeartbeats 200000

namespace MathGraph.AnnalsMathlibBridgeV0

open Set FractionalExpectationThresholds

universe u

/-- Standalone diagnostic: the supremum is indexed by a possibly proof-valued
    sort, and the codomain is conditionally complete Nat, not CompleteLattice. -/
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

def singletonFamily : Set (Set Unit) := {Set.univ}

theorem singletonUniverseSize : (Set.univ : Set Unit).ncard = 1 := by
  simp

/-- First missing authentic-definition bridge: does `l` reduce to 1? -/
theorem singletonLargestMinimalSize : l singletonFamily = 1 := by
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

/-- If the exact `l` theorem compiles, this follows in Mathlib's real log. -/
theorem singletonLogVanishes : Real.log (l singletonFamily : ℝ) = 0 := by
  rw [singletonLargestMinimalSize]
  norm_num

#print axioms singletonUniverseSize
#print axioms natSupOne
#print axioms singletonLargestMinimalSize
#print axioms singletonLogVanishes

end MathGraph.AnnalsMathlibBridgeV0
