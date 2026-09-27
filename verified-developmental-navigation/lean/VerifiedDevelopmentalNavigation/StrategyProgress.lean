namespace VerifiedDevelopmentalNavigation

/-!
# Well-founded strategy progress

A domain-independent closeout theorem for Crystal-style goal-relative strategy
certificates.

The acting side need not preserve every lawful continuation. It is enough to
choose a strategy step such that, after every protected adversarial response,
either the goal has been reached or a natural-valued rank strictly decreases.

This is the abstract shape used by Crystal Chess: one compiled move is an
existential witness, the opponent replies universally, and an exact verifier
checks the resulting two-ply transition.
-/

namespace StrategyProgress

variable {S : Type}

/-- A finite path of exactly `n` transitions that avoids the goal at every
visited state, including its final state. -/
def AvoidsFor (goal : S → Prop) (step : S → S → Prop) : Nat → S → Prop
  | 0, s => ¬ goal s
  | n + 1, s =>
      ¬ goal s ∧ ∃ t, step s t ∧ AvoidsFor goal step n t

theorem avoidsFor_notGoal
    {goal : S → Prop} {step : S → S → Prop}
    {n : Nat} {s : S}
    (h : AvoidsFor goal step n s) :
    ¬ goal s := by
  cases n with
  | zero =>
      exact h
  | succ n =>
      exact h.1

/-- Every certified strategy/adversary round either reaches the goal or
strictly decreases the well-founded natural rank. -/
def Progresses
    (rank : S → Nat) (goal : S → Prop) (step : S → S → Prop) : Prop :=
  ∀ ⦃s t⦄, ¬ goal s → step s t → goal t ∨ rank t < rank s

/-- A goal-avoiding path cannot contain more transitions than the starting
rank permits. In particular, avoiding for `rank s + 1` transitions is
impossible.

The proof deliberately uses only a natural-valued rank and ordinary induction;
no chess-specific semantics enter here. -/
theorem no_avoidance_beyond_rank
    (rank : S → Nat) (goal : S → Prop) (step : S → S → Prop)
    (hprogress : Progresses rank goal step) :
    ∀ r s, rank s ≤ r → ¬ AvoidsFor goal step (r + 1) s := by
  intro r
  induction r with
  | zero =>
      intro s hrs hpath
      change ¬ goal s ∧ ∃ t, step s t ∧ AvoidsFor goal step 0 t at hpath
      rcases hpath with ⟨hnot, t, hstep, htail⟩
      have hp := hprogress hnot hstep
      cases hp with
      | inl hgoal =>
          exact (avoidsFor_notGoal htail) hgoal
      | inr hlt =>
          have hs0 : rank s = 0 := Nat.eq_zero_of_le_zero hrs
          have ht0 : rank t < 0 := by
            simpa [hs0] using hlt
          exact (Nat.not_lt_zero (rank t)) ht0
  | succ r ih =>
      intro s hrs hpath
      change
        ¬ goal s ∧
          ∃ t, step s t ∧ AvoidsFor goal step (r + 1) t
        at hpath
      rcases hpath with ⟨hnot, t, hstep, htail⟩
      have hp := hprogress hnot hstep
      cases hp with
      | inl hgoal =>
          exact (avoidsFor_notGoal htail) hgoal
      | inr hlt =>
          have htlt : rank t < Nat.succ r :=
            Nat.lt_of_lt_of_le hlt hrs
          have htle : rank t ≤ r :=
            Nat.le_of_lt_succ htlt
          exact ih t htle htail

/-- Any infinite play following certified strategy/adversary rounds must hit
the goal. Equivalently, an infinite goal-avoiding play is impossible. -/
theorem no_infinite_goal_avoiding_play
    (rank : S → Nat) (goal : S → Prop) (step : S → S → Prop)
    (hprogress : Progresses rank goal step)
    (play : Nat → S)
    (hstep : ∀ n, step (play n) (play (n + 1))) :
    ¬ (∀ n, ¬ goal (play n)) := by
  intro havoid

  have hprefix :
      ∀ n k, AvoidsFor goal step n (play k) := by
    intro n
    induction n with
    | zero =>
        intro k
        exact havoid k
    | succ n ih =>
        intro k
        exact ⟨havoid k, ⟨play (k + 1), hstep k, ih (k + 1)⟩⟩

  have htooLong :
      AvoidsFor goal step (rank (play 0) + 1) (play 0) :=
    hprefix (rank (play 0) + 1) 0

  exact
    (no_avoidance_beyond_rank
      rank goal step hprogress
      (rank (play 0)) (play 0) (Nat.le_refl _)) htooLong

end StrategyProgress

end VerifiedDevelopmentalNavigation
