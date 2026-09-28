import CapstoneObstruction
import SemanticObstruction
import CorrectedCapstone

/-!
# L4YAML advertised-capstone no-go theorem

This file combines the independently kernel-checked counterexamples into the
actual universal statement Nicolas's plan aims to establish.

The result is not that a proof is difficult: the universal biconditional is
false at the pinned upstream revision.

Two independent witnesses are retained:
* a local surface-grammar over-approximation (%YAML .2);
* a stateful semantic mismatch (unbound alias *x).

Either one alone refutes the universal theorem.
-/

namespace L4YAMLNoGo

open L4YAML
open L4YAML.Surface

theorem advertised_parse_iff_grammar_is_false :
    ¬ (∀ input : String,
      ((∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs) ↔
       InYamlLanguage input)) := by
  intro h
  exact L4YAMLCapstoneObstruction.parse_iff_grammar_current_statement_false
    (h "%YAML .2\n---")

theorem advertised_parse_iff_grammar_is_false_semantically :
    ¬ (∀ input : String,
      ((∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs) ↔
       InYamlLanguage input)) := by
  intro h
  exact L4YAMLSemanticObstruction.parse_iff_grammar_semantic_obstruction
    (h "*x")

/-- The problem factors cleanly: the full load pipeline already has an exact
    biconditional with scanner+token-parser acceptance.  The missing theorem
    must therefore relate a corrected surface/semantic language to that
    executable language, rather than trying to prove the false statement
    above. -/
theorem executable_factorization (input : String) :
    (∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs) ↔
      L4YAMLCorrectedCapstone.InExecutableLanguage input :=
  L4YAMLCorrectedCapstone.parse_iff_executable_language input

end L4YAMLNoGo

#print axioms L4YAMLNoGo.advertised_parse_iff_grammar_is_false
