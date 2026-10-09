import Mathlib

/-!
Source: Bastounis, Circelli, Hansen, arXiv:2610.08144v1, section 4.2,
page 15. The following namespace reproduces the displayed code, preserving
its Int/Nat/Rat domains, `!=` predicate and totalised sInf definition.
The namespace is added only to avoid collisions with the audit declarations.

The source contract below is an explicitly authored interpretation of
"the least natural number satisfying B, then 1/(n+1)". The kernel can check
mathematical correspondence with this contract. It cannot authenticate a
natural-language interpretation or decide arbitrary existence presuppositions.
-/
namespace PaperCode

def p_e (n x1 x2 : Int) : Int := x1 + x2 - n
def B_e (n : Nat) : Prop :=
  forall (x1 x2 : Nat), p_e (n : Int) (x1 : Int) (x2 : Int) != 0
noncomputable def n_e : Nat := sInf {n : Nat | B_e n}
noncomputable def r_e : Rat := 1 / (n_e + 1)
theorem example_3_1 : (r_e + 1) ^ 2 = r_e ^ 2 + 2 * r_e + 1 := by ring

end PaperCode

namespace MathGraph.Presupposition

/-- Independent, membership-preserving specification. No use of sInf. -/
def MinimumValueSpec (S : Set Nat) (r : Rat) : Prop :=
  ∃ n : Nat, n ∈ S ∧ (∀ m : Nat, m ∈ S → n ≤ m) ∧
    r = 1 / ((n : Rat) + 1)

/-- The implementation under audit: a total operation, including on empty sets. -/
noncomputable def totalizedValue (S : Set Nat) : Rat :=
  1 / ((sInf S : Rat) + 1)

/-- Exact bridge goal, frozen before implementation. The required condition
is nonemptiness; proving this equivalence is not a procedure for deciding it. -/
theorem minimum_spec_iff_nonempty (S : Set Nat) :
    MinimumValueSpec S (totalizedValue S) ↔ S.Nonempty := by
  fail "UNPROVED_SOURCE_TO_IMPLEMENTATION_BRIDGE"

end MathGraph.Presupposition
