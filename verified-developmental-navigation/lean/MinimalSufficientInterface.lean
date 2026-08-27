import Mathlib.Data.Set.Lattice

namespace VerifiedDevelopmentalNavigation

universe u v w

variable {X : Type u} {D : Type v} {Z : Type w}

/-- An interface `R` is sufficient for protected semantics `Γ` when `Γ` factors through `R`. -/
def Sufficient (Γ : X → D) (R : X → Z) : Prop :=
  ∃ h : Z → D, Γ = h ∘ R

/-- Kernel relation of a map. -/
def KerRel (f : X → D) : X → X → Prop := fun x y => f x = f y

/-- Factorization implies kernel inclusion. -/
theorem sufficient_implies_kernel_inclusion
    (Γ : X → D) (R : X → Z) (hR : Sufficient Γ R) :
    ∀ ⦃x y : X⦄, R x = R y → Γ x = Γ y := by
  rcases hR with ⟨h, rfl⟩
  intro x y hxy
  simp [Function.comp_apply, hxy]

/-- Cumulative protected semantics refine old kernel distinctions. -/
theorem factorized_requirement_kernel_monotone
    {Dnew : Type v} {Dold : Type w}
    (Γnew : X → Dnew) (Γold : X → Dold)
    (h : Dnew → Dold) (hfac : Γold = h ∘ Γnew) :
    ∀ ⦃x y : X⦄, Γnew x = Γnew y → Γold x = Γold y := by
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

end VerifiedDevelopmentalNavigation
