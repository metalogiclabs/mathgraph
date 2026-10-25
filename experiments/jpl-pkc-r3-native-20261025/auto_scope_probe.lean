/- Test-first MathGraph PKC empirical object evidence checker: source-native fixtures.
   Expected: MATCH for original P; MISMATCH for Q using P gate;
   UNKNOWN for .all scope and an unrelated true spot check. -/
module
public import HCP.L6_Requirements
meta import HCP.L6_Requirements
public import PropertyKindCalculus.KindRequirement
meta import PropertyKindCalculus.KindRequirement
import all Init.Prelude
import all PropertyKindCalculus.Provenance

open HCP.L6_Requirements
open PropertyKindCalculus

namespace MathGraphAutoScope20261026

public def wrongObjectQ : Provenance.Requirement :=
  { HCP.L6_Requirements.r3CouplingSpringRange with
    name := "MathGraph-Q"
    statement := "Q's extension remains within its rated range"
    scope := .objects [``HCP.L6_Requirements.PairId.Q] }

public def unsupportedAll : Provenance.Requirement :=
  { HCP.L6_Requirements.r3CouplingSpringRange with
    name := "MathGraph-All"
    scope := .all }

public def unrelatedTrue : Bool := true

public def unrelatedSpot : Provenance.Requirement :=
  { HCP.L6_Requirements.r3CouplingSpringRange with
    name := "MathGraph-Unlinked-Spot"
    spotChecks := [``unrelatedTrue] }

-- Existing PKC semantics alone admit these declarations.
#kind_requirement wrongObjectQ
#kind_requirement unrelatedSpot

-- MathGraph tests below must be driven by requirement metadata, not hand-provided P/Q.
#mathgraph_empirical_scope HCP.L6_Requirements.r3CouplingSpringRange
#mathgraph_empirical_scope wrongObjectQ
#mathgraph_empirical_scope unsupportedAll
#mathgraph_empirical_scope unrelatedSpot

end MathGraphAutoScope20261026
