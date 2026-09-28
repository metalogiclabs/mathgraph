import L4YAML.Surface.Document
import L4YAML.Parser.Composition

/-!
# L4YAML semantic obstruction to parse_iff_grammar

The current capstone equates executable parse success with the context-free-ish
surface predicate `InYamlLanguage`.

But the executable scanner enforces a stateful semantic condition that the
surface grammar does not encode: an alias must refer to an anchor defined
earlier in the stream.

Therefore an unbound alias can have an exact surface derivation using ordinary
spec-facing constructors while `parseYaml` rejects it before parsing.

This obstruction is independent of `SLYamlStream.scannerDrop` and independent
of the simplified directive production.
-/

namespace L4YAMLSemanticObstruction

open L4YAML
open L4YAML.Surface
open L4YAML.CharPredicates

def parseAccepts (s : String) : Bool :=
  match L4YAML.TokenParser.parseYaml s with
  | .ok _ => true
  | .error _ => false

example : parseAccepts "*x" = false := by native_decide

/-- `*x` is syntactically a YAML alias node in the current surface grammar. -/
theorem unbound_alias_is_in_surface :
    InYamlLanguage "*x" := by
  let s0 : SurfPos := ⟨['*', 'x'], 0⟩
  let s1 : SurfPos := ⟨['x'], 1⟩
  let s2 : SurfPos := ⟨[], 2⟩

  have hx : GChar isNsAnchorChar s1 s2 := by
    exact GChar.mk 'x' [] 1 (by
      simp [isNsAnchorChar, isNsChar, isLineBreakProp, isLineFeedProp,
        isCarriageReturnProp, isWhiteSpaceProp, isSpaceProp, isTabProp,
        isPrintableProp, isFlowIndicatorProp])

  have hname : GPlus (GChar isNsAnchorChar) s1 s2 :=
    GPlus.mk s1 s2 s2 hx (GStar.nil s2)

  have halias : SCNsAliasNode s0 s2 :=
    SCNsAliasNode.mk ['x'] 0 s2 hname

  have hflow : SFlowNode 0 .flowOut s0 s2 :=
    SFlowNode.alias 0 .flowOut s0 s2 halias

  have hsep : SSeparate 0 .flowOut s0 s0 := by
    exact SSeparateLines.inline 0 s0 s0 (SSeparateInLine.startOfLine s0)

  have heof : SSLComments s2 s2 :=
    SSLComments.withComment s2 s2 s2
      (SSBComment.noSep s2 s2 (SBComment.eof 2))
      (GStar.nil s2)

  have hblock : SBlockNode 0 .blockIn s0 s2 :=
    SBlockNode.flowInBlock 0 .blockIn s0 s0 s2 s2 hsep hflow heof

  have hbare : SLBareDocument s0 s2 :=
    SLBareDocument.mk s0 s2 hblock

  have hstream : SLYamlStream s0 s2 :=
    SLYamlStream.single s0 s0 s2 s2
      (GStar.nil s0)
      (GOpt.some s0 s2 (SLAnyDocument.bare s0 s2 hbare))
      (GStar.nil s2)

  exact ⟨s2, hstream, rfl⟩

theorem unbound_alias_has_no_parse
    (docs : Array YamlDocument) :
    L4YAML.TokenParser.parseYaml "*x" ≠ .ok docs := by
  intro h
  have hrejected : parseAccepts "*x" = false := by native_decide
  unfold parseAccepts at hrejected
  rw [h] at hrejected
  contradiction

/-- A second kernel-level counterexample to the advertised capstone, arising
    from parser/scanner semantic validation rather than a relaxed local grammar
    production. -/
theorem parse_iff_grammar_semantic_obstruction :
    ¬ ((∃ docs, L4YAML.TokenParser.parseYaml "*x" = .ok docs) ↔
       InYamlLanguage "*x") := by
  intro h
  obtain ⟨docs, hdocs⟩ := h.mpr unbound_alias_is_in_surface
  exact unbound_alias_has_no_parse docs hdocs

end L4YAMLSemanticObstruction

-- qualification trigger
