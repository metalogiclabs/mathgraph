import L4YAML.Surface.Node
open L4YAML L4YAML.Surface
namespace MathGraphClaim
-- The source grammar already admits both empty tails, for every index and position.
theorem sourceEmptyTails (n : Nat) (s : SurfPos) :
    SCompactSeqTail n s s ∧ SCompactMapTail n s s :=
  ⟨SCompactSeqTail.nil n s, SCompactMapTail.nil n s⟩
#print axioms sourceEmptyTails
end MathGraphClaim
