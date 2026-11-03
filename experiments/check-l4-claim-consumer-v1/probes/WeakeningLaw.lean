namespace MathGraphClaim
-- Reusable logical obstruction: P-or-True does not authorize arbitrary P.
theorem weakeningDoesNotAuthorize : ¬ (∀ P : Prop, (P ∨ True) → P) := by
  intro h
  exact h False (Or.inr True.intro)
#print axioms weakeningDoesNotAuthorize
end MathGraphClaim
