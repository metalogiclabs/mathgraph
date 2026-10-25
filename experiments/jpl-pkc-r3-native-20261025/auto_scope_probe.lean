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

set_option compiler.relaxedMetaCheck true

namespace MathGraphAutoScopeGuard20261026

open Lean Meta

/-!
A deliberately fail-closed, source-native MathGraph scope-to-gate check.
It cannot infer scientific truth from a Boolean. The only MATCH warrant is
that an already PKC-accepted empirical requirement names one object and the
declared gate expects exactly that object's PairState, with each Bool spot
check explicitly naming this same gate in its definition body.
-/
open Elab Command in
elab "#mathgraph_empirical_scope " r:ident : command => liftTermElabM do
  let rname ← realizeGlobalConstNoOverload r
  let _ ← PropertyKindCalculus.KindRequirement.checkRequirement rname
  let req ← PropertyKindCalculus.KindRequirement.requirementValueOf rname
  unless req.kind == .empirical do
    throwError "MATHGRAPH_SCOPE_UNKNOWN: requirement is not empirical"
  let claimed ← match req.scope with
    | .objects [object] => pure object
    | _ => throwError "MATHGRAPH_SCOPE_UNKNOWN: requires one explicit object"
  if req.gate.isAnonymous then
    throwError "MATHGRAPH_SCOPE_UNKNOWN: empirical gate is absent"
  let env ← getEnv
  let some gateInfo := env.find? req.gate
    | throwError "MATHGRAPH_SCOPE_UNKNOWN: empirical gate not found"
  let gateType ← Meta.whnf gateInfo.type
  let .forallE _ input output _ := gateType
    | throwError "MATHGRAPH_SCOPE_UNKNOWN: gate is not a unary predicate"
  unless output.isConstOf ``Bool do
    throwError "MATHGRAPH_SCOPE_UNKNOWN: gate return type is not Bool"
  let input ← Meta.whnf input
  let .app family indexed := input
    | throwError "MATHGRAPH_SCOPE_UNKNOWN: gate input is not an indexed observation"
  unless family.isConstOf ``HCP.L6_Requirements.PairState do
    throwError "MATHGRAPH_SCOPE_UNKNOWN: unsupported observation family"
  let .const observed _ := indexed
    | throwError "MATHGRAPH_SCOPE_UNKNOWN: object index is not a closed declaration"
  if observed != claimed then
    throwError "MATHGRAPH_SCOPE_MISMATCH: requirement object {claimed}, gate object {observed}"
  if req.spotChecks.isEmpty then
    throwError "MATHGRAPH_SCOPE_UNKNOWN: no spot-check evidence"
  for s in req.spotChecks do
    let some info := env.find? s
      | throwError "MATHGRAPH_SCOPE_UNKNOWN: spot check {s} is absent"
    let some value := info.value? (allowOpaque := true)
      | throwError "MATHGRAPH_SCOPE_UNKNOWN: spot check {s} has no inspectable body"
    let refs := value.foldConsts ({} : NameSet) fun c names => names.insert c
    unless refs.contains req.gate do
      throwError "MATHGRAPH_SCOPE_UNKNOWN: spot check {s} does not directly reference gate"
  logInfo m!"MATHGRAPH_SCOPE_MATCH: requirement '{req.name}' object {claimed} is gate-bound"

end MathGraphAutoScopeGuard20261026

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

public def maskedGateResult : Bool :=
  (withinRatedRange pairP_earlier) == (withinRatedRange pairP_earlier)

public def maskedGateSpot : Provenance.Requirement :=
  { HCP.L6_Requirements.r3CouplingSpringRange with
    name := "MathGraph-Masked-Gate"
    spotChecks := [``maskedGateResult] }

-- Existing PKC semantics alone admit these declarations.
#kind_requirement wrongObjectQ
#kind_requirement unrelatedSpot
#kind_requirement maskedGateSpot

-- MathGraph tests below must be driven by requirement metadata, not hand-provided P/Q.
#mathgraph_empirical_scope HCP.L6_Requirements.r3CouplingSpringRange
#mathgraph_empirical_scope wrongObjectQ
#mathgraph_empirical_scope unsupportedAll
#mathgraph_empirical_scope unrelatedSpot
#mathgraph_empirical_scope maskedGateSpot

end MathGraphAutoScope20261026
