module
public import L4YAML.Parser.Composition
public import L4YAML.Parser.IndexedComposition
public import L4YAML.Output.Json
public import L4YAML.Proofs.Serialization.SerializationWellFormed
public import Lean.Data.Json
public meta import L4YAML.Parser.Composition
public meta import L4YAML.Parser.IndexedComposition
public meta import L4YAML.Output.Json
public meta import L4YAML.Proofs.Serialization.SerializationWellFormed

@[expose] public section

namespace MathGraph.GraphCompose
open L4YAML

/-!
A BOUNDED graph representation of JPL's raw YAML serialization tree.
All changes are on the MathGraph side; no JPL source is changed.
Node IDs are allocated at the START of nodes and aliases refer to IDs.
This expresses cycles and sharing without finite tree unrolling.

No universal YAML proof is claimed. The finite tests independently compare
node-edge identity with a byte-pinned ruamel.yaml composer.
-/

structure GraphState where
  nodes : Array Lean.Json := #[]
  anchors : List (String × Nat) := []
  deriving Inhabited

def jsonNode (kind : String) (extra : List (String × Lean.Json)) : Lean.Json :=
  Lean.Json.mkObj (("kind", .str kind) :: extra)

def alloc (s : GraphState) : Nat × GraphState :=
  (s.nodes.size, { s with nodes := s.nodes.push Lean.Json.null })

def assign (s : GraphState) (id : Nat) (value : Lean.Json) : GraphState :=
  { s with nodes := s.nodes.set! id value }

def bind (s : GraphState) (name : Option String) (id : Nat) : GraphState :=
  match name with
  | none => s
  | some a => { s with anchors := (a, id) :: s.anchors }

/-- The same most-recent-first lookup used by the actual alias branch. -/
def aliasTarget (s : GraphState) (name : String) : Option Nat :=
  s.anchors.findSome? (fun (n, idx) => if n == name then some idx else none)

/-- A just-started anchor is immediately visible to its descendants,
    even before any child has been traversed. -/
theorem started_anchor_visible (s : GraphState) (name : String) (id : Nat) :
    aliasTarget (bind s (some name) id) name = some id := by
  simp [aliasTarget, bind]

/-- The new graph node's ID is allocated before processing children. -/
theorem allocation_is_fresh (s : GraphState) :
    (alloc s).1 = s.nodes.size := rfl

