/-!
Bounded research: Boolean receipt-list liveness equivalence, for all finite lists.

This proves the mathematical list predicate, not that arbitrary Python code,
source identity, or an external documentary receipt is formally authenticated.
-/
namespace MathGraphEvidenceLiveness

def active (withdrawn : String → Bool) (receipt : String) : Bool :=
  !withdrawn receipt

def oldLiveness (withdrawn : String → Bool)
    (route : List String) (relation : Option (String × List String)) : Bool :=
  (route ++ (match relation with
     | none => []
     | some (verifier, evidence) => verifier :: evidence)).all (active withdrawn)

def newLiveness (withdrawn : String → Bool)
    (route : List String) (relation : Option (String × List String)) : Bool :=
  route.all (active withdrawn) &&
    (match relation with
      | none => true
      | some (verifier, evidence) =>
          active withdrawn verifier && evidence.all (active withdrawn))

private theorem all_append_receipts (predicate : String → Bool)
    (left right : List String) :
    (left ++ right).all predicate = (left.all predicate && right.all predicate) := by
  induction left with
  | nil => simp
  | cons receipt tail ih =>
      simp [List.all, ih, Bool.and_assoc]

theorem all_finite_receipt_lists_equivalent
    (withdrawn : String → Bool) (route : List String)
    (relation : Option (String × List String)) :
    oldLiveness withdrawn route relation =
      newLiveness withdrawn route relation := by
  cases relation with
  | none =>
      simp [oldLiveness, newLiveness]
  | some pair =>
      rcases pair with ⟨verifier, evidence⟩
      simp [oldLiveness, newLiveness, all_append_receipts,
        List.all, Bool.and_assoc]

end MathGraphEvidenceLiveness

#print axioms MathGraphEvidenceLiveness.all_finite_receipt_lists_equivalent
