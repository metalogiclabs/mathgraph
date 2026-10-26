module

public import L4YAML.Parser.Composition
public import L4YAML.Parser.IndexedComposition
public import Lean.Data.Json
public meta import L4YAML.Parser.Composition
public meta import L4YAML.Parser.IndexedComposition

@[expose] public section

open L4YAML

/-- Observe loading, not JSON serialization: YAML alias graphs can be cyclic. -/
def legacyAccept (input : String) : Bool :=
  (TokenParser.parseYaml input).isOk

def indexedAccept (input : String) : Bool :=
  (TokenParser.Indexed.parseYamlSingleIx input).isOk

-- Deliberately stale historical assertion for the RED characterization run:
-- an older parser epoch refused this legal self-alias.
#guard legacyAccept "&x [*x]" == false
#guard indexedAccept "&x [*x]" == false

-- Independent positive/negative controls.
#guard legacyAccept "[&x 1, *x]"
#guard indexedAccept "[&x 1, *x]"
#guard !legacyAccept "[*x]"
#guard !indexedAccept "[*x]"

def cases : Array (String × String) := #[
  ("flow-sequence-self", "&x [*x]"),
  ("flow-mapping-self", "&x {a: *x}"),
  ("block-sequence-self", "&x\n- *x\n"),
  ("declared-before-use", "[&x 1, *x]"),
  ("dangling-alias", "[*x]"),
  ("missing-inside-cycle", "&x [*x, *y]")
]

def main : IO Unit := do
  for (kind, source) in cases do
    IO.println (Lean.Json.mkObj [
      ("kind", .str kind),
      ("input", .str source),
      ("legacy_accept", Lean.toJson (legacyAccept source)),
      ("indexed_accept", Lean.toJson (indexedAccept source))]).compress

end
