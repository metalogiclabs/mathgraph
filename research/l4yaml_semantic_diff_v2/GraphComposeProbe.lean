module
public import L4YAML.Parser.Composition
public import L4YAML.Parser.IndexedComposition
public import L4YAML.Output.Json
public import Lean.Data.Json
public meta import L4YAML.Parser.Composition
public meta import L4YAML.Parser.IndexedComposition
public meta import L4YAML.Output.Json

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
      let node := jsonNode "sequence" [("items", toJson children)]
      return (id, assign s id node)
  | .mapping _ pairs _ anchor => do
      let (id, s) := alloc s
      let s := bind s anchor id
      let (children, s) ← buildPairs pairs.toList s
      let edges := children.map fun (k, v) =>
        Lean.Json.arr #[toJson k, toJson v]
      let node := jsonNode "mapping" [("pairs", Lean.Json.arr edges)]
      return (id, assign s id node)
  | .alias name =>
      match s.anchors.findSome? (fun (n, idx) => if n == name then some idx else none) with
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
    ("root", toJson root),
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

end MathGraph.GraphCompose

open MathGraph.GraphCompose

def main (args : List String) : IO Unit := do
  let some path := args.head?
    | throw (IO.userError "pass JSONL input path")
  let data ← IO.FS.readFile path
  for line in data.splitOn "\n" do
    if line != "" then
      match Lean.Json.parse line with
      | .ok (.str source) =>
          let record := Lean.Json.mkObj [
            ("input", .str source),
            ("legacy", resultJson (graphLegacy source)),
            ("indexed", resultJson (graphIndexed source))
          ]
          IO.println record.compress
      | _ => throw (IO.userError "non-string JSONL input")

end
