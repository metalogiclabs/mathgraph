module

public import L4YAML.Schema.Api
public import Lean.Data.Json
public meta import L4YAML.Schema.Api

@[expose] public section

def typedValueJson (value : L4YAML.Schema.YamlType) : Lean.Json :=
  match value with
  | .str s => Lean.Json.mkObj [("kind", .str "str"), ("value", .str s)]
  | .bool b => Lean.Json.mkObj [("kind", .str "bool"), ("value", Lean.toJson b)]
  | .null => Lean.Json.mkObj [("kind", .str "null"), ("value", Lean.Json.null)]
  | .int n => Lean.Json.mkObj [("kind", .str "int"), ("value", Lean.toJson n)]
  | _ => Lean.Json.mkObj [("kind", .str "UNSUPPORTED")]

def scalarCase (source : String) : Lean.Json := Id.run do
  let result := match L4YAML.parseTyped source with
    | .ok (.map pairs) =>
      if pairs.size == 1 then typedValueJson pairs[0]!.2
      else Lean.Json.mkObj [("kind", .str "UNEXPECTED_MAP")]
    | _ => Lean.Json.mkObj [("kind", .str "PARSE_REFUSAL")]
  return Lean.Json.mkObj [("input", .str source), ("result", result)]

def main : IO Unit := do
  let cases := #[
    "k: \"true\"\n", "k: true\n", "k: \"null\"\n", "k: null\n",
    "k: \"42\"\n", "k: 42\n", "k: !!str true\n", "k: !!bool 'true'\n"]
  for source in cases do
    IO.println (scalarCase source).compress

end
