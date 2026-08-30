import MathGraph.Calculus.GeneralOrbitStabilizerBoundary

namespace MathGraph.Calculus

namespace BoundaryGroupAction

/-- A boundary code is faithful at a chosen representative when equal codewords
never collapse two operationally different orbit points.  This is the weakest
losslessness condition needed for an external boundary representation. -/
def FaithfulAt
    {Γ Ω Code : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (encode : Γ → Code) : Prop :=
  ∀ g h : Γ, encode g = encode h → A.SameAt a g h

/-- A family of symmetry labels is pairwise operationally separated when every
distinct pair lands on different orbit points. -/
def PairwiseOrbitSeparated
    {Γ Ω I : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (labels : I → Γ) : Prop :=
  ∀ i j : I, i ≠ j → ¬ A.SameAt a (labels i) (labels j)

/-- Information lower bound, in representation-independent form.

For any pairwise-separated family of operational orbit choices, every faithful
boundary code must be injective on that family.  Thus a lossless external code
must contain at least as many distinguishable codewords as there are distinct
operational orbit points it is required to represent. -/
theorem faithful_code_injective_on_separated_family
    {Γ Ω I Code : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (labels : I → Γ) (encode : Γ → Code)
    (hFaithful : A.FaithfulAt a encode)
    (hSeparated : A.PairwiseOrbitSeparated a labels) :
    Function.Injective (fun i : I => encode (labels i)) := by
  intro i j hCode
  by_contra hne
  have hSame : A.SameAt a (labels i) (labels j) :=
    hFaithful (labels i) (labels j) hCode
  exact hSeparated i j hne hSame

/-- Orbit/stabilizer form of the same lower bound.  A faithful code cannot give
the same codeword to two labels whose relative displacement lies outside the
stabilizer. -/
theorem faithful_code_separates_nonstabilizer_labels
    {Γ Ω Code : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (encode : Γ → Code) (hFaithful : A.FaithfulAt a encode)
    (g h : Γ) (hOutside : ¬ A.Stabilizes a (A.Relative g h)) :
    encode g ≠ encode h := by
  intro hCode
  have hSame : A.SameAt a g h := hFaithful g h hCode
  exact hOutside ((A.sameAt_iff_relative_stabilizes a g h).1 hSame)

/-- A strict finite consequence: a one-bit Bool boundary cannot faithfully
encode three pairwise-distinct operational orbit points.

This is the first nontrivial finite-information obstruction beyond the earlier
two-point / one-bit witness. -/
theorem one_bit_cannot_encode_three_separated_orbit_points
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (g0 g1 g2 : Γ)
    (h01 : ¬ A.SameAt a g0 g1)
    (h02 : ¬ A.SameAt a g0 g2)
    (h12 : ¬ A.SameAt a g1 g2) :
    ¬ A.FaithfulAt a (fun g =>
      if A.SameAt a g g0 then false else
      if A.SameAt a g g1 then true else false) := by
  intro hFaithful
  let encode : Γ → Bool := fun g =>
    if A.SameAt a g g0 then false else
    if A.SameAt a g g1 then true else false
  have h0 : encode g0 = false := by
    unfold encode
    simp [SameAt]
  have h1 : encode g1 = true := by
    unfold encode
    have h10 : ¬ A.SameAt a g1 g0 := by
      intro hs
      exact h01 hs.symm
    simp [h10, SameAt]
  have h2 : encode g2 = false := by
    unfold encode
    have h20 : ¬ A.SameAt a g2 g0 := by
      intro hs
      exact h02 hs.symm
    have h21 : ¬ A.SameAt a g2 g1 := by
      intro hs
      exact h12 hs.symm
    simp [h20, h21]
  have hSame02 : A.SameAt a g0 g2 := by
    apply hFaithful g0 g2
    rw [h0, h2]
  exact h02 hSame02

/-- Encoder-independent one-bit pigeonhole theorem.  If three labels are
pairwise operationally distinct, *no* Bool-valued encoding can be faithful. -/
theorem no_bool_code_for_three_separated_orbit_points
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (g0 g1 g2 : Γ)
    (h01 : ¬ A.SameAt a g0 g1)
    (h02 : ¬ A.SameAt a g0 g2)
    (h12 : ¬ A.SameAt a g1 g2)
    (encode : Γ → Bool) :
    ¬ A.FaithfulAt a encode := by
  intro hFaithful
  have e01 : encode g0 ≠ encode g1 := by
    intro he
    exact h01 (hFaithful g0 g1 he)
  have e02 : encode g0 ≠ encode g2 := by
    intro he
    exact h02 (hFaithful g0 g2 he)
  have e12 : encode g1 ≠ encode g2 := by
    intro he
    exact h12 (hFaithful g1 g2 he)
  cases h0 : encode g0 <;> cases h1 : encode g1 <;> cases h2 : encode g2
  · exact e01 (by rw [h0, h1])
  · exact e01 (by rw [h0, h1])
  · exact e02 (by rw [h0, h2])
  · exact e12 (by rw [h1, h2])
  · exact e12 (by rw [h1, h2])
  · exact e02 (by rw [h0, h2])
  · exact e01 (by rw [h0, h1])
  · exact e01 (by rw [h0, h1])

/-- Finite-information boundary certificate.

The general theorem is cardinality-free and therefore applies to any index and
code types: a faithful code embeds every separated operational family.  The
Bool corollary proves a strict capacity obstruction already at three orbit
points, showing that the earlier one-bit result is specific to a two-choice
orbit and does not survive larger operational symmetry classes. -/
theorem finite_information_boundary_certificate
    {Γ Ω I Code : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (labels : I → Γ) (encode : Γ → Code)
    (hFaithful : A.FaithfulAt a encode)
    (hSeparated : A.PairwiseOrbitSeparated a labels) :
    Function.Injective (fun i : I => encode (labels i)) :=
  A.faithful_code_injective_on_separated_family a labels encode hFaithful hSeparated

end BoundaryGroupAction

end MathGraph.Calculus
