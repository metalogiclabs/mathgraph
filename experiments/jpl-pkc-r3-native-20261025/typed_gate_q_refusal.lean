/- MathGraph negative spike: claim Q cannot reuse P-typed gate as Q evidence. -/
module
public import HCP.L6_Requirements
meta import HCP.L6_Requirements
public import PropertyKindCalculus.KindRequirement
meta import PropertyKindCalculus.KindRequirement

namespace MathGraphTypedScope20261025
open HCP.L6_Requirements
open PropertyKindCalculus

structure GateFor (π : PairId) where
  check : PairState π → Bool

def incorrectQ : Provenance.Requirement :=
  { r3CouplingSpringRange with
    name := "R3-Q-Typed-Obstruction-MathGraph"
    statement := "Q's extension remains within the rated range"
    scope := .objects [``PairId.Q] }

-- The original PKC requirement check admits this declarative Q claim.
#kind_requirement incorrectQ

-- The independent typed evidence obligation must reject P's gate for Q.
def purportedQEvidence : GateFor .Q := ⟨withinRatedRange⟩

end MathGraphTypedScope20261025
