module

public import L4YAML.Parser.Composition
public import L4YAML.Parser.IndexedComposition
public import Lean.Data.Json
public meta import L4YAML.Parser.Composition
public meta import L4YAML.Parser.IndexedComposition

@[expose] public section

open L4YAML

-- Exact, ordered source-derived examples from upstream scanner PR #89's guard.
def flowCases : Array String := #[
  "{a:[1]}", "[a:[1]]", "{a:{b: c}}", "[a:{b: c}]", "{a:[]}",
  "{a:{}}", "{a :[1]}", "{:[1]}", "[:[1]]", "{? a :[1]}",
  "[? a :[1]]", "{\"a\":b}", "{\"a\":[1]}", "{'a':{b: c}}",
  "{[a]:[1]}", "{a: [1]}", "{a:b}", "{a:\"x\"}", "a: [1]"
]

def main : IO Unit := do
  for source in flowCases do
    let legacy := (TokenParser.parseYaml source).isOk
    let indexed := (TokenParser.Indexed.parseYamlSingleIx source).isOk
    IO.println (Lean.Json.mkObj [
      ("input", .str source),
      ("legacy", Lean.toJson legacy),
      ("indexed", Lean.toJson indexed)]).compress

end
