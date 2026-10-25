/- MathGraph private causal withdrawal: Q-only scope over P-only port. -/
module
public import HCP.L6_Requirements
meta import HCP.L6_Requirements
public import PropertyKindCalculus.KindRequirement
meta import PropertyKindCalculus.KindRequirement
import all Init.Prelude
import all PropertyKindCalculus.Provenance

open HCP.L6_Requirements
open PropertyKindCalculus

namespace MathGraphQOnlyControl20261025

open PropertyKindCalculus.Provenance (NodeId KindRef)

public def duplicatedPBoundary : Provenance.Contract NodeId KindRef :=
  HCP.L6_Requirements.couplingExtensionBoundary

public def wrongScopeOnly : Provenance.Requirement :=
  { HCP.L6_Requirements.r3CouplingSpringRange with
    name := "R3-Q-Only-MathGraph"
    statement := "Q's coupling-spring extension stays within its rated range in every state or record"
    governs := ``duplicatedPBoundary
    scope := .objects [``HCP.L6_Requirements.PairId.Q] }

#kind_requirement wrongScopeOnly
#kind_requirement_coverage MathGraphQOnlyControl20261025
#kind_requirement_clean MathGraphQOnlyControl20261025

end MathGraphQOnlyControl20261025
