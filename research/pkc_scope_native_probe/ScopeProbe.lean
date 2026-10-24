/- 
MathGraph Check: source-native scope/gate consistency witness.

Immutable source under test: nasa-jpl/PropertyKindCalculus
@ 7d4c6b6fc26f1e0d01b0bba3319bb296f31afc11 (merged main).

Adversarial edit is data only; no upstream source modified.
The question is whether #kind_requirement accepts a gate over PairState .P
when the declared Requirement.scope instead names the distinct PairId.Q.
-/ 
module

public import HCP.L6_Requirements
meta import HCP.L6_Requirements
public import PropertyKindCalculus.KindRequirement
meta import PropertyKindCalculus.KindRequirement

import all Init.Prelude
import all PropertyKindCalculus.Provenance

open HCP.L6_Requirements
open PropertyKindCalculus

/-- Unmodified P-scope positive control. -/
#kind_requirement r3CouplingSpringRange

/--
The same gate and spot checks, but claiming Q as the scoped object.
This is deliberately inconsistent: withinRatedRange accepts PairState .P.
-/ 
def MathGraphProbe.r3WrongScope : Provenance.Requirement :=
  { r3CouplingSpringRange with
    scope := .objects [``PairId.Q] }

#kind_requirement MathGraphProbe.r3WrongScope
