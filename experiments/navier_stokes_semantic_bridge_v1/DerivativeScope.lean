/-!
A small, independently kernel-checkable assumption-direction separator.

This is a logical abstraction about the *availability of hypotheses* at
derivative orders 4 and 5. It is NOT a formalisation of the Navier–Stokes
inverse operator, its estimates, the PDF's intended semantics, or the
universal theorem for arbitrary output derivative order m.
-/

namespace MathGraph.SemanticCorrespondence

/-- Supplying facts through order five also supplies them through order four. -/
theorem five_assumptions_imply_four (P : Nat → Prop)
    (h : ∀ j : Nat, j ≤ 5 → P j) :
    ∀ j : Nat, j ≤ 4 → P j := by
  intro j hj
  have h45 : (4 : Nat) ≤ 5 := by decide
  exact h j (Nat.le_trans hj h45)

/-- Uniform order-four availability does not imply order-five availability.
    Countermodel: choose P(j) := (j ≤ 4), then P(5) is false. -/
theorem four_assumptions_do_not_imply_five :
    ¬ (∀ P : Nat → Prop,
        (∀ j : Nat, j ≤ 4 → P j) →
        (∀ j : Nat, j ≤ 5 → P j)) := by
  intro h
  have h4 : ∀ j : Nat, j ≤ 4 → j ≤ 4 := by
    intro j hj
    exact hj
  have h5 : ∀ j : Nat, j ≤ 5 → j ≤ 4 :=
    h (fun j : Nat => j ≤ 4) h4
  have contradiction : (5 : Nat) ≤ 4 := h5 5 (by decide)
  exact (by decide : ¬ ((5 : Nat) ≤ 4)) contradiction

end MathGraph.SemanticCorrespondence
