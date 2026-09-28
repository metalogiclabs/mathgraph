import L4YAML.Surface.Document
import L4YAML.Scanner.Scanner
import L4YAML.Parser.TokenParser

/-!
# L4YAML capstone obstruction probe

The advertised final capstone is:

```lean
(∃ docs, parseYaml input = .ok docs) ↔ InYamlLanguage input
```

Removing `scannerDrop` is necessary for exactness, but it is not sufficient
for this theorem as the surface grammar currently stands.

`SLDirective` is deliberately simplified to accept `%` followed by arbitrary
non-break text. The executable scanner is stricter for the special `%YAML`
directive: YAML 1.2.2 requires digit+ "." digit+, so `%YAML .2` is rejected.

This file asks the kernel whether the current exact surface constructors
(non-scannerDrop) nevertheless derive the malformed directive stream. If so,
the biconditional capstone is false as currently stated and the next residual is
a surface-grammar tightening, not merely scannerDrop removal.
-/

namespace L4YAMLCapstoneObstruction

open L4YAML
open L4YAML.Surface

def parseAccepts (s : String) : Bool :=
  match TokenParser.parseYaml s with
  | .ok _ => true
  | .error _ => false

example : parseAccepts "%YAML .2\n---" = false := by native_decide

/-- The current simplified surface grammar derives the malformed YAML version
    directive using only ordinary grammar constructors; scannerDrop is absent. -/
theorem malformed_yaml_version_is_in_surface :
    InYamlLanguage "%YAML .2\n---" := by
  let s0 : SurfPos :=
    ⟨['%', 'Y', 'A', 'M', 'L', ' ', '.', '2', '\n', '-', '-', '-'], 0⟩
  let s1 : SurfPos :=
    ⟨['Y', 'A', 'M', 'L', ' ', '.', '2', '\n', '-', '-', '-'], 1⟩
  let s2 : SurfPos :=
    ⟨['A', 'M', 'L', ' ', '.', '2', '\n', '-', '-', '-'], 2⟩
  let s3 : SurfPos :=
    ⟨['M', 'L', ' ', '.', '2', '\n', '-', '-', '-'], 3⟩
  let s4 : SurfPos :=
    ⟨['L', ' ', '.', '2', '\n', '-', '-', '-'], 4⟩
  let s5 : SurfPos :=
    ⟨[' ', '.', '2', '\n', '-', '-', '-'], 5⟩
  let s6 : SurfPos :=
    ⟨['.', '2', '\n', '-', '-', '-'], 6⟩
  let s7 : SurfPos :=
    ⟨['2', '\n', '-', '-', '-'], 7⟩
  let s8 : SurfPos :=
    ⟨['\n', '-', '-', '-'], 8⟩
  let s9 : SurfPos :=
    ⟨['-', '-', '-'], 0⟩
  let s10 : SurfPos := ⟨[], 3⟩

  have hY : SCommentChar s1 s2 := by
    exact GChar.mk 'Y' _ 1 (by decide)
  have hA : SCommentChar s2 s3 := by
    exact GChar.mk 'A' _ 2 (by decide)
  have hM : SCommentChar s3 s4 := by
    exact GChar.mk 'M' _ 3 (by decide)
  have hL : SCommentChar s4 s5 := by
    exact GChar.mk 'L' _ 4 (by decide)
  have hSpace : SCommentChar s5 s6 := by
    exact GChar.mk ' ' _ 5 (by decide)
  have hDot : SCommentChar s6 s7 := by
    exact GChar.mk '.' _ 6 (by decide)
  have hTwo : SCommentChar s7 s8 := by
    exact GChar.mk '2' _ 7 (by decide)

  have hBody : GStar SCommentChar s1 s8 :=
    GStar.cons s1 s2 s8 hY
      (GStar.cons s2 s3 s8 hA
        (GStar.cons s3 s4 s8 hM
          (GStar.cons s4 s5 s8 hL
            (GStar.cons s5 s6 s8 hSpace
              (GStar.cons s6 s7 s8 hDot
                (GStar.cons s7 s8 s8 hTwo (GStar.nil s8)))))))

  have hBreak : SBBreak s8 s9 := by
    exact SBBreak.lf ['-', '-', '-'] 8
  have hLineEnd : SSLComments s8 s9 :=
    SSLComments.withComment s8 s9 s9
      (SSBComment.noSep s8 s9 (SBComment.break s8 s9 hBreak))
      (GStar.nil s9)

  have hDirective : SLDirective s0 s9 :=
    SLDirective.mk
      ['Y', 'A', 'M', 'L', ' ', '.', '2', '\n', '-', '-', '-']
      0 s8 s9 hBody hLineEnd

  have hDirectivePlus : GPlus SLDirective s0 s9 :=
    GPlus.mk s0 s9 s9 hDirective (GStar.nil s9)

  have hMarker : SCDirectivesEnd s9 s10 := by
    exact SCDirectivesEnd.mk []

  have hEOF : SSLComments s10 s10 :=
    SSLComments.withComment s10 s10 s10
      (SSBComment.noSep s10 s10 (SBComment.eof 3))
      (GStar.nil s10)

  have hExplicit : SLExplicitDocument s9 s10 :=
    SLExplicitDocument.withContent s9 s10 s10 hMarker
      (GAlt.right s10 s10
        (GSeq.mk s10 s10 s10 (GEps.mk s10) hEOF))

  have hDirectiveDoc : SLDirectiveDocument s0 s10 :=
    SLDirectiveDocument.mk s0 s9 s10 hDirectivePlus hExplicit

  have hAny : SLAnyDocument s0 s10 :=
    SLAnyDocument.directive s0 s10 hDirectiveDoc

  have hStream : SLYamlStream s0 s10 :=
    SLYamlStream.single s0 s0 s10 s10
      (GStar.nil s0)
      (GOpt.some s0 s10 hAny)
      (GStar.nil s10)

  refine ⟨s10, ?_, rfl⟩
  exact hStream

/-- Every candidate parser result for this fixed input is impossible. -/
theorem malformed_yaml_version_has_no_parse
    (docs : Array YamlDocument) :
    TokenParser.parseYaml "%YAML .2\n---" ≠ .ok docs := by
  native_decide

/-- Kernel-level counterexample to the capstone biconditional as currently
    stated. -/
theorem parse_iff_grammar_current_statement_false :
    ¬ ((∃ docs, TokenParser.parseYaml "%YAML .2\n---" = .ok docs) ↔
       InYamlLanguage "%YAML .2\n---") := by
  intro h
  obtain ⟨docs, hdocs⟩ := h.mpr malformed_yaml_version_is_in_surface
  exact malformed_yaml_version_has_no_parse docs hdocs

end L4YAMLCapstoneObstruction
