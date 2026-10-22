module
public import L4YAML

-- Intentionally outside a public section, to exercise private-name deriving.
open L4YAML

structure ExternalQ where
  x : Option String
  y : Bool
deriving BEq, L4YAML.Schema.FromYaml, L4YAML.Schema.ToYaml

#guard ((parseAs ExternalQ "x: \"null\"\ny: true\n").toOption ==
  some ({ x := some "null", y := true } : ExternalQ))
#guard ((parseAs ExternalQ "x: null\ny: false\n").toOption ==
  some ({ x := none, y := false } : ExternalQ))

-- Derived ToYaml, emitter and typed reparse must agree on distinct payloads.
#guard ((parseAs ExternalQ (Dump.dump (toYaml
  ({ x := some "null", y := true } : ExternalQ)))).toOption ==
  some ({ x := some "null", y := true } : ExternalQ))
#guard ((parseAs ExternalQ (Dump.dump (toYaml
  ({ x := none, y := true } : ExternalQ)))).toOption ==
  some ({ x := none, y := true } : ExternalQ))
