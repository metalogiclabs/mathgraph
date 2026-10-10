import L4YAML.Proofs.Serialization

/-!
Independent replay against pinned public nasa-jpl/L4YAML proof objects, not
a substitute for a parser-to-normative-surface theorem.
Proof dependencies remain in the original JPL checkout. No local copy of
the proof or redefinition of source claims is accepted here.
-/

open L4YAML.Proofs.Serialization.SerializationWellFormed
open L4YAML.Proofs.Serialization.CommitTrace

example :
    SerializationWellFormed (yamlNodeEvents (.anchored "x" (.alias "x"))) :=
  yaml_enclosing_anchor_self_reference_allowed "x"

example :
    ¬ SerializationWellFormed (l4yamlNodeEvents (.anchored "x" (.alias "x"))) :=
  current_l4yaml_enclosing_anchor_self_reference_rejected "x"

example :
    SerializationWellFormed
      (l4yamlNodesEvents [.anchored "x" .atom, .alias "x"]) :=
  later_sibling_alias_allowed "x"

example (input : String) :
    (∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs) ↔
      L4YAML.Proofs.Serialization.InExecutableLanguage input :=
  L4YAML.Proofs.Serialization.parse_iff_executable_language input

#print axioms L4YAML.Proofs.Serialization.CommitTrace.yaml_enclosing_anchor_self_reference_allowed
#print axioms L4YAML.Proofs.Serialization.CommitTrace.current_l4yaml_enclosing_anchor_self_reference_rejected
#print axioms L4YAML.Proofs.Serialization.CommitTrace.later_sibling_alias_allowed
#print axioms L4YAML.Proofs.Serialization.parse_iff_executable_language
