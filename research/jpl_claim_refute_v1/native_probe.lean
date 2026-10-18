import L4YAML.Parser.Composition

/-!
Source-exact *native* executable controls, NOT an attempted proof of all YAML
1.2.2. The author already documented these separator families. The purpose
is to independently replay the current implementation and control the
claim-to-warrant classification under a pinned source.

Lean toolchain and upstream revision are pinned in the workflow.
-/

open L4YAML.TokenParser

def auditAccepts (s : String) : Bool :=
  match parseYaml s with
  | .ok _    => true
  | .error _ => false

-- Real positive controls: normal scalar and anchored alias use.
#guard auditAccepts "---\nfoo: bar\n"
#guard auditAccepts "---\na: &a bar\nb: *a\n"

-- Real negative controls: known stateful grammar/serialization barriers.
#guard !(auditAccepts "*x")
#guard !(auditAccepts "!h!x")
#guard !(auditAccepts "&x [*x]")
#guard !(auditAccepts "%YAML .2\n---\n")

-- These witnesses *reproduce* documented old work, not new refutations.
