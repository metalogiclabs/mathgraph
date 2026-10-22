import Lake
open Lake DSL

-- This is an independently authored consumer, not part of L4YAML.
package l4yaml_external_consumer where
  requiresModuleSystem := true

require L4YAML from git
  "https://github.com/nasa-jpl/L4YAML.git" @ "c65755071dd91025b043b6f5e51ddb6578e9746b"

@[default_target]
lean_lib Probe where
  roots := #[`Probe]
