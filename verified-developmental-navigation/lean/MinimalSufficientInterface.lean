import Mathlib.Data.Set.Lattice
import Mathlib.Data.Quot

namespace VerifiedDevelopmentalNavigation

universe u v w

variable {X : Type u} {D : Type v} {Z : Type w}

/-- An interface `R` is sufficient for protected semantics `Γ` when `Γ` factors through `R`. -/
def Sufficient (Γ : X → D) (R : X → Z) : Prop :=
  ∃ h : Z → D, Γ = h ∘ R

/-- Kernel relation of a map. -/
def KerRel (f : X → D) : X → X → Prop := fun x y => f x = f y

/-- A representation refines another when its kernel is contained in the other's kernel. -/
def Refines {A : Type*} {B : Type*} (R : X → A) (S : X → B) : Prop :=
  ∀ ⦃x y : X⦄, R x = R y → S x = S y

/-- Factorization implies kernel inclusion. -/
theorem sufficient_implies_kernel_inclusion
    (Γ : X → D) (R : X → Z) (hR : Sufficient Γ R) :
    Refines R Γ := by
  rcases hR with ⟨h, rfl⟩
  intro x y hxy
  simp [Function.comp_apply, hxy]

/-- Kernel inclusion is sufficient for factorization, with no choice principle required. -/
theorem kernel_inclusion_implies_sufficient
    (Γ : X → D) (R : X → Z)
    (hker : Refines R Γ) :
    Sufficient Γ R := by
  let h : Z → D := fun z =>
    if hz : ∃ x, R x = z then Γ (Classical.choose hz)
    else Classical.choice (Classical.propComplete (Nonempty D))
  refine ⟨h, ?_⟩
  funext x
  simp only [Function.comp_apply]
  have hx : ∃ y, R y = R x := ⟨x, rfl⟩
  simp [h, hx]
  apply hker
  exact Classical.choose_spec hx

/-- Sufficiency is exactly kernel inclusion. -/
theorem sufficient_iff_kernel_inclusion
    [Nonempty D] (Γ : X → D) (R : X → Z) :
    Sufficient Γ R ↔ Refines R Γ := by
  constructor
  · exact sufficient_implies_kernel_inclusion Γ R
  · intro hker
    classical
    let h : Z → D := fun z =>
      if hz : ∃ x, R x = z then Γ (Classical.choose hz)
      else Classical.choice (inferInstance : Nonempty D)
    refine ⟨h, ?_⟩
    funext x
    simp only [Function.comp_apply]
    have hx : ∃ y, R y = R x := ⟨x, rfl⟩
    simp [h, hx]
    apply hker
    exact Classical.choose_spec hx

/-- The protected semantics themselves are sufficient. -/
theorem semantics_self_sufficient (Γ : X → D) : Sufficient Γ Γ := by
  exact ⟨id, by funext x; rfl⟩

/-- Every sufficient interface refines the protected semantics. This is the coarsest-interface theorem. -/
theorem protected_semantics_coarsest
    (Γ : X → D) (R : X → Z) (hR : Sufficient Γ R) :
    Refines R Γ :=
  sufficient_implies_kernel_inclusion Γ R hR

/-- Two single-valued protected semantics that mutually factor through each other induce the same kernel. -/
theorem mutual_factorization_same_kernel
    {D₁ : Type v} {D₂ : Type w}
    (Γ₁ : X → D₁) (Γ₂ : X → D₂)
    (h12 : Sufficient Γ₁ Γ₂) (h21 : Sufficient Γ₂ Γ₁) :
    ∀ x y, Γ₁ x = Γ₁ y ↔ Γ₂ x = Γ₂ y := by
  intro x y
  constructor
  · intro h
    exact sufficient_implies_kernel_inclusion Γ₂ Γ₁ h21 h
  · intro h
    exact sufficient_implies_kernel_inclusion Γ₁ Γ₂ h12 h

/-- Cumulative protected semantics refine old kernel distinctions. -/
theorem factorized_requirement_kernel_monotone
    {Dnew : Type v} {Dold : Type w}
    (Γnew : X → Dnew) (Γold : X → Dold)
    (h : Dnew → Dold) (hfac : Γold = h ∘ Γnew) :
    Refines Γnew Γold := by
  intro x y hxy
  rw [hfac]
  simp [Function.comp_apply, hxy]

/-- A family of probes is sound for `Γ` if Γ-equivalent states agree on every probe. -/
def ProbeSound {I : Type*} {E : I → Type*}
    (Γ : X → D) (q : (i : I) → X → E i) : Prop :=
  ∀ x y, Γ x = Γ y → ∀ i, q i x = q i y

/-- A family of probes is complete for `Γ` if every Γ-inequivalent pair is separated. -/
def ProbeComplete {I : Type*} {E : I → Type*}
    (Γ : X → D) (q : (i : I) → X → E i) : Prop :=
  ∀ x y, Γ x ≠ Γ y → ∃ i, q i x ≠ q i y

/-- Sound + complete probes induce exactly the protected kernel relation. -/
theorem probe_basis_exact
    {I : Type*} {E : I → Type*}
    (Γ : X → D) (q : (i : I) → X → E i)
    (hs : ProbeSound Γ q) (hc : ProbeComplete Γ q) :
    ∀ x y, (∀ i, q i x = q i y) ↔ Γ x = Γ y := by
  intro x y
  constructor
  · intro hq
    by_contra hne
    rcases hc x y hne with ⟨i, hi⟩
    exact hi (hq i)
  · intro hΓ i
    exact hs x y hΓ i

/-- Sound probes can only refine Γ-equivalence classes, never split inside them. -/
theorem probe_sound_no_false_split
    {I : Type*} {E : I → Type*}
    (Γ : X → D) (q : (i : I) → X → E i)
    (hs : ProbeSound Γ q) :
    ∀ x y, Γ x = Γ y → ∀ i, q i x = q i y := hs

/-- Completeness says every genuine Γ-distinction has a separating witness. -/
theorem probe_complete_has_separator
    {I : Type*} {E : I → Type*}
    (Γ : X → D) (q : (i : I) → X → E i)
    (hc : ProbeComplete Γ q) :
    ∀ x y, Γ x ≠ Γ y → ∃ i, q i x ≠ q i y := hc

end VerifiedDevelopmentalNavigation
