import MathGraph.Calculus.Core

universe u v w z

namespace MathGraph.Calculus

/-- `strong` refines `weak` when every pair identified by `strong` is also
identified by `weak`. Thus `strong` carries at least as much distinguishing
information as `weak`. -/
def Refines {ι : Type w} {κ : Type z} {α : Type u} {β : Type v}
    (strong : Language ι α β) (weak : Language κ α β) : Prop :=
  ∀ ⦃x y⦄, ConsequentialEq strong x y → ConsequentialEq weak x y

theorem refines_refl {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) : Refines L L := by
  intro x y h
  exact h

theorem refines_trans {ι : Type w} {κ : Type z} {μ : Type} {α : Type u} {β : Type v}
    {A : Language ι α β} {B : Language κ α β} {C : Language μ α β}
    (hAB : Refines A B) (hBC : Refines B C) : Refines A C := by
  intro x y h
  exact hBC (hAB h)

/-- Adding an observable can only refine, never coarsen, consequential
identity. -/
theorem extend_refines {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) :
    Refines (extend L c) L := by
  intro x y h
  exact (consequentialEq_extend_iff L c x y).mp h |>.1

/-- Two languages are semantically equivalent when they induce exactly the
same consequential identity relation. -/
def LanguageEq {ι : Type w} {κ : Type z} {α : Type u} {β : Type v}
    (A : Language ι α β) (B : Language κ α β) : Prop :=
  Refines A B ∧ Refines B A

/-- Join two languages without privileging either one. -/
def join {ι : Type w} {κ : Type z} {α : Type u} {β : Type v}
    (A : Language ι α β) (B : Language κ α β) :
    Language (Sum ι κ) α β
  | Sum.inl i => A i
  | Sum.inr k => B k

/-- Identity under a joined language is exactly intersection of the two
component identities. -/
theorem consequentialEq_join_iff {ι : Type w} {κ : Type z}
    {α : Type u} {β : Type v} (A : Language ι α β) (B : Language κ α β)
    (x y : α) :
    ConsequentialEq (join A B) x y ↔
      ConsequentialEq A x y ∧ ConsequentialEq B x y := by
  constructor
  · intro h
    constructor
    · intro i
      exact h (Sum.inl i)
    · intro k
      exact h (Sum.inr k)
  · rintro ⟨hA, hB⟩ q
    cases q with
    | inl i => exact hA i
    | inr k => exact hB k

theorem join_refines_left {ι : Type w} {κ : Type z}
    {α : Type u} {β : Type v} (A : Language ι α β) (B : Language κ α β) :
    Refines (join A B) A := by
  intro x y h
  exact (consequentialEq_join_iff A B x y).mp h |>.1

theorem join_refines_right {ι : Type w} {κ : Type z}
    {α : Type u} {β : Type v} (A : Language ι α β) (B : Language κ α β) :
    Refines (join A B) B := by
  intro x y h
  exact (consequentialEq_join_iff A B x y).mp h |>.2

/-- The join is the least common refinement: any language that refines both
inputs also refines their join. -/
theorem refines_join {ι : Type w} {κ : Type z} {μ : Type}
    {α : Type u} {β : Type v} {A : Language ι α β} {B : Language κ α β}
    {C : Language μ α β} (hA : Refines C A) (hB : Refines C B) :
    Refines C (join A B) := by
  intro x y hC
  exact (consequentialEq_join_iff A B x y).mpr ⟨hA hC, hB hC⟩

/-- A residual witness makes extension strictly more discriminating: the
extension refines the original language, but the original cannot refine the
extension. -/
theorem residual_forces_strict_refinement
    {ι : Type w} {α : Type u} {β : Type v}
    {L : Language ι α β} {c : Observation α β} {x y : α}
    (r : ResidualWitness L c x y) :
    Refines (extend L c) L ∧ ¬ Refines L (extend L c) := by
  constructor
  · exact extend_refines L c
  · intro h
    have hext : ConsequentialEq (extend L c) x y := h r.indistinguishable
    exact (residual_forces_split r) hext

/-- Redundant extension is exactly semantic equivalence with the original
language. -/
theorem redundant_iff_languageEq_extension
    {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) :
    Redundant L c ↔ LanguageEq (extend L c) L := by
  constructor
  · intro hred
    constructor
    · exact extend_refines L c
    · intro x y hL
      exact (consequentialEq_extend_iff L c x y).mpr ⟨hL, hred hL⟩
  · intro hEq x y hL
    have hext : ConsequentialEq (extend L c) x y := hEq.2 hL
    exact (consequentialEq_extend_iff L c x y).mp hext |>.2

end MathGraph.Calculus
