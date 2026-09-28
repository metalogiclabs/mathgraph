import L4YAML.Proofs.Production.DocumentProduction
import CapstoneObstruction

/-!
# Current language relation

This theorem states the strongest exact fact about the advertised capstone at
the pinned L4YAML revision:

  executable parse language ⊂ current InYamlLanguage

The inclusion is upstream's existing parse strictness theorem.  Strictness is
witnessed by the independently kernel-checked malformed-directive example.
-/

namespace L4YAMLLanguageRelation

open L4YAML
open L4YAML.Surface

def ParseLanguage (input : String) : Prop :=
  ∃ docs, L4YAML.TokenParser.parseYaml input = .ok docs

theorem parse_language_subset_surface :
    ∀ input, ParseLanguage input → InYamlLanguage input := by
  intro input h
  obtain ⟨docs, hdocs⟩ := h
  exact L4YAML.Proofs.DocumentProduction.parse_strict_proof input docs hdocs

theorem malformed_directive_not_in_parse_language :
    ¬ ParseLanguage "%YAML .2\n---" := by
  rintro ⟨docs, hdocs⟩
  exact L4YAMLCapstoneObstruction.malformed_yaml_version_has_no_parse docs hdocs

/-- The current executable language is a proper subset of the current surface
    language.  This is stronger than merely saying the proposed biconditional
    has not yet been proved. -/
theorem parse_language_strictly_smaller_than_surface :
    (∀ input, ParseLanguage input → InYamlLanguage input) ∧
    (∃ input, InYamlLanguage input ∧ ¬ ParseLanguage input) := by
  refine ⟨parse_language_subset_surface, ?_⟩
  exact ⟨"%YAML .2\n---",
    L4YAMLCapstoneObstruction.malformed_yaml_version_is_in_surface,
    malformed_directive_not_in_parse_language⟩

end L4YAMLLanguageRelation