/-!
Conditional event-to-graph bridge. JPL's Event describes names and access;
MathGraph's state additionally stores target node IDs. There is deliberately
NO claim that an arbitrary source has a unique TraceOf derivation (refuted at
L4YAML PR #119). The theorem covers the sublanguage below only.
-/

open L4YAML.Proofs.Serialization.SerializationWellFormed

inductive AnchorEvent where
  | beginDocument
  | endDocument
  | defineAnchor (name : String) (id : Nat)
  | useAlias (name : String)
  deriving Repr, DecidableEq

def AnchorEvent.asSerializationEvent : AnchorEvent → Event
  | .beginDocument => .beginDocument
  | .endDocument => .endDocument
  | .defineAnchor name _ => .defineAnchor name
  | .useAlias name => .useAlias name

/-- Graph-level trace authorization for the fragment; no names are guessed
from arbitrary input text. IDs are supplied by the chosen trace's node-start
events. -/
def graphTraceCheck (s : GraphState) : List AnchorEvent → Bool
  | [] => true
  | .beginDocument :: rest =>
      graphTraceCheck { s with anchors := [] } rest
  | .endDocument :: rest =>
      graphTraceCheck { s with anchors := [] } rest
  | .defineAnchor name id :: rest =>
      graphTraceCheck (bind s (some name) id) rest
  | .useAlias name :: rest =>
      (aliasTarget s name).isSome && graphTraceCheck s rest

private theorem first_match_some_iff (xs : List (String × Nat)) (name : String) :
    (xs.findSome? (fun (n, id) => if n == name then some id else none)).isSome = true ↔
      name ∈ xs.map Prod.fst := by
  induction xs with
  | nil => simp
  | cons pair tail ih =>
      obtain ⟨key, id⟩ := pair
      by_cases h : key = name
      · subst key
        simp [List.findSome?]
      · have hrev : name ≠ key := Ne.symm h
        simp_all [List.findSome?]

theorem aliasTarget_exists_iff_allowed
    (env : Env) (s : GraphState) (name : String)
    (h : env.anchors = s.anchors.map Prod.fst) :
    (aliasTarget s name).isSome = true ↔ AliasAllowed env name := by
  unfold aliasTarget AliasAllowed
  rw [h]
  exact first_match_some_iff s.anchors name

/-- A full-list conditional correspondence between the actual JPL
well-formedness checker and the GraphState's node-ID availability checker.
Document reset and repeated declarations are covered. This theorem does not
interpret omitted tag events or assert source trace uniqueness. -/
theorem graphTraceCheck_agrees_with_JPL
    (env : Env) (s : GraphState) (ops : List AnchorEvent)
    (h : env.anchors = s.anchors.map Prod.fst) :
    graphTraceCheck s ops =
      checkFrom env (ops.map AnchorEvent.asSerializationEvent) := by
  induction ops generalizing env s with
  | nil =>
      simp [graphTraceCheck, checkFrom]
  | cons event rest ih =>
      cases event with
      | beginDocument =>
          have h' :
              (env.reset).anchors =
                ({ s with anchors := [] } : GraphState).anchors.map Prod.fst := by
            rfl
          simpa [graphTraceCheck, checkFrom, AnchorEvent.asSerializationEvent] using
            ih env.reset { s with anchors := [] } h'
      | endDocument =>
          have h' :
              (env.reset).anchors =
                ({ s with anchors := [] } : GraphState).anchors.map Prod.fst := by
            rfl
          simpa [graphTraceCheck, checkFrom, AnchorEvent.asSerializationEvent] using
            ih env.reset { s with anchors := [] } h'
      | defineAnchor name id =>
          have h' :
              ({ env with anchors := name :: env.anchors } : Env).anchors =
                (bind s (some name) id).anchors.map Prod.fst := by
            simp [bind, h]
          simpa [graphTraceCheck, checkFrom, AnchorEvent.asSerializationEvent] using
            ih { env with anchors := name :: env.anchors }
               (bind s (some name) id) h'
      | useAlias name =>
          by_cases ha : AliasAllowed env name
          · have ht : (aliasTarget s name).isSome = true :=
              (aliasTarget_exists_iff_allowed env s name h).2 ha
            simpa [graphTraceCheck, checkFrom, AnchorEvent.asSerializationEvent,
                   ha, ht] using ih env s h
          · have ht : (aliasTarget s name).isSome = false := by
              cases hs : (aliasTarget s name).isSome with
              | false => rfl
              | true =>
                  exact False.elim (ha ((aliasTarget_exists_iff_allowed env s name h).1 hs))
            simp [graphTraceCheck, checkFrom, AnchorEvent.asSerializationEvent, ha, ht]

/-!
Raw-node-start provenance bridge (conditional on the selected JPL raw tree).
Each .nodeStart allocates its own graph ID from the ACTUAL GraphState allocator.
The projection to JPL's Event omits only this local ID, not the declaration.
This does not claim uniqueness or even existence of a source TraceOf derivation.
-/

inductive RawAction where
  | beginDocument
  | endDocument
  | nodeStart (anchor : Option String)
  | aliasUse (name : String)
  deriving Repr, DecidableEq

def RawAction.events : RawAction → List Event
  | .beginDocument => [.beginDocument]
  | .endDocument => [.endDocument]
  | .nodeStart none => []
  | .nodeStart (some name) => [.defineAnchor name]
  | .aliasUse name => [.useAlias name]

def projectedEvents (actions : List RawAction) : List Event :=
  actions.flatMap RawAction.events

/-- Same two graph operations performed by each original GraphCompose.build
node constructor, factored into an executable allocation transition. -/
def allocateNodeStart (s : GraphState) (anchor : Option String) : Nat × GraphState :=
  let (id, s') := alloc s
  (id, bind s' anchor id)

theorem allocateNodeStart_fresh (s : GraphState) (anchor : Option String) :
    (allocateNodeStart s anchor).1 = s.nodes.size := rfl

theorem allocateNodeStart_visible (s : GraphState) (name : String) :
    aliasTarget (allocateNodeStart s (some name)).2 name =
      some (allocateNodeStart s (some name)).1 := by
  simp [allocateNodeStart, alloc, bind, aliasTarget]

/-- The source-plan checker exercises REAL graph allocation and resets.
Only alias existence matters for this Boolean contract; the full graph
composer below also retains the chosen ID and emits actual reference edges. -/
def rawActionCheck (s : GraphState) : List RawAction → Bool
  | [] => true
  | .beginDocument :: rest =>
      rawActionCheck { s with anchors := [] } rest
  | .endDocument :: rest =>
      rawActionCheck { s with anchors := [] } rest
  | .nodeStart anchor :: rest =>
      rawActionCheck (allocateNodeStart s anchor).2 rest
  | .aliasUse name :: rest =>
      (aliasTarget s name).isSome && rawActionCheck s rest

/-- For EVERY event-action list, JPL's actual name-only well-formedness
checker agrees with the graph ID authorization checker, provided their
initial environments name the same anchors. Unlike the earlier theorem,
definition events receive fresh IDs via the actual graph allocator; callers
cannot choose their IDs. -/
theorem rawActionCheck_agrees_with_JPL (env : Env) (s : GraphState)
    (actions : List RawAction)
    (h : env.anchors = s.anchors.map Prod.fst) :
    rawActionCheck s actions = checkFrom env (projectedEvents actions) := by
  induction actions generalizing env s with
  | nil =>
      simp [rawActionCheck, projectedEvents, checkFrom]
  | cons action rest ih =>
      cases action with
      | beginDocument =>
          have h' : (env.reset).anchors =
              ({ s with anchors := [] } : GraphState).anchors.map Prod.fst := rfl
          simpa [rawActionCheck, projectedEvents, RawAction.events, checkFrom] using
            ih env.reset { s with anchors := [] } h'
      | endDocument =>
          have h' : (env.reset).anchors =
              ({ s with anchors := [] } : GraphState).anchors.map Prod.fst := rfl
          simpa [rawActionCheck, projectedEvents, RawAction.events, checkFrom] using
            ih env.reset { s with anchors := [] } h'
      | nodeStart anchor =>
          cases anchor with
          | none =>
              have h' : env.anchors =
                  (allocateNodeStart s none).2.anchors.map Prod.fst := by
                simpa [allocateNodeStart, alloc, bind] using h
              simpa [rawActionCheck, projectedEvents, RawAction.events, checkFrom] using
                ih env (allocateNodeStart s none).2 h'
          | some name =>
              have h' : ({env with anchors := name :: env.anchors} : Env).anchors =
                  (allocateNodeStart s (some name)).2.anchors.map Prod.fst := by
                simp [allocateNodeStart, alloc, bind, h]
              simpa [rawActionCheck, projectedEvents, RawAction.events, checkFrom] using
                ih {env with anchors := name :: env.anchors}
                   (allocateNodeStart s (some name)).2 h'
      | aliasUse name =>
          by_cases ha : AliasAllowed env name
          · have ht : (aliasTarget s name).isSome = true :=
              (aliasTarget_exists_iff_allowed env s name h).2 ha
            simpa [rawActionCheck, projectedEvents, RawAction.events,
                   checkFrom, ha, ht] using ih env s h
          · have ht : (aliasTarget s name).isSome = false := by
              cases hs : (aliasTarget s name).isSome with
              | false => rfl
              | true =>
                  exact False.elim (ha ((aliasTarget_exists_iff_allowed env s name h).1 hs))
            simp [rawActionCheck, projectedEvents, RawAction.events, checkFrom, ha, ht]

/-- Selective source-to-action extraction from the JPL serialization tree.
This function is EXECUTABLE, not yet a kernel-side proof that arbitrary
YAML source has a unique or faithful TraceOf derivation. -/
partial def rawTreeActions (value : YamlValue) : List RawAction :=
  match value with
  | .scalar scalar => [.nodeStart scalar.anchor]
  | .sequence _ items _ anchor =>
      .nodeStart anchor :: items.toList.flatMap rawTreeActions
  | .mapping _ pairs _ anchor =>
      .nodeStart anchor :: pairs.toList.flatMap
        (fun (key, value) => rawTreeActions key ++ rawTreeActions value)
  | .alias name => [.aliasUse name]

def rawDocumentPlan (document : YamlDocument) : List RawAction :=
  .beginDocument :: rawTreeActions document.value ++ [.endDocument]

def rawSourcePlanAllowed (input : String) : Bool :=
  match TokenParser.parseYamlRaw input with
  | .error _ => false
  | .ok docs => docs.all fun doc => rawActionCheck {} (rawDocumentPlan doc)

def indexedRawSourcePlanAllowed (input : String) : Bool :=
  match TokenParser.Indexed.parseYamlRawIx input with
  | .error _ => false
  | .ok docs => docs.all fun doc => rawActionCheck {} (rawDocumentPlan doc)

#guard rawSourcePlanAllowed "&x [*x]"
#guard indexedRawSourcePlanAllowed "&x [*x]"
#guard rawSourcePlanAllowed "[&x [&x 1], *x]"
#guard indexedRawSourcePlanAllowed "[&x [&x 1], *x]"
#guard rawSourcePlanAllowed "[&x 1, *x, &x 9, *x]"
#guard !(rawSourcePlanAllowed "[*x]")
#guard !(indexedRawSourcePlanAllowed "[*x]")
#guard !(rawSourcePlanAllowed "---\n&x 1\n---\n*x\n")

-- Finite adversarial event controls (the theorem itself quantifies over traces).
#guard graphTraceCheck {} [AnchorEvent.defineAnchor "x" 0, .useAlias "x"]
#guard graphTraceCheck {} [AnchorEvent.defineAnchor "x" 0,
                            AnchorEvent.defineAnchor "x" 1, .useAlias "x"]
#guard !(graphTraceCheck {} [AnchorEvent.useAlias "x"])
#guard !(graphTraceCheck {} [AnchorEvent.defineAnchor "x" 0,
                            .endDocument, .beginDocument, .useAlias "x"])
