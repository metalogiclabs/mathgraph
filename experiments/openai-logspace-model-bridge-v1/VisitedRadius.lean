import FiniteEnvelope

/-!
An intermediate-value theorem for any integer walk whose increments are at
most one, applied to OpenAI's pinned unit-step work-head semantics.
This establishes coverage of every intermediate integer position but does
not yet deduce the quantitative Finset.card visited-count inequality.
-/

namespace Metalogic.OpenAIMath.VisitedRadius

open OAI.ExactDerandomization

theorem integer_walk_covers_nonnegative_segment
    (p : ℕ → ℤ) (h0 : p 0 = 0)
    (hup : ∀ t, p (t + 1) ≤ p t + 1) :
    ∀ t z, 0 ≤ z → z ≤ p t →
      ∃ u, u ≤ t ∧ p u = z := by
  intro t
  induction t with
  | zero =>
      intro z hz0 hzt
      refine ⟨0, le_rfl, ?_⟩
      rw [h0]
      omega
  | succ t ih =>
      intro z hz0 hzt
      by_cases hprior : z ≤ p t
      · obtain ⟨u,hu,heq⟩ := ih z hz0 hprior
        exact ⟨u, by omega, heq⟩
      · have hstep := hup t
        refine ⟨t + 1, le_rfl, ?_⟩
        omega

theorem integer_walk_covers_nonpositive_segment
    (p : ℕ → ℤ) (h0 : p 0 = 0)
    (hdown : ∀ t, p t ≤ p (t + 1) + 1) :
    ∀ t z, p t ≤ z → z ≤ 0 →
      ∃ u, u ≤ t ∧ p u = z := by
  intro t
  induction t with
  | zero =>
      intro z hzt hz0
      refine ⟨0, le_rfl, ?_⟩
      rw [h0]
      omega
  | succ t ih =>
      intro z hzt hz0
      by_cases hprior : p t ≤ z
      · obtain ⟨u,hu,heq⟩ := ih z hprior hz0
        exact ⟨u, by omega, heq⟩
      · have hstep := hdown t
        refine ⟨t + 1, le_rfl, ?_⟩
        omega

/-- Every integer between 0 and a nonnegative reached work-head coordinate
has really been visited by that head at some earlier time. -/
theorem oai_head_visits_positive_intermediate
    {q w h : ℕ} (M : Machine q w h) (x : Word)
    (coins : CoinTape) (k : Fin w) (t : ℕ) (z : ℤ)
    (hzero : 0 ≤ z) (hgoal : z ≤ (M.run x coins t).workPos k) :
    ∃ u, u ≤ t ∧ (M.run x coins u).workPos k = z := by
  apply integer_walk_covers_nonnegative_segment
    (fun u => (M.run x coins u).workPos k) (by rfl)
  · intro u
    exact (FiniteEnvelope.machine_step_workhead_unit_bounds
      M x (coins u) (M.run x coins u) k).1
  · exact hzero
  · exact hgoal

/-- Every integer between a reached nonpositive head coordinate and zero
has also been visited by that head. -/
theorem oai_head_visits_negative_intermediate
    {q w h : ℕ} (M : Machine q w h) (x : Word)
    (coins : CoinTape) (k : Fin w) (t : ℕ) (z : ℤ)
    (hgoal : (M.run x coins t).workPos k ≤ z) (hzero : z ≤ 0) :
    ∃ u, u ≤ t ∧ (M.run x coins u).workPos k = z := by
  apply integer_walk_covers_nonpositive_segment
    (fun u => (M.run x coins u).workPos k) (by rfl)
  · intro u
    exact (FiniteEnvelope.machine_step_workhead_unit_bounds
      M x (coins u) (M.run x coins u) k).2
  · exact hgoal
  · exact hzero

end Metalogic.OpenAIMath.VisitedRadius
