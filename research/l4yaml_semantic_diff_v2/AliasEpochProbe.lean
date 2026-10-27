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

-- Current source declares anchors at node start and resolves them at completion.
-- These self-cycles are legal; historical RED witness: CI run 40249383652.
#guard legacyAccept "&x [*x]"
#guard indexedAccept "&x [*x]"
#guard legacyAccept "&x {a: *x}"
#guard indexedAccept "&x {a: *x}"
#guard legacyAccept "&x\n- *x\n"
#guard indexedAccept "&x\n- *x\n"

-- Independent positive/negative controls.
#guard legacyAccept "[&x 1, *x]"
#guard indexedAccept "[&x 1, *x]"
#guard !legacyAccept "[*x]"
#guard !indexedAccept "[*x]"
#guard !legacyAccept "&x [*x, *y]"
#guard !indexedAccept "&x [*x, *y]"

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
