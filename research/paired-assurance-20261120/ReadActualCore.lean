import L4YAML.Schema.Schema
/-! Read-only source-native diagnostic of the actual L4YAML Core Schema resolver.
The external YAML tag expectations live in the frozen research protocol, not here.
This emits actual constructor tags from L4YAML.Schema.resolveImplicit. -/

open L4YAML.Schema

def observedTag : YamlType → String
  | .null => "null"
  | .bool _ => "bool"
  | .int _ => "int"
  | .float _ => "float"
  | .str _ => "str"
  | .seq _ => "seq"
  | .map _ => "map"

def main : IO Unit := do
  let inputs : List String :=
    ["1_000", "1000", "0x", "0", "1.", "1.0",
     "true", "hello", "0x3A", "null", ".inf", "yes"]
  for input in inputs do
    IO.println (input ++ "\t" ++ observedTag (resolveImplicit input))
