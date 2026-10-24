module

public import L4YAML.Output.Json
public import L4YAML.Output.Events
public import L4YAML.Output.JsonIx
public import Lean.Data.Json
public meta import L4YAML.Output.Json
public meta import L4YAML.Output.Events
public meta import L4YAML.Output.JsonIx

@[expose] public section

open L4YAML

def optionString (v : Option String) : Lean.Json :=
  match v with | some s => .str s | none => .null

partial def shape (v : YamlValue) : Lean.Json :=
  match v with
  | .scalar s => Lean.Json.mkObj [
      ("kind", .str "scalar"), ("content", .str s.content),
      ("anchor", optionString s.anchor), ("tag", optionString s.tag)]
  | .sequence _ items tag anchor => Lean.Json.mkObj [
      ("kind", .str "sequence"), ("items", .arr (items.map shape)),
      ("anchor", optionString anchor), ("tag", optionString tag)]
  | .mapping _ pairs tag anchor => Lean.Json.mkObj [
      ("kind", .str "mapping"),
      ("pairs", .arr (pairs.map fun (k,v) => Lean.Json.arr #[shape k, shape v])),
      ("anchor", optionString anchor), ("tag", optionString tag)]
  | .alias name => Lean.Json.mkObj [("kind", .str "alias"), ("name", .str name)]

def docsResult (result : Except ScanError (Array YamlDocument)) : Lean.Json :=
  match result with
  | .ok docs => Lean.Json.mkObj [
      ("status", .str "ok"), ("values", .arr (docs.map fun d => shape d.value))]
  | .error e => Lean.Json.mkObj [("status", .str "error"), ("error", .str (toString e))]

def stringResult (result : Except ScanError String) : Lean.Json :=
  match result with
  | .ok value => Lean.Json.mkObj [("status", .str "ok"), ("value", .str value)]
  | .error e => Lean.Json.mkObj [("status", .str "error"), ("error", .str (toString e))]

def cases : List (String × String) := [
  ("same-name-seq", "[&x [&x 1], *x]"),
  ("same-name-seq-both-aliases", "[&x [&x 1, *x], *x]"),
  ("same-name-map", "a: &x {b: &x 1}\nc: *x\n"),
  ("same-name-map-both-aliases", "a: &x {b: &x 1, c: *x}\nd: *x\n"),
  ("sibling-rebind", "[&x 1, *x, &x 2, *x]"),
  ("nested-distinct", "[&o [&x 1], *x, *o]"),
  ("noalias-same-name", "[&x [&x 1]]"),
  ("same-name-string", "[&x [&x inner], *x]"),
  ("single-anchor", "[&x 1, *x]"),
  ("no-alias", "[1,[2]]"),
  ("selfcycle-policy", "&x [*x]"),
  ("rebound-selfcycle-policy", "[&x 0, &x [*x]]"),
  ("undefined-alias-control", "[*missing]")
]

def main : IO Unit := do
  for (name, input) in cases do
    let raw := TokenParser.parseYamlRaw input
    let composed := raw.map fun docs => docs.map YamlDocument.compose
    let row := Lean.Json.mkObj [
      ("case", .str name), ("input", .str input),
      ("raw", docsResult raw),
      ("composed", docsResult composed),
      ("public_load", docsResult (TokenParser.parseYaml input)),
      ("indexed_raw", docsResult (TokenParser.Indexed.parseYamlRawIx input)),
      ("indexed_load", docsResult (TokenParser.Indexed.parseYamlIx input)),
      ("json", stringResult (L4YAML.Json.streamToJson input)),
      ("indexed_json", stringResult (L4YAML.Json.streamToJsonIx input)),
      ("events", stringResult (L4YAML.Events.streamToEvents input))]
    IO.println row.compress

end
