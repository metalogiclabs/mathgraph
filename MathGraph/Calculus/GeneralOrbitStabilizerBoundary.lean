import MathGraph.Calculus.OrbitStabilizerBoundary

namespace MathGraph.Calculus

/-- A minimal self-contained group-action interface.  We state exactly the
laws needed by the orbit/stabilizer compression theorem instead of importing a
larger algebraic hierarchy. -/
structure BoundaryGroupAction (Γ Ω : Type) where
  one : Γ
  mul : Γ → Γ → Γ
  inv : Γ → Γ
  act : Γ → Ω → Ω
  one_mul : ∀ g, mul one g = g
  inv_mul : ∀ g, mul (inv g) g = one
  assoc : ∀ g h k, mul (mul g h) k = mul g (mul h k)
  one_act : ∀ x, act one x = x
  mul_act : ∀ g h x, act (mul g h) x = act g (act h x)

namespace BoundaryGroupAction

/-- The stabilizer predicate of a chosen orbit representative. -/
def Stabilizes {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g : Γ) : Prop :=
  A.act g a = a

/-- Two symmetry labels are operationally equivalent at a representative when
they land on the same orbit point. -/
def SameAt {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g h : Γ) : Prop :=
  A.act g a = A.act h a

/-- Relative displacement between two labels.  This is the element whose
membership in the stabilizer decides whether the labels produce the same
operational target. -/
def Relative {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (g h : Γ) : Γ :=
  A.mul (A.inv h) g

/-- If two labels produce the same orbit point, their relative displacement is
in the stabilizer of the representative. -/
theorem sameAt_implies_relative_stabilizes
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g h : Γ)
    (hSame : A.SameAt a g h) :
    A.Stabilizes a (A.Relative g h) := by
  unfold SameAt Relative Stabilizes at *
  rw [A.mul_act]
  rw [hSame]
  rw [← A.mul_act]
  rw [A.inv_mul]
  exact A.one_act a

/-- Conversely, if the relative displacement fixes the representative, then
the two labels land on the same orbit point. -/
theorem relative_stabilizes_implies_sameAt
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g h : Γ)
    (hStab : A.Stabilizes a (A.Relative g h)) :
    A.SameAt a g h := by
  unfold SameAt Relative Stabilizes at *
  have h1 : A.act (A.mul (A.inv h) g) a = a := hStab
  have h2 := congrArg (fun z => A.act h z) h1
  rw [← A.mul_act] at h2
  rw [A.assoc] at h2
  rw [A.inv_mul] at h2
  rw [A.one_mul] at h2
  exact h2

/-- Full orbit/stabilizer compression law: symmetry labels are distinguishable
at the boundary exactly up to the stabilizer of the chosen representative. -/
theorem sameAt_iff_relative_stabilizes
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g h : Γ) :
    A.SameAt a g h ↔ A.Stabilizes a (A.Relative g h) := by
  constructor
  · exact A.sameAt_implies_relative_stabilizes a g h
  · exact A.relative_stabilizes_implies_sameAt a g h

/-- A chosen representative plus one symmetry label reconstructs an ordered
external task without independently supplying a target point. -/
def TaskFromRepresentative
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g : Γ) :
    Stage26TaskBoundary Ω :=
  ⟨a, A.act g a⟩

/-- Replacing a symmetry label by a stabilizer-equivalent label leaves the
reconstructed task unchanged.  Hence the external symmetry label is needed
only modulo the stabilizer. -/
theorem task_eq_of_relative_stabilizes
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) (g h : Γ)
    (hStab : A.Stabilizes a (A.Relative g h)) :
    A.TaskFromRepresentative a g = A.TaskFromRepresentative a h := by
  apply Stage26TaskBoundary.ext
  · rfl
  · exact A.relative_stabilizes_implies_sameAt a g h hStab

/-- A canonical endogenous representative would have to be fixed by every
symmetry of the seed. -/
structure CanonicalRepresentative {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) where
  anchor : Ω
  invariant : ∀ g : Γ, A.act g anchor = anchor

/-- If the action has no globally fixed point, no symmetry-respecting
endogenous representative exists.  Some external orbit-representative choice is
therefore unavoidable. -/
theorem no_canonical_representative_of_no_global_fixed_point
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω)
    (hFree : ∀ a : Ω, ∃ g : Γ, A.act g a ≠ a) :
    ¬ Nonempty (CanonicalRepresentative A) := by
  intro h
  rcases h with ⟨c⟩
  rcases hFree c.anchor with ⟨g, hg⟩
  exact hg (c.invariant g)

/-- General orbit/stabilizer boundary certificate.

The operational content of a symmetry label relative to a chosen representative
is exactly its coset modulo the stabilizer: two labels reconstruct the same
ordered task iff their relative displacement fixes the representative.  If the
seed action has no globally fixed point, the representative itself cannot be
chosen canonically from the symmetric seed.  Thus the irreducible external
contact is a choice of orbit representative, while the remaining orientation
label is quotiented by its stabilizer. -/
theorem general_orbit_stabilizer_boundary_certificate
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω)
    (hFree : ∀ a : Ω, ∃ g : Γ, A.act g a ≠ a) :
    (∀ (a : Ω) (g h : Γ),
      A.SameAt a g h ↔ A.Stabilizes a (A.Relative g h)) ∧
    (∀ (a : Ω) (g h : Γ),
      A.Stabilizes a (A.Relative g h) →
      A.TaskFromRepresentative a g = A.TaskFromRepresentative a h) ∧
    ¬ Nonempty (CanonicalRepresentative A) := by
  refine ⟨?_, ?_, A.no_canonical_representative_of_no_global_fixed_point hFree⟩
  · intro a g h
    exact A.sameAt_iff_relative_stabilizes a g h
  · intro a g h hs
    exact A.task_eq_of_relative_stabilizes a g h hs

end BoundaryGroupAction

end MathGraph.Calculus
