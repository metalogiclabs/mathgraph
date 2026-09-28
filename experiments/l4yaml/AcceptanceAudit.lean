import L4YAML.Parser.Composition

namespace L4YAMLAcceptanceAudit

open L4YAML

def resultTag (s : String) : String :=
  match TokenParser.parseYaml s with
  | .ok _ => "OK"
  | .error e => "ERR: " ++ toString e

#eval ("doc-start-inline", resultTag "--- foo")
#eval ("doc-start-inline-map", resultTag "--- a: b")
#eval ("unbound-alias", resultTag "*x")
#eval ("undeclared-tag-handle", resultTag "!h!x")
#eval ("duplicate-yaml-directive", resultTag "%YAML 1.2\n%YAML 1.2\n---")
#eval ("malformed-yaml-version", resultTag "%YAML .2\n---")
#eval ("secondary-tag-empty", resultTag "!!")
#eval ("named-tag-empty-suffix", resultTag "!h!")
#eval ("block-header-dup-chomp", resultTag "|++\n")
#eval ("block-header-dup-indent", resultTag "|11\n")

end L4YAMLAcceptanceAudit
