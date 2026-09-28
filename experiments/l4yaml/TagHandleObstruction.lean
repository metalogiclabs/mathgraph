import L4YAML.Surface.Document
import L4YAML.Parser.Composition

/-!
# L4YAML undeclared-tag-handle obstruction

A named tag handle is syntactically admitted by the surface production
`SCNsTagProperty.named` independently of any preceding `%TAG` directive.
The executable parser, however, carries a per-document tag-handle environment
and rejects undeclared named handles.

This is a second stateful semantic obstruction to the proposed
`parse_iff_grammar` capstone, independent of `scannerDrop` and of malformed
`%YAML` directive syntax.
-/

namespace L4YAMLTagHandleObstruction

open L4YAML
open L4YAML.Surface
open L4YAML.CharPredicates

def parseAccepts (s : String) : Bool :=
  match L4YAML.TokenParser.parseYaml s with
  | .ok _ => true
  | .error _ => false

example : parseAccepts "!h!x" = false := by native_decide

theorem undeclared_named_tag_is_in_surface :
    InYamlLanguage "!h!x" := by
  let s0 : SurfPos := ⟨['!', 'h', '!', 'x'], 0⟩
  let s1 : SurfPos := ⟨['!', 'x'], 2⟩
  let s2 : SurfPos := ⟨['x'], 3⟩
  let s3 : SurfPos := ⟨[], 4⟩

  have hh : GChar isWordCharProp ⟨['h', '!', 'x'], 1⟩ s1 := by
    exact GChar.mk 'h' ['!', 'x'] 1 (by native_decide)
  have hhandle : GPlus (GChar isWordCharProp) ⟨['h', '!', 'x'], 1⟩ s1 :=
    GPlus.mk _ s1 s1 hh (GStar.nil s1)
  have hbang : GLit '!' s1 s2 := by
    exact GLit.mk ['x'] 2
  have hx : GChar isTagCharProp s2 s3 := by
    exact GChar.mk 'x' [] 3 (by native_decide)
  have hsuffix : GStar (GChar isTagCharProp) s2 s3 :=
    GStar.cons s2 s3 s3 hx (GStar.nil s3)

  have htag : SCNsTagProperty s0 s3 :=
    SCNsTagProperty.named ['h', '!', 'x'] 0 s1 s2 s3
      hhandle hbang hsuffix

  have hprops : SCNsProperties 0 .flowOut s0 s3 :=
    SCNsProperties.tagFirst 0 .flowOut s0 s3 s3
      htag (GOpt.none s3)

  have hflow : SFlowNode 0 .flowOut s0 s3 :=
    SFlowNode.propsEmpty 0 .flowOut s0 s3 hprops

  have hsep : SSeparate 0 .flowOut s0 s0 := by
    exact SSeparateLines.inline 0 s0 s0 (SSeparateInLine.startOfLine s0)

  have heof : SSLComments s3 s3 :=
    SSLComments.withComment s3 s3 s3
      (SSBComment.noSep s3 s3 (SBComment.eof 4))
      (GStar.nil s3)

  have hblock : SBlockNode 0 .blockIn s0 s3 :=
    SBlockNode.flowInBlock 0 .blockIn s0 s0 s3 s3 hsep hflow heof

  have hbare : SLBareDocument s0 s3 :=
    SLBareDocument.mk s0 s3 hblock

  have hstream : SLYamlStream s0 s3 :=
    SLYamlStream.single s0 s0 s3 s3
      (GStar.nil s0)
      (GOpt.some s0 s3 (SLAnyDocument.bare s0 s3 hbare))
      (GStar.nil s3)

  exact ⟨s3, hstream, rfl⟩

theorem undeclared_named_tag_has_no_parse
    (docs : Array YamlDocument) :
    L4YAML.TokenParser.parseYaml "!h!x" ≠ .ok docs := by
  intro h
  have hrejected : parseAccepts "!h!x" = false := by native_decide
  unfold parseAccepts at hrejected
  rw [h] at hrejected
  contradiction

theorem parse_iff_grammar_tag_handle_obstruction :
    ¬ ((∃ docs, L4YAML.TokenParser.parseYaml "!h!x" = .ok docs) ↔
       InYamlLanguage "!h!x") := by
  intro h
  obtain ⟨docs, hdocs⟩ := h.mpr undeclared_named_tag_is_in_surface
  exact undeclared_named_tag_has_no_parse docs hdocs

end L4YAMLTagHandleObstruction
