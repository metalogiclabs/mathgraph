/-!
MathGraph foundation: a universal strict economic compounding guarantee is
mathematically impossible without assumptions on baselines and task families.

This is a negative theorem, not a claim that useful bounded compounding
cannot occur.
-/
namespace MathGraphEconomicBoundary

theorem no_strict_improvement_over_zero (candidateCost : Nat) :
    ¬ candidateCost < 0 := by
  intro h
  exact Nat.not_lt_zero candidateCost h

theorem no_universal_strict_cost_dominance
    (candidateCost : Nat → Nat) :
    ¬ (∀ baselineCost : Nat → Nat,
      ∀ task : Nat, candidateCost task < baselineCost task) := by
  intro h
  have impossible := h (fun _ => 0) 0
  exact Nat.not_lt_zero (candidateCost 0) impossible

theorem equality_does_not_imply_strict_gain
    (candidate baseline : Nat) (tie : candidate = baseline) :
    ¬ candidate < baseline := by
  intro h
  rw [tie] at h
  exact Nat.lt_irrefl baseline h

end MathGraphEconomicBoundary
