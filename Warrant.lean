import Mathlib

namespace IndependentWarrant

def Adequate {S T V : Type} (q : S → T) (w : S → V) : Prop :=
  ∀ x y, q x = q y → w x = w y

theorem factor_adequate {S T V : Type} (q : S → T) (w : S → V)
    (f : T → V) (h : ∀ x, w x = f (q x)) : Adequate q w := by
  intro x y e
  rw [h x, h y, e]

theorem collision_refutes {S T V : Type} (q : S → T) (w : S → V)
    (x y : S) (e : q x = q y) (d : w x ≠ w y) : ¬ Adequate q w :=
  fun h => d (h x y e)

theorem refinement_adequate {S T V : Type} (q : S → T) (w : S → V) :
    Adequate (fun x => (q x, w x)) w := by
  intro x y e
  exact congrArg Prod.snd e

theorem refinement_minimal {S T V U : Type} (q : S → T) (w : S → V)
    (r : S → U) (hq : Adequate r q) (hw : Adequate r w) :
    Adequate r (fun x => (q x, w x)) := by
  intro x y e
  rw [hq x y e, hw x y e]

theorem compose {S T U V : Type} (q : S → T) (r : T → U)
    (w : T → V) (h : Adequate r w) :
    Adequate (r ∘ q) (w ∘ q) := by
  intro x y e
  exact h (q x) (q y) e

#print axioms factor_adequate
#print axioms collision_refutes
#print axioms refinement_adequate
#print axioms refinement_minimal
#print axioms compose
end IndependentWarrant
