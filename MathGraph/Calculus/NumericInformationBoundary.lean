import MathGraph.Calculus.FiniteInformationBoundary

namespace MathGraph.Calculus
namespace BoundaryGroupAction

/-- Enumerate all Bool words of exactly `b` bits. -/
def allBitWords : Nat → List (List Bool)
  | 0 => [[]]
  | b + 1 =>
      (allBitWords b).map (fun w => false :: w) ++
      (allBitWords b).map (fun w => true :: w)

/-- The explicit enumeration contains exactly `2^b` words. -/
theorem allBitWords_length (b : Nat) :
    (allBitWords b).length = 2 ^ b := by
  induction b with
  | zero => rfl
  | succ b ih =>
      simp [allBitWords, ih, Nat.two_pow_succ]

/-- Every Bool word of length `b` occurs in the explicit enumeration. -/
theorem mem_allBitWords_of_length
    (w : List Bool) (b : Nat) (hw : w.length = b) :
    w ∈ allBitWords b := by
  induction b generalizing w with
  | zero =>
      cases w with
      | nil => simp [allBitWords]
      | cons x xs => simp at hw
  | succ b ih =>
      cases w with
      | nil => simp at hw
      | cons x xs =>
          have hxs : xs.length = b := by
            simpa using Nat.succ.inj hw
          cases x with
          | false =>
              simp [allBitWords, ih xs hxs]
          | true =>
              simp [allBitWords, ih xs hxs]

/-- A list-level separated family.  This avoids importing cardinality machinery:
each head is operationally distinct from every later label, recursively. -/
def SeparatedList
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω) : List Γ → Prop
  | [] => True
  | g :: gs =>
      (∀ h : Γ, h ∈ gs → ¬ A.SameAt a g h) ∧
      A.SeparatedList a gs

/-- Faithfulness turns operational separation into distinct codewords. -/
theorem encoded_nodup_of_separated
    {Γ Ω Code : Type} [DecidableEq Code]
    (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (encode : Γ → Code) (hFaithful : A.FaithfulAt a encode) :
    ∀ labels : List Γ,
      A.SeparatedList a labels →
      (labels.map encode).Nodup := by
  intro labels
  induction labels with
  | nil =>
      intro _
      simp
  | cons g gs ih =>
      intro hSep
      have hHead : ∀ h : Γ, h ∈ gs → ¬ A.SameAt a g h := hSep.1
      have hTail : A.SeparatedList a gs := hSep.2
      have hNotMem : encode g ∉ gs.map encode := by
        intro hm
        rw [List.mem_map] at hm
        rcases hm with ⟨h, hh, heq⟩
        have hSame : A.SameAt a g h := hFaithful g h heq.symm
        exact hHead h hh hSame
      exact List.nodup_cons.mpr ⟨hNotMem, ih hTail⟩

/-- Exact finite capacity theorem for a `b`-bit external boundary.

If each operational label is encoded by exactly `b` Bool bits, the code is
faithful, and the finite label list is operationally separated, then the number
of labels is at most `2^b`.  This is the numeric form of the prior
representation-independent injectivity lower bound. -/
theorem separated_orbit_choices_le_two_pow_bits
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (b : Nat) (labels : List Γ) (encode : Γ → List Bool)
    (hWidth : ∀ g : Γ, (encode g).length = b)
    (hFaithful : A.FaithfulAt a encode)
    (hSeparated : A.SeparatedList a labels) :
    labels.length ≤ 2 ^ b := by
  have hNodup : (labels.map encode).Nodup :=
    A.encoded_nodup_of_separated a encode hFaithful labels hSeparated
  have hSubset : labels.map encode ⊆ allBitWords b := by
    intro w hw
    rw [List.mem_map] at hw
    rcases hw with ⟨g, hg, rfl⟩
    exact mem_allBitWords_of_length (encode g) b (hWidth g)
  have hLe : (labels.map encode).length ≤ (allBitWords b).length :=
    hNodup.length_le_of_subset hSubset
  rw [List.length_map, allBitWords_length] at hLe
  exact hLe

/-- Strict pigeonhole corollary: more than `2^b` separated operational choices
cannot be faithfully represented by a fixed-width `b`-bit boundary code. -/
theorem no_b_bit_code_above_capacity
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (b : Nat) (labels : List Γ)
    (hTooMany : 2 ^ b < labels.length)
    (encode : Γ → List Bool)
    (hWidth : ∀ g : Γ, (encode g).length = b)
    (hSeparated : A.SeparatedList a labels) :
    ¬ A.FaithfulAt a encode := by
  intro hFaithful
  have hCap : labels.length ≤ 2 ^ b :=
    A.separated_orbit_choices_le_two_pow_bits a b labels encode
      hWidth hFaithful hSeparated
  exact (Nat.not_lt_of_ge hCap) hTooMany

/-- Numeric information-boundary certificate. -/
theorem numeric_information_boundary_certificate
    {Γ Ω : Type} (A : BoundaryGroupAction Γ Ω) (a : Ω)
    (b : Nat) (labels : List Γ) (encode : Γ → List Bool)
    (hWidth : ∀ g : Γ, (encode g).length = b)
    (hFaithful : A.FaithfulAt a encode)
    (hSeparated : A.SeparatedList a labels) :
    labels.length ≤ 2 ^ b :=
  A.separated_orbit_choices_le_two_pow_bits a b labels encode
    hWidth hFaithful hSeparated

end BoundaryGroupAction
end MathGraph.Calculus
