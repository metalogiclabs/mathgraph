import L4YAML.Surface.Node

/-!
# Flow-entry continuation algebra

A small proof-engineering replacement for left-to-right `snoc` accumulation of
YAML flow collections.

The surface grammar is right-recursive, while the scanner/parser consume input
left-to-right.  Rather than repeatedly rebuilding a completed
`SFlowSeqEntries` / `SFlowMapEntries` derivation, retain a continuation:

  prefix start cur := every valid tail from cur closes a valid collection from start.

Each comma-separated entry composes one constructor into that continuation.
At the closing bracket the final entry is supplied as `single` (or `consEnd`
for a trailing comma).

This has two useful consequences for the grammar-completeness capstone:

* no bespoke structural `snoc` theorem is needed;
* no already-built derivation must be inverted during left-to-right scanning.

It is a minimal sufficient interface between lexical accumulation and the
right-recursive YAML surface grammar.
-/

namespace L4YAMLFlowContinuation

open L4YAML.Surface

abbrev FlowSeqK (n : Nat) (c : L4YAML.YamlContext) (start cur : SurfPos) : Prop :=
  ∀ finish, SFlowSeqEntries n c cur finish → SFlowSeqEntries n c start finish

abbrev FlowMapK (n : Nat) (c : L4YAML.YamlContext) (start cur : SurfPos) : Prop :=
  ∀ finish, SFlowMapEntries n c cur finish → SFlowMapEntries n c start finish

lemma FlowSeqK.refl (n : Nat) (c : L4YAML.YamlContext) (s : SurfPos) :
    FlowSeqK n c s s :=
  fun _ h => h

lemma FlowMapK.refl (n : Nat) (c : L4YAML.YamlContext) (s : SurfPos) :
    FlowMapK n c s s :=
  fun _ h => h

/--
Consume one non-final sequence entry plus its comma and post-comma separation,
leaving a continuation waiting for the remaining entries.
-/
lemma FlowSeqK.step
    {n : Nat} {c : L4YAML.YamlContext}
    {start cur s1 s2 s3 next : SurfPos}
    (k : FlowSeqK n c start cur)
    (h_entry : SFlowSeqEntry n c cur s1)
    (h_sep : GOpt (SSeparate n c) s1 s2)
    (h_comma : GLit ',' s2 s3)
    (h_after : GOpt (SSeparate n c) s3 next) :
    FlowSeqK n c start next := by
  intro finish h_tail
  exact k finish
    (SFlowSeqEntries.consMore n c cur s1 s2 s3 next finish
      h_entry h_sep h_comma h_after h_tail)

/-- Close a sequence continuation with its final entry. -/
lemma FlowSeqK.finish
    {n : Nat} {c : L4YAML.YamlContext}
    {start cur s1 finish : SurfPos}
    (k : FlowSeqK n c start cur)
    (h_entry : SFlowSeqEntry n c cur s1)
    (h_sep : GOpt (SSeparate n c) s1 finish) :
    SFlowSeqEntries n c start finish :=
  k finish (SFlowSeqEntries.single n c cur s1 finish h_entry h_sep)

/-- Close a sequence continuation with a YAML-permitted trailing comma. -/
lemma FlowSeqK.finishTrailing
    {n : Nat} {c : L4YAML.YamlContext}
    {start cur s1 s2 s3 finish : SurfPos}
    (k : FlowSeqK n c start cur)
    (h_entry : SFlowSeqEntry n c cur s1)
    (h_sep : GOpt (SSeparate n c) s1 s2)
    (h_comma : GLit ',' s2 s3)
    (h_after : GOpt (SSeparate n c) s3 finish) :
    SFlowSeqEntries n c start finish :=
  k finish
    (SFlowSeqEntries.consEnd n c cur s1 s2 s3 finish
      h_entry h_sep h_comma h_after)

/-- Mapping analogue of `FlowSeqK.step`. -/
lemma FlowMapK.step
    {n : Nat} {c : L4YAML.YamlContext}
    {start cur s1 s2 s3 next : SurfPos}
    (k : FlowMapK n c start cur)
    (h_entry : SFlowMapEntry n c cur s1)
    (h_sep : GOpt (SSeparate n c) s1 s2)
    (h_comma : GLit ',' s2 s3)
    (h_after : GOpt (SSeparate n c) s3 next) :
    FlowMapK n c start next := by
  intro finish h_tail
  exact k finish
    (SFlowMapEntries.consMore n c cur s1 s2 s3 next finish
      h_entry h_sep h_comma h_after h_tail)

/-- Close a mapping continuation with its final entry. -/
lemma FlowMapK.finish
    {n : Nat} {c : L4YAML.YamlContext}
    {start cur s1 finish : SurfPos}
    (k : FlowMapK n c start cur)
    (h_entry : SFlowMapEntry n c cur s1)
    (h_sep : GOpt (SSeparate n c) s1 finish) :
    SFlowMapEntries n c start finish :=
  k finish (SFlowMapEntries.single n c cur s1 finish h_entry h_sep)

/-- Close a mapping continuation with a YAML-permitted trailing comma. -/
lemma FlowMapK.finishTrailing
    {n : Nat} {c : L4YAML.YamlContext}
    {start cur s1 s2 s3 finish : SurfPos}
    (k : FlowMapK n c start cur)
    (h_entry : SFlowMapEntry n c cur s1)
    (h_sep : GOpt (SSeparate n c) s1 s2)
    (h_comma : GLit ',' s2 s3)
    (h_after : GOpt (SSeparate n c) s3 finish) :
    SFlowMapEntries n c start finish :=
  k finish
    (SFlowMapEntries.consEnd n c cur s1 s2 s3 finish
      h_entry h_sep h_comma h_after)

end L4YAMLFlowContinuation
