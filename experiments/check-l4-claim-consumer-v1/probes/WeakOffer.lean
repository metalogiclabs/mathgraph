import L4YAML.Proofs.Serialization.TraceOf.Node
open L4YAML L4YAML.Surface L4YAML.Proofs.Serialization.TraceOf
namespace MathGraphClaim
-- A deliberately weakened offered conclusion. Valid Lean, insufficient for P.
def EmptyTailTrace (n : Nat) (s : SurfPos) : Prop :=
  TCompactSeqTail n s s [] ∧ TCompactMapTail n s s []
theorem offered (n : Nat) (s : SurfPos) : EmptyTailTrace n s ∨ True := Or.inr True.intro
#print axioms offered
end MathGraphClaim