#guard aliasTarget (bind (bind ({} : GraphState) (some "x") 0) (some "x") 1) "x" == some 1
#guard (graphTraceCheck {} [AnchorEvent.defineAnchor "x" 0, .useAlias "x"]) ==
  checkFrom ({} : Env) ([AnchorEvent.defineAnchor "x" 0, .useAlias "x"].map
    AnchorEvent.asSerializationEvent)

partial def build (v : YamlValue) (s : GraphState) : Except String (Nat × GraphState) :=
  match v with
  | .scalar data => do
      let (id, s) := alloc s
      let s := bind s data.anchor id
      let json := L4YAML.Json.yamlToJson (.scalar data)
      return (id, assign s id (jsonNode "scalar" [("json", .str json)]))
  | .sequence _ items _ anchor => do
      let (id, s) := alloc s
      let s := bind s anchor id
      let (children, s) ← buildList items.toList s
      let node := jsonNode "sequence" [("items", Lean.toJson children)]
      return (id, assign s id node)
  | .mapping _ pairs _ anchor => do
      let (id, s) := alloc s
      let s := bind s anchor id
      let (children, s) ← buildPairs pairs.toList s
      let edges := children.map fun (k, v) =>
        Lean.Json.arr #[Lean.toJson k, Lean.toJson v]
      let node := jsonNode "mapping" [("pairs", Lean.Json.arr edges)]
      return (id, assign s id node)
  | .alias name =>
      match aliasTarget s name with
      | some id => .ok (id, s)
      | none => .error ("UNBOUND_ALIAS:" ++ name)
