import L4YAML.Parser.Composition
import L4YAML.Proofs.Composition
import L4YAML.Surface.Document

/-!
# L4YAML corrected capstone boundary

The current proposed capstone compares a pure surface predicate directly with
the full executable load pipeline.  The probes in this directory show that
those are not currently extensionally equal.

This file factors the theorem at the actual executable boundary.

`InExecutableLanguage input` means exactly that scanning and token parsing
both succeed.  Composition is total, so `parseYaml` success is equivalent to
this predicate.  The genuinely missing language theorem is therefore the
separate bridge between an exact, semantically well-formed surface language and
`InExecutableLanguage`.
-/

namespace L4YAMLCorrectedCapstone

open L4YAML

/-- The exact acceptance language of scanner + token parser, before the total
    Compose map is applied. -/
def InExecutableLanguage (input : String) : Prop :=
  ∃ (tokens : Array (Positioned YamlToken)) (rawDocs : Array YamlDocument),
    Scanner.scanFiltered input = .ok tokens ∧
    TokenParser.parseStream tokens = .ok rawDocs

/-- Scanner-only acceptance, useful for pinning the flow-adjacency boundary. -/
def InScannerLanguage (input : String) : Prop :=
  ∃ tokens : Array (Positioned YamlToken),
    Scanner.scanFiltered input = .ok tokens

/-- The final Compose map is total, so it does not change the accepted
    input language. Any acceptance mismatch with the surface specification is
    already present in the raw scanner+parser pipeline. -/
theorem parse_acceptance_iff_raw_acceptance (input : String) :
    (∃ docs, TokenParser.parseYaml input = .ok docs) ↔
    (∃ rawDocs, TokenParser.parseYamlRaw input = .ok rawDocs) := by
  constructor
  · rintro ⟨docs, h⟩
    unfold TokenParser.parseYaml at h
    split at h
    · rename_i rawDocs hraw
      exact ⟨rawDocs, hraw⟩
    · contradiction
  · rintro ⟨rawDocs, hraw⟩
    exact ⟨rawDocs.map YamlDocument.compose,
      L4YAML.Proofs.Composition.parseYaml_of_parseYamlRaw_ok input rawDocs hraw⟩

/-- Full `parseYaml` acceptance is exactly scanner+parser acceptance.  No
    surface-grammar assumptions are needed here. -/
theorem parse_iff_executable_language (input : String) :
    (∃ docs, TokenParser.parseYaml input = .ok docs) ↔
      InExecutableLanguage input := by
  constructor
  · rintro ⟨docs, h⟩
    unfold TokenParser.parseYaml at h
    split at h
    · rename_i rawDocs hraw
      obtain ⟨tokens, hscan, hparse⟩ :=
        L4YAML.Proofs.Composition.parseYamlRaw_ok_decompose input rawDocs hraw
      exact ⟨tokens, rawDocs, hscan, hparse⟩
    · contradiction
  · rintro ⟨tokens, rawDocs, hscan, hparse⟩
    exact ⟨rawDocs.map YamlDocument.compose,
      L4YAML.Proofs.Composition.parseYaml_pipeline
        input tokens rawDocs hscan hparse⟩

/-- Executable acceptance always implies scanner acceptance. -/
theorem executable_implies_scanner (input : String) :
    InExecutableLanguage input → InScannerLanguage input := by
  rintro ⟨tokens, rawDocs, hscan, hparse⟩
  exact ⟨tokens, hscan⟩

end L4YAMLCorrectedCapstone
