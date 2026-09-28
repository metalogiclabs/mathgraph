import L4YAML.Surface.Document
import L4YAML.Parser.Composition
import L4YAML.Scanner.Scanner

/-!
# Exact nested-flow witness

A small end-to-end positive/negative control for the L4YAML
grammar-completeness campaign.

The positive input `[[],[]]` is proved to inhabit the *spec constructors*
all the way up to `InYamlLanguage`, with no use of `SLYamlStream.scannerDrop`.
The adjacent negative control `[[][]]` is scan-accepted but parse-rejected.

This pins the intended division of labor:
- lexical evidence accounts for literal character spans;
- parser structure accounts for the comma-separated collection shape.
-/

namespace L4YAMLExactNestedFlow

open L4YAML
open L4YAML.Surface

def scanAccepts (s : String) : Bool :=
  match Scanner.scan s with
  | .ok _ => true
  | .error _ => false

def parseAccepts (s : String) : Bool :=
  match TokenParser.parseYaml s with
  | .ok _ => true
  | .error _ => false

-- Adjacent nested entries are still lexical scanner input, but not parser syntax.
example : scanAccepts "[[][]]" = true := by native_decide
example : parseAccepts "[[][]]" = false := by native_decide

-- Proper comma separation is accepted.
example : scanAccepts "[[],[]]" = true := by native_decide
example : parseAccepts "[[],[]]" = true := by native_decide

/--
A complete exact surface witness for a nested two-entry flow sequence.

Every constructor below is a YAML surface-production constructor. In
particular, this derivation never uses `SLYamlStream.scannerDrop`.
-/
theorem nested_pair_exact_language : InYamlLanguage "[[],[]]" := by
  let s0 : SurfPos := ⟨['[', '[', ']', ',', '[', ']', ']'], 0⟩
  let s1 : SurfPos := ⟨['[', ']', ',', '[', ']', ']'], 1⟩
  let s2 : SurfPos := ⟨[']', ',', '[', ']', ']'], 2⟩
  let s3 : SurfPos := ⟨[',', '[', ']', ']'], 3⟩
  let s4 : SurfPos := ⟨['[', ']', ']'], 4⟩
  let s5 : SurfPos := ⟨[']', ']'], 5⟩
  let s6 : SurfPos := ⟨[']'], 6⟩
  let s7 : SurfPos := ⟨[], 7⟩

  have h_outer_open : GLit '[' s0 s1 := by
    exact GLit.mk _ _
  have h_inner1_open : GLit '[' s1 s2 := by
    exact GLit.mk _ _
  have h_inner1_close : GLit ']' s2 s3 := by
    exact GLit.mk _ _
  have h_comma : GLit ',' s3 s4 := by
    exact GLit.mk _ _
  have h_inner2_open : GLit '[' s4 s5 := by
    exact GLit.mk _ _
  have h_inner2_close : GLit ']' s5 s6 := by
    exact GLit.mk _ _
  have h_outer_close : GLit ']' s6 s7 := by
    exact GLit.mk _ _

  have h_inner1 : SFlowSequence 0 .flowIn s1 s3 :=
    SFlowSequence.empty 0 .flowIn s1 s2 s2 s3
      h_inner1_open (GOpt.none s2) h_inner1_close
  have h_inner2 : SFlowSequence 0 .flowIn s4 s6 :=
    SFlowSequence.empty 0 .flowIn s4 s5 s5 s6
      h_inner2_open (GOpt.none s5) h_inner2_close

  have h_entry1 : SFlowSeqEntry 0 .flowIn s1 s3 :=
    SFlowSeqEntry.node 0 .flowIn s1 s3
      (SFlowNode.content 0 .flowIn s1 s3
        (SFlowContent.flowSeq 0 .flowIn s1 s3 h_inner1))
  have h_entry2 : SFlowSeqEntry 0 .flowIn s4 s6 :=
    SFlowSeqEntry.node 0 .flowIn s4 s6
      (SFlowNode.content 0 .flowIn s4 s6
        (SFlowContent.flowSeq 0 .flowIn s4 s6 h_inner2))

  have h_tail : SFlowSeqEntries 0 .flowIn s4 s6 :=
    SFlowSeqEntries.single 0 .flowIn s4 s6 s6
      h_entry2 (GOpt.none s6)
  have h_entries : SFlowSeqEntries 0 .flowIn s1 s6 :=
    SFlowSeqEntries.consMore 0 .flowIn s1 s3 s3 s4 s4 s6
      h_entry1 (GOpt.none s3) h_comma (GOpt.none s4) h_tail

  have h_outer : SFlowSequence 0 .flowOut s0 s7 :=
    SFlowSequence.nonempty 0 .flowOut s0 s1 s1 s6 s7
      h_outer_open (GOpt.none s1) h_entries h_outer_close
  have h_outer_node : SFlowNode 0 .flowOut s0 s7 :=
    SFlowNode.content 0 .flowOut s0 s7
      (SFlowContent.flowSeq 0 .flowOut s0 s7 h_outer)

  have h_top_sep : SSeparate 0 .flowOut s0 s0 := by
    exact SSeparateLines.inline 0 s0 s0 (SSeparateInLine.startOfLine s0)
  have h_eof : SSLComments s7 s7 :=
    SSLComments.withComment s7 s7 s7
      (SSBComment.noSep s7 s7 (SBComment.eof 7))
      (GStar.nil s7)

  have h_block : SBlockNode 0 .blockIn s0 s7 :=
    SBlockNode.flowInBlock 0 .blockIn s0 s0 s7 s7
      h_top_sep h_outer_node h_eof
  have h_bare : SLBareDocument s0 s7 :=
    SLBareDocument.mk s0 s7 h_block
  have h_stream : SLYamlStream s0 s7 :=
    SLYamlStream.single s0 s0 s7 s7
      (GStar.nil s0)
      (GOpt.some s0 s7 (SLAnyDocument.bare s0 s7 h_bare))
      (GStar.nil s7)

  refine ⟨s7, ?_, rfl⟩
  exact h_stream

end L4YAMLExactNestedFlow
