/- MathGraph private replay: Q-scoped claim beside the authentic P requirement. -/
module
public import HCP.L6_Requirements
meta import HCP.L6_Requirements
public import PropertyKindCalculus.KindRequirement
meta import PropertyKindCalculus.KindRequirement
import all Init.Prelude
import all PropertyKindCalculus.Provenance

open HCP.L6_Requirements
open PropertyKindCalculus

#kind_requirement r3CouplingSpringRange

namespace HCP.L6_Requirements

public def r3WrongScopeMathGraph20261025 : Provenance.Requirement :=
  { r3CouplingSpringRange with
    name := "R3-Q-MathGraph"
    statement := "Q's coupling-spring extension stays within its rated range in every state or record"
    scope := .objects [``PairId.Q] }

#kind_requirement r3WrongScopeMathGraph20261025
#kind_requirements HCP.L6_Requirements
#kind_requirement_coverage HCP.L6_Requirements
#kind_requirement_clean HCP.L6_Requirements

end HCP.L6_Requirements
