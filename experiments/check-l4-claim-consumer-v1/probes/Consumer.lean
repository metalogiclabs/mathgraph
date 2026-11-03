import L4YAML.Proofs.Serialization.TraceOf.Node
open L4YAML L4YAML.Surface L4YAML.Proofs.Serialization.TraceOf
namespace MathGraphClaim
-- This consumer requires the two exported constructor APIs asserted by upstream212.
-- Its rejection does not assert that no other proof could exist.
def EmptyTailTrace (n : Nat) (s : SurfPos) : Prop :=
  TCompactSeqTail n s s [] ∧ TCompactMapTail n s s []
theorem requiredTrace (n : Nat) (s : SurfPos) : EmptyTailTrace n s :=
  ⟨TCompactSeqTail.nil n s, TCompactMapTail.nil n s⟩
theorem consumer (n : Nat) (s : SurfPos) : EmptyTailTrace n s := requiredTrace n s
#print axioms consumer
end MathGraphClaim
