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

def singletonFamily : Set (Set Unit) := {Set.univ}

theorem singletonUniverseSize : (Set.univ : Set Unit).ncard = 1 := by
  simp

/-- First missing authentic-definition bridge: does `l` reduce to 1? -/
theorem singletonLargestMinimalSize : l singletonFamily = 1 := by
  classical
  have hmin : IsMin (⟨Set.univ, by simp [singletonFamily]⟩ : singletonFamily) := by
    intro a _
    have ha : (a : Set Unit) = Set.univ := by
      simpa [singletonFamily] using a.property
    exact le_of_eq (Subtype.ext ha.symm)
  haveI : Nonempty (IsMin (⟨Set.univ, by simp [singletonFamily]⟩ : singletonFamily)) :=
    ⟨hmin⟩
  have hbound : BddAbove (Set.range
      (fun _ : IsMin (⟨Set.univ, by simp [singletonFamily]⟩ : singletonFamily) => (1 : Nat))) := by
    refine ⟨1, ?_⟩
    rintro x ⟨i, rfl⟩
    exact le_rfl
  simp [FractionalExpectationThresholds.l, singletonFamily]
  apply le_antisymm
  · apply ciSup_le
    intro _
    exact le_rfl
  · exact le_ciSup hbound hmin

/-- If the exact `l` theorem compiles, this follows in Mathlib's real log. -/
theorem singletonLogVanishes : Real.log (l singletonFamily : ℝ) = 0 := by
  rw [singletonLargestMinimalSize]
  norm_num

#print axioms singletonUniverseSize
#print axioms singletonLargestMinimalSize
#print axioms singletonLogVanishes

end MathGraph.AnnalsMathlibBridgeV0
