import L4YAML.Surface.Document
import L4YAML.Parser.Composition

/-!
# L4YAML block-header surface obstruction

The surface production `SCBBlockHeader` currently uses an unbounded `GStar`
over header-indicator characters.  The executable scanner consumes at most two
header indicators.  Therefore three indicator characters can be derived by the
surface grammar but are rejected by the executable parser.

This is independent of directives, aliases, tag handles, and `scannerDrop`.
-/

namespace L4YAMLBlockHeaderObstruction

open L4YAML
open L4YAML.Surface

def parseAccepts (s : String) : Bool :=
  match L4YAML.TokenParser.parseYaml s with
  | .ok _ => true
  | .error _ => false

example : parseAccepts "|+++\n" = false := by native_decide

theorem triple_chomp_header_is_in_surface :
    InYamlLanguage "|+++\n" := by
  let s0 : SurfPos := ⟨['|', '+', '+', '+', '\n'], 0⟩
  let s1 : SurfPos := ⟨['+', '+', '+', '\n'], 1⟩
  let s2 : SurfPos := ⟨['+', '+', '\n'], 2⟩
  let s3 : SurfPos := ⟨['+', '\n'], 3⟩
  let s4 : SurfPos := ⟨['\n'], 4⟩
  let s5 : SurfPos := ⟨[], 0⟩

  have hp1 :
      GChar (fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true) s1 s2 := by
    exact GChar.mk (p := fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true)
      '+' ['+', '\n'] 1 (by native_decide)
  have hp2 :
      GChar (fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true) s2 s3 := by
    exact GChar.mk (p := fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true)
      '+' ['\n'] 2 (by native_decide)
  have hp3 :
      GChar (fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true) s3 s4 := by
    exact GChar.mk (p := fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true)
      '+' [] 3 (by native_decide)

  have hheaders :
      GStar (GChar (fun c => L4YAML.Grammar.isBlockScalarHeaderChar c = true)) s1 s4 :=
    GStar.cons s1 s2 s4 hp1
      (GStar.cons s2 s3 s4 hp2
        (GStar.cons s3 s4 s4 hp3 (GStar.nil s4)))

  have hbreak : SBBreak s4 s5 := by
    exact SBBreak.lf [] 4

  have hcomment : SSBComment s4 s5 :=
    SSBComment.noSep s4 s5 (SBComment.break s4 s5 hbreak)

  have hheader : SCBBlockHeader s1 s5 :=
    SCBBlockHeader.mk s1 s4 s5 hheaders hcomment

  have hcontent : SLLiteralContent 0 s5 s5 :=
    SLLiteralContent.mk 0 s5 s5 s5 s5 s5
      (GOpt.none s5)
      (GOpt.none s5)
      (GStar.nil s5)
      (GOpt.none s5)

  have hlit : SCLLiteral 0 s0 s5 :=
    SCLLiteral.mk 0 0 ['+', '+', '+', '\n'] 0 s5 s5 hheader hcontent

  have hsep : SSeparate 0 .blockIn s0 s0 := by
    exact SSeparateLines.inline 0 s0 s0 (SSeparateInLine.startOfLine s0)

  have hblock : SBlockNode 0 .blockIn s0 s5 :=
    SBlockNode.blockLiteral 0 .blockIn s0 s0 s0 s5
      hsep (GOpt.none s0) hlit

  have hbare : SLBareDocument s0 s5 :=
    SLBareDocument.mk s0 s5 hblock

  have hstream : SLYamlStream s0 s5 :=
    SLYamlStream.single s0 s0 s5 s5
      (GStar.nil s0)
      (GOpt.some s0 s5 (SLAnyDocument.bare s0 s5 hbare))
      (GStar.nil s5)

  exact ⟨s5, hstream, rfl⟩

theorem triple_chomp_header_has_no_parse
    (docs : Array YamlDocument) :
    L4YAML.TokenParser.parseYaml "|+++\n" ≠ .ok docs := by
  intro h
  have hrejected : parseAccepts "|+++\n" = false := by native_decide
  unfold parseAccepts at hrejected
  rw [h] at hrejected
  contradiction

theorem parse_iff_grammar_block_header_obstruction :
    ¬ ((∃ docs, L4YAML.TokenParser.parseYaml "|+++\n" = .ok docs) ↔
       InYamlLanguage "|+++\n") := by
  intro h
  obtain ⟨docs, hdocs⟩ := h.mpr triple_chomp_header_is_in_surface
  exact triple_chomp_header_has_no_parse docs hdocs

end L4YAMLBlockHeaderObstruction
