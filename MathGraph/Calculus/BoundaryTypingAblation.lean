import MathGraph.Calculus.RockBottomAblation

namespace MathGraph.Calculus

/-- Four boundary positions used to test whether endpoint typing is genuine
structure or merely bookkeeping. -/
inductive BoundaryPoint where
  | a | b | c | d

/-- Two primitive events with incompatible boundaries. -/
inductive BoundaryEdge : BoundaryPoint → BoundaryPoint → Type where
  | ab : BoundaryEdge .a .b
  | cd : BoundaryEdge .c .d

/-- Each primitive event separately generates a valid typed continuation. -/
def typed_ab : FreePath BoundaryEdge .a .b :=
  FreePath.ofGenerator .ab

def typed_cd : FreePath BoundaryEdge .c .d :=
  FreePath.ofGenerator .cd

/-- Erasing boundaries leaves only anonymous event names. -/
inductive ErasedEvent where
  | ab | cd

/-- With boundary information erased, arbitrary event lists are admitted as
putative continuations. -/
def UntypedContinuation := List ErasedEvent

/-- The two individually valid events can now be sequenced even though the
first ends at `b` and the second starts at `c`. -/
def spurious_untyped_ab_then_cd : UntypedContinuation :=
  [.ab, .cd]

/-- In the boundary-typed free continuation, that same composite cannot exist:
there is no path from `a` to `d` using only `a→b` and `c→d`. -/
def no_typed_a_to_d : FreePath BoundaryEdge .a .d → Empty := by
  intro p
  cases p with
  | step e rest =>
      cases e with
      | ab =>
          cases rest with
          | step e₂ rest₂ => exact nomatch e₂

/-- Decisive boundary ablation. Primitive events survive erasure, and their
untyped sequencing survives, but erasure creates a composite that the typed
continuation calculus rejects. Therefore some source/target compatibility
information is necessary; endpoint labels themselves are representational,
but composability boundaries are not disposable. -/
def boundary_typing_ablation_certificate :
    FreePath BoundaryEdge .a .b ×
    FreePath BoundaryEdge .c .d ×
    UntypedContinuation ×
    (FreePath BoundaryEdge .a .d → Empty) :=
  ⟨typed_ab, typed_cd, spurious_untyped_ab_then_cd, no_typed_a_to_d⟩

end MathGraph.Calculus
