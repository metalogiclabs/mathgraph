import MathGraph.Calculus.Core
import MathGraph.Calculus.Refinement

universe u v w

namespace MathGraph.Calculus

/-- The separation relation induced by a consequence language: two states are
separated exactly when some licensed observation distinguishes them. -/
def Separated {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (x y : α) : Prop :=
  ∃ i, L i x ≠ L i y

/-- Consequential identity is exactly non-separation by the induced relation. -/
theorem consequentialEq_iff_not_separated
    {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (x y : α) :
    ConsequentialEq L x y ↔ ¬ Separated L x y := by
  constructor
  · intro hEq hSep
    rcases hSep with ⟨i, hne⟩
    exact hne (hEq i)
  · intro hNoSep i
    classical
    by_contra hne
    exact hNoSep ⟨i, hne⟩

/-- The induced separation is irreflexive. -/
theorem separated_irrefl
    {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (x : α) :
    ¬ Separated L x x := by
  intro h
  rcases h with ⟨i, hne⟩
  exact hne rfl

/-- The induced separation is symmetric. -/
theorem separated_symm
    {ι : Type w} {α : Type u} {β : Type v}
    {L : Language ι α β} {x y : α}
    (h : Separated L x y) : Separated L y x := by
  rcases h with ⟨i, hne⟩
  exact ⟨i, fun hEq => hne hEq.symm⟩

/-- The induced separation is cotransitive.  Thus the observation language
canonically induces an apartness relation, and consequential identity is its
negation. -/
theorem separated_cotrans
    {ι : Type w} {α : Type u} {β : Type v}
    {L : Language ι α β} {x y z : α}
    (h : Separated L x z) :
    Separated L x y ∨ Separated L y z := by
  rcases h with ⟨i, hxz⟩
  classical
  by_cases hxy : L i x = L i y
  · right
    refine ⟨i, ?_⟩
    intro hyz
    exact hxz (hxy.trans hyz)
  · left
    exact ⟨i, hxy⟩

/-- Extending a language by one consequence adds exactly the old separators
plus pairs separated by the new consequence.  This is the separation-dual of
the golden refinement law. -/
theorem separated_extend_iff
    {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) (x y : α) :
    Separated (extend L c) x y ↔ Separated L x y ∨ c x ≠ c y := by
  constructor
  · rintro ⟨q, hq⟩
    cases q with
    | inl i => exact Or.inl ⟨i, hq⟩
    | inr u =>
        cases u
        exact Or.inr hq
  · intro h
    cases h with
    | inl hOld =>
        rcases hOld with ⟨i, hi⟩
        exact ⟨Sum.inl i, hi⟩
    | inr hNew =>
        exact ⟨Sum.inr (), hNew⟩

/-- A residual witness is exactly an old non-separation together with a new
separator. -/
theorem residual_iff_nonseparation_plus_separator
    {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) (x y : α) :
    ResidualWitness L c x y ↔
      (¬ Separated L x y) ∧ c x ≠ c y := by
  constructor
  · intro r
    exact ⟨(consequentialEq_iff_not_separated L x y).mp r.indistinguishable,
      r.separated⟩
  · rintro ⟨hNoSep, hSep⟩
    exact {
      indistinguishable := (consequentialEq_iff_not_separated L x y).mpr hNoSep
      separated := hSep
    }

/-- Refinement can be read purely on separators: a stronger language preserves
all separations made by a weaker one. -/
theorem refines_iff_separation_inclusion
    {ι : Type w} {κ : Type} {α : Type u} {β : Type v}
    (strong : Language ι α β) (weak : Language κ α β) :
    Refines strong weak ↔
      ∀ ⦃x y⦄, Separated weak x y → Separated strong x y := by
  classical
  constructor
  · intro hRef x y hSepWeak
    by_contra hNoStrong
    have hStrongEq : ConsequentialEq strong x y :=
      (consequentialEq_iff_not_separated strong x y).mpr hNoStrong
    have hWeakEq : ConsequentialEq weak x y := hRef hStrongEq
    exact (consequentialEq_iff_not_separated weak x y).mp hWeakEq hSepWeak
  · intro hSep x y hStrongEq
    apply (consequentialEq_iff_not_separated weak x y).mpr
    intro hWeakSep
    have hStrongSep := hSep hWeakSep
    exact (consequentialEq_iff_not_separated strong x y).mp hStrongEq hStrongSep

end MathGraph.Calculus
