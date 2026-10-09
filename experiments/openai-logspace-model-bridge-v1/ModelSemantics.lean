import OAI.Computability.Logspace.Deterministic

/-!
Independently authored operational lemmas about the exact OAI machine semantics.
These are general facts of the published finite-state machine model, not a
proof of equivalence with a separately formalized textbook Turing model.
-/

namespace Metalogic.OpenAIMath.ModelSemantics

open OAI.ExactDerandomization

variable {q w h : ℕ}

/-- A deterministic machine's one-step transition does not depend on the coin. -/
theorem deterministic_step_coin_irrelevant
    (M : Machine q w h) (hd : M.Deterministic) (x : Word)
    (u v : Bool) (c : Configuration q w h x.length) :
    M.step x u c = M.step x v c := by
  have heq (s : Fin (q + 1)) (i : Fin h → InputSymbol)
      (t : Fin w → Bool) (b₁ b₂ : Bool) :
      M.transition s i t b₁ = M.transition s i t b₂ := by
    change ∀ s i t, M.transition s i t false = M.transition s i t true at hd
    cases b₁ <;> cases b₂ <;> simp [hd]
  have hsame :=
    heq c.state (fun j => readInput x (c.inputPos j))
      (fun k => c.work k (c.workPos k)) u v
  unfold Machine.step
  cases ho : M.output c.state with
  | none => simp [ho, hsame]
  | some val => simp [ho]

/-- Coin-sequence choices do not change a deterministic machine's execution. -/
theorem deterministic_run_coin_irrelevant
    (M : Machine q w h) (hd : M.Deterministic) (x : Word)
    (a b : CoinTape) (t : ℕ) :
    M.run x a t = M.run x b t := by
  induction t with
  | zero => rfl
  | succ t ih =>
      change M.step x (a t) (M.run x a t) =
        M.step x (b t) (M.run x b t)
      rw [ih]
      exact deterministic_step_coin_irrelevant M hd x (a t) (b t) (M.run x b t)

/-- An output-bearing halting configuration is an absorbing state. -/
theorem halted_step_is_fixed
    (M : Machine q w h) (x : Word) (a : Bool)
    (c : Configuration q w h x.length) (out : Bool)
    (halt : M.output c.state = some out) :
    M.step x a c = c := by
  simp [Machine.step, halt]

/-- Two coin streams with the same prefix of length t produce the same state at t. -/
theorem run_depends_only_on_coin_prefix
    (M : Machine q w h) (x : Word)
    (a b : CoinTape) (t : ℕ)
    (hprefix : ∀ i, i < t → a i = b i) :
    M.run x a t = M.run x b t := by
  induction t with
  | zero => rfl
  | succ t ih =>
      have p : ∀ i, i < t → a i = b i :=
        fun i hi => hprefix i (Nat.lt_trans hi (Nat.lt_succ_self t))
      change M.step x (a t) (M.run x a t) =
        M.step x (b t) (M.run x b t)
      rw [ih p, hprefix t (Nat.lt_succ_self t)]


/-- Once a machine reaches an output-bearing state its complete configuration persists. -/
theorem halted_run_is_stable
    (M : Machine q w h) (x : Word) (coins : CoinTape) (t k : ℕ)
    (out : Bool) (halt : M.output (M.run x coins t).state = some out) :
    M.run x coins (t + k) = M.run x coins t := by
  induction k with
  | zero => simp
  | succ k ih =>
      calc
        M.run x coins (t + (k + 1)) =
            M.step x (coins (t + k)) (M.run x coins (t + k)) := by
              rw [Nat.add_succ]
              rfl
        _ = M.step x (coins (t + k)) (M.run x coins t) := by rw [ih]
        _ = M.run x coins t :=
              halted_step_is_fixed M x (coins (t + k)) (M.run x coins t) out halt

/-- Deterministic executions that reach the same full configuration have
    identical future configurations, independent of the coin positions. -/
theorem deterministic_repeat_propagates
    (M : Machine q w h) (hd : M.Deterministic) (x : Word)
    (coins : CoinTape) (t u k : ℕ)
    (same : M.run x coins t = M.run x coins u) :
    M.run x coins (t + k) = M.run x coins (u + k) := by
  induction k with
  | zero => simpa using same
  | succ k ih =>
      calc
        M.run x coins (t + (k + 1)) =
            M.step x (coins (t + k)) (M.run x coins (t + k)) := by
              rw [Nat.add_succ]
              rfl
        _ = M.step x (coins (t + k)) (M.run x coins (u + k)) := by rw [ih]
        _ = M.step x (coins (u + k)) (M.run x coins (u + k)) :=
              deterministic_step_coin_irrelevant M hd x
                (coins (t + k)) (coins (u + k)) (M.run x coins (u + k))
        _ = M.run x coins (u + (k + 1)) := by
              rw [Nat.add_succ]
              rfl

end Metalogic.OpenAIMath.ModelSemantics
