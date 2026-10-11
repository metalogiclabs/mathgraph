/-!
MathGraph protected-future refinement and source-indexed requalification.

This is a general conditional calculus. It deliberately does not claim that
any arbitrary real source adapter or equivalence relation satisfies the premises.
-/
universe u v

namespace MathGraphRefinement

def EquivalentOn {S : Type u} {Query : Type v}
    (protected : Query → Prop) (observe : S → Query → Prop)
    (x y : S) : Prop :=
  ∀ q, protected q → (observe x q ↔ observe y q)

theorem equivalent_refl {S : Type u} {Query : Type v}
    (protected : Query → Prop) (observe : S → Query → Prop) (x : S) :
    EquivalentOn protected observe x x := by
  intro q h
  exact Iff.rfl

theorem equivalent_symm {S : Type u} {Query : Type v}
    (protected : Query → Prop) (observe : S → Query → Prop)
    {x y : S} (h : EquivalentOn protected observe x y) :
    EquivalentOn protected observe y x := by
  intro q hq
  exact (h q hq).symm

theorem equivalent_trans {S : Type u} {Query : Type v}
    (protected : Query → Prop) (observe : S → Query → Prop)
    {x y z : S}
    (hxy : EquivalentOn protected observe x y)
    (hyz : EquivalentOn protected observe y z) :
    EquivalentOn protected observe x z := by
  intro q hq
  exact (hxy q hq).trans (hyz q hq)

theorem restriction_preserves_equivalence {S : Type u} {Query : Type v}
    (old new : Query → Prop) (observe : S → Query → Prop)
    (included : ∀ q, new q → old q)
    {x y : S} (h : EquivalentOn old observe x y) :
    EquivalentOn new observe x y := by
  intro q hq
  exact h q (included q hq)

theorem expansion_requires_new_obligations {S : Type u} {Query : Type v}
    (old new : Query → Prop) (observe : S → Query → Prop)
    {x y : S}
    (hOld : EquivalentOn old observe x y)
    (hFresh : ∀ q, new q → ¬ old q → (observe x q ↔ observe y q)) :
    EquivalentOn new observe x y := by
  intro q hNew
  by_cases h : old q
  · exact hOld q h
  · exact hFresh q hNew h

theorem distinguishing_query_blocks_equivalence
    {S : Type u} {Query : Type v}
    (protected : Query → Prop) (observe : S → Query → Prop)
    (x y : S) (q : Query)
    (hq : protected q)
    (different : ¬ (observe x q ↔ observe y q)) :
    ¬ EquivalentOn protected observe x y := by
  intro h
  exact different (h q hq)

def LiveSupport {Source : Type u}
    (live : Source → Prop) (paths : List (List Source)) : Prop :=
  ∃ path, path ∈ paths ∧ ∀ s, s ∈ path → live s

theorem alternative_path_survives {Source : Type u}
    (live : Source → Prop) (paths : List (List Source))
    (path : List Source) (member : path ∈ paths)
    (allLive : ∀ s, s ∈ path → live s) :
    LiveSupport live paths := by
  exact ⟨path,member,allLive⟩

theorem no_path_no_warrant {Source : Type u}
    (live : Source → Prop) (paths : List (List Source))
    (noPath : ∀ path, path ∈ paths →
      ¬ (∀ s, s ∈ path → live s)) :
    ¬ LiveSupport live paths := by
  intro h
  rcases h with ⟨path,member,allLive⟩
  exact noPath path member allLive

end MathGraphRefinement
