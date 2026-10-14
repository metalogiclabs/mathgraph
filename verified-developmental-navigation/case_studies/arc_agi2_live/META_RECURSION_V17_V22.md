# Recursive ARC residual: V17–V22

Evidence status: all ARC-AGI-2 results below use public evaluation data pinned at `f3283f727488ad98fe575ea6a5ac981e4a188e49`. Anything derived after inspecting held-out outputs is `KNOWN_WORLD_RETROSPECTIVE_REPAIR`, not protected capability evidence.

## V17 — symbolic action CompleteCover

Run `33041899889` exhaustively evaluated a frozen eight-program action family inside the V13 symbolic ontology: pairwise composition with two tail policies, offset-1 pairwise composition, whole-chain root collapse, and synchronous one-hop variants. Across 120 evaluation tasks this was 960 candidate evaluations. Exactly one task (`d35bdbdc`) fit all demonstrations and zero held-out tests were solved. Therefore the finite action family was exhausted without closing the `L1 -> L0` edge. This is not a completeness claim for symbolic programs generally.

## V13 held-out diagnostic

Run `33041998582` localized the remaining `d35bdbdc` residual. Test 0 does not parse under the fixed V13 3x3-ring symbolic carrier at all. Tests 1 and 2 do parse. Under the original delete-tail program test 1 differs from the target in 18 cells, while test 2 differs in only one cell. Thus the held-out failure is not purely an action-policy residual: at least one held-out case violates the current object/carrier representation.

## V18–V22 representation repairs

V18 (`33042078085`) generalized the carrier to any centered cardinal motif and obtained 0 demonstration fits / 0 held-out solves. V19 (`33042149269`) restricted this to the literal union of exact rings and strict crosses and again obtained 0 / 0. These reject naive shape-union generalization because it admits incidental motifs and destroys the training semantics.

V20 (`33042212125`) restored exact V13 rings and admitted crosses only when supported by the symbolic key relation. This recovered the `d35bdbdc` demonstration fit but still produced 0 held-out solves and no source-distinct solve.

V21 (`33042276946`) tested an explicit product of the previously explored spatial grouping relation and symbolic equality relation. Across 1,552 candidate evaluations it produced 0 demonstration fits / 0 held-out solves. Simple composition of two relation languages is therefore not sufficient.

V22 (`33042339015`) stopped naming ring/cross shapes and defined a candidate object by local support topology: a payload surrounded cardinally by one carrier color whose whole 8-connected carrier component is small and local. This again preserved exactly one demonstration fit (`d35bdbdc`) but produced 0 held-out solves and no source-distinct solve.

## Meta-residual

The evidence no longer supports another hand-authored tweak to the `d35bdbdc` ontology as the highest-information move. V17 rules out a small action-only explanation, while V18–V22 show that several manually proposed representation repairs either destroy demonstration reach or merely recover the same single known-world fit without external capability.

The live residual has therefore moved upward: the **representation generator / adequacy process itself is still designer-supplied**. The next gate should freeze a procedure that induces candidate observations, objects, and relations from raw training traces plus verifier consequences, then evaluate that induced representation on a fresh protected task split whose outputs were not used to design the representation generator.

A successful recursive-development result should require the full causal chain:

`L0 task failure -> L1 representation residual -> L2 change to representation-generating policy -> induced L1 representation -> protected L0 capability gain`,

followed by ablation of the L2-induced representation policy or learned adequacy map causing the protected gain to disappear.
