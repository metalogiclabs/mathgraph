module

public import L4YAML.Output.Json
public import L4YAML.Output.JsonIx
public import L4YAML.Parser.IndexedComposition
public import Lean.Data.Json
public meta import L4YAML.Output.Json
public meta import L4YAML.Output.JsonIx
public meta import L4YAML.Parser.IndexedComposition

@[expose] public section

open L4YAML

namespace MathGraph.L4YAMLExperiment

/-!
Bounded, independent counterfactual against the immutable JPL parser.
The SOURCE serialization tree comes from the unmodified JPL code.
Only the Compose timing is changed here. This returns a value tree,
NOT a representation graph with node identity, so cyclic fidelity
and universal correctness remain UNKNOWN.

The claim tested: do the nested rebindings resolve differently if a
collection anchor enters the lexical/event-order environment when
its node STARTS instead of after its children have been processed?
-/

/-- Experimental tree-valued approximation to start-event anchor binding.
The raw collection value is used for early lookup. This deliberately
does not purport to preserve cyclic graph identity. -/
def resolveStart (v : YamlValue)
    (env : List (String × YamlValue) := []) :
    YamlValue × List (String × YamlValue) :=
  match v with
  | .scalar s =>
      (v, match s.anchor with
        | some a => (a, YamlValue.scalar { s with anchor := none } |>.adaptForFlowContext) :: env
        | none => env)
  | .sequence style items tag anchor =>
      let started := match anchor with
        | some a => (a, v.stripAnchors.adaptForFlowContext) :: env
        | none => env
      let r := goList items.toList started
      (YamlValue.sequence style r.fst.toArray tag anchor, r.snd)
  | .mapping style pairs tag anchor =>
      let started := match anchor with
        | some a => (a, v.stripAnchors.adaptForFlowContext) :: env
        | none => env
      let r := goPairs pairs.toList started
      (YamlValue.mapping style r.fst.toArray tag anchor, r.snd)
  | .alias name =>
      match env.findSome? (fun (n, val) => if n == name then some val else none) with
      | some val => (val, env)
      | none => (v, env)
where
  goList : List YamlValue → List (String × YamlValue)
      → List YamlValue × List (String × YamlValue)
    | [], env => ([], env)
    | v :: rest, env =>
        let r := resolveStart v env
        let rs := goList rest r.snd
        (r.fst :: rs.fst, rs.snd)

  goPairs : List (YamlValue × YamlValue) → List (String × YamlValue)
      → List (YamlValue × YamlValue) × List (String × YamlValue)
    | [], env => ([], env)
    | (k, v) :: rest, env =>
        let rk := resolveStart k env
        let rv := resolveStart v rk.snd
        let rs := goPairs rest rv.snd
        ((rk.fst, rv.fst) :: rs.fst, rs.snd)

/-- Use raw source-native documents, change Compose *only*. -/
def composeStart (doc : YamlDocument) : YamlDocument :=
  { doc with
    value := (resolveStart doc.value).fst.stripAnchors
    anchors := #[] }

def asJson : Except ScanError String → Lean.Json
  | .ok output => Lean.Json.mkObj [("status", .str "ok"), ("value", .str output)]
  | .error e => Lean.Json.mkObj [("status", .str "error"), ("error", .str (toString e))]

def legacyEventTime (input : String) : Except ScanError String :=
  match TokenParser.parseYamlRaw input with
  | .ok docs => .ok (Json.docsToJson (docs.map composeStart))
  | .error e => .error e

def indexedEventTime (input : String) : Except ScanError String :=
  match TokenParser.Indexed.parseYamlRawIx input with
  | .ok docs => .ok (Json.docsToJson (docs.map composeStart))
  | .error e => .error e

end MathGraph.L4YAMLExperiment

open MathGraph.L4YAMLExperiment

def main (args : List String) : IO Unit := do
  let some path := args.head?
    | throw (IO.userError "JSONL input path required")
  let input ← IO.FS.readFile path
  for line in input.splitOn "\n" do
    if line != "" then
      match Lean.Json.parse line with
      | .ok (.str source) =>
          IO.println (Lean.Json.mkObj [
            ("input", .str source),
            ("original_legacy", asJson (Json.streamToJson source)),
            ("original_indexed", asJson (Json.streamToJsonIx source)),
            ("event_legacy", asJson (legacyEventTime source)),
            ("event_indexed", asJson (indexedEventTime source))
          ]).compress
      | _ => throw (IO.userError "invalid non-string JSONL row")

end