where
  buildList : List YamlValue → GraphState → Except String (Array Nat × GraphState)
    | [], s => .ok (#[], s)
    | h :: t, s => do
        let (id, s) ← build h s
        let (ids, s) ← buildList t s
        return (#[id] ++ ids, s)

  buildPairs : List (YamlValue × YamlValue) → GraphState →
      Except String (Array (Nat × Nat) × GraphState)
    | [], s => .ok (#[], s)
    | (key, value) :: t, s => do
        let (k, s) ← build key s
        let (v, s) ← build value s
        let (rest, s) ← buildPairs t s
        return (#[(k, v)] ++ rest, s)

def graphOf (doc : YamlDocument) : Except String Lean.Json := do
  let (root, s) ← build doc.value {}
  return Lean.Json.mkObj [
    ("root", Lean.toJson root),
    ("nodes", Lean.Json.arr s.nodes)
  ]

def graphsOf (docs : Array YamlDocument) : Except String Lean.Json := do
  let mut graphs : Array Lean.Json := #[]
  for doc in docs do
    let graph ← graphOf doc
    graphs := graphs.push graph
  return Lean.Json.arr graphs

def graphLegacy (input : String) : Except String Lean.Json := do
  match L4YAML.TokenParser.parseYamlRaw input with
  | .ok docs => graphsOf docs
  | .error err => .error (toString err)

def graphIndexed (input : String) : Except String Lean.Json := do
  match L4YAML.TokenParser.Indexed.parseYamlRawIx input with
  | .ok docs => graphsOf docs
  | .error err => .error (toString err)

def resultJson : Except String Lean.Json → Lean.Json
  | .ok data => Lean.Json.mkObj [("status", .str "ok"), ("graphs", data)]
  | .error err => Lean.Json.mkObj [("status", .str "error"), ("error", .str err)]

/-- Native scanner tokens are a source-linked authority boundary independent
from the parser's reconstructed YAML serialization tree. -/
def scannerAnchorOrder (source : String) : Except String (List String) :=
  match Scanner.scanFiltered source with
  | .error err => .error (toString err)
  | .ok tokens =>
      .ok (tokens.toList.filterMap fun pos =>
        match pos.val with
        | .anchor name => some ("&" ++ name)
        | .alias name => some ("*" ++ name)
        | _ => none)

/-- This is a parser-structure projection, not a theorem of source
TraceOf uniqueness. Only anchor/alias event order is compared. -/
def parsedAnchorOrder (docs : Array YamlDocument) : List String :=
  docs.toList.flatMap fun doc =>
    (rawTreeActions doc.value).filterMap fun a =>
      match a with
      | .nodeStart (some name) => some ("&" ++ name)
      | .aliasUse name => some ("*" ++ name)
      | _ => none

def traceOrderRecord (input : String) : Lean.Json := Id.run do
  let scanned := scannerAnchorOrder input
  let parsed := TokenParser.parseYamlRaw input
  let parsedIx := TokenParser.Indexed.parseYamlRawIx input
  let status := match scanned, parsed, parsedIx with
    | .ok a, .ok docs, .ok docsIx =>
        if a == parsedAnchorOrder docs &&
           parsedAnchorOrder docs == parsedAnchorOrder docsIx
        then "MATCH" else "MISMATCH"
    | _, _, _ => "REFUSED"
  let scannerEvents := match scanned with | .ok v => v | .error _ => []
  let treeEvents := match parsed with
    | .ok docs => parsedAnchorOrder docs
    | .error _ => []
  return Lean.Json.mkObj [
    ("input", .str input),
    ("status", .str status),
    ("scanner", Lean.toJson scannerEvents),
    ("raw_tree", Lean.toJson treeEvents)
  ]

def traceOrderMatched (source : String) : Bool :=
  match (traceOrderRecord source).getObjValAs? String "status" with
  | .ok status => status == "MATCH"
  | .error _ => false

#guard traceOrderMatched "&x [*x]"
#guard traceOrderMatched "[&x [&x 1], *x]"

end MathGraph.GraphCompose

open MathGraph.GraphCompose

def main (args : List String) : IO Unit := do
  let traceMode := args.head? == some "--trace"
  let pathOpt := if traceMode then (args.drop 1).head? else args.head?
  let some path := pathOpt
    | throw (IO.userError "pass JSONL input path")
  let data ← IO.FS.readFile path
  for line in data.splitOn "\n" do
    if line != "" then
      match Lean.Json.parse line with
      | .ok (.str source) =>
          let record := if traceMode then traceOrderRecord source else
            Lean.Json.mkObj [
              ("input", .str source),
              ("legacy", resultJson (graphLegacy source)),
              ("indexed", resultJson (graphIndexed source))
            ]
          IO.println record.compress
      | _ => throw (IO.userError "non-string JSONL input")

end
