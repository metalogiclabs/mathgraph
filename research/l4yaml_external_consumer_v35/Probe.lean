module
public import L4YAML

-- Intentionally outside a public section, to exercise private-name deriving.
open L4YAML

structure ExternalQ where
  x : Option String
  y : Bool
deriving BEq, L4YAML.Schema.FromYaml, L4YAML.Schema.ToYaml

-- No #guard/#eval here: those are meta programs, requiring additional
-- meta imports not needed by an ordinary compiled downstream consumer.
-- The source-native 125-case suite tests runtime values separately.
def sourceFacingChecks : Array Bool := #[
  (parseAs ExternalQ "x: \"null\"\ny: true\n").toOption ==
    some ({ x := some "null", y := true } : ExternalQ),
  (parseAs ExternalQ "x: null\ny: false\n").toOption ==
    some ({ x := none, y := false } : ExternalQ),
  (parseAs ExternalQ (Dump.dump (toYaml
    ({ x := some "null", y := true } : ExternalQ)))).toOption ==
    some ({ x := some "null", y := true } : ExternalQ),
  (parseAs ExternalQ (Dump.dump (toYaml
    ({ x := none, y := true } : ExternalQ)))).toOption ==
    some ({ x := none, y := true } : ExternalQ)
]
