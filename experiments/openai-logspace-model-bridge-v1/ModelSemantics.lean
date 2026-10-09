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
  unfold Machine.step
  cases ho : M.output c.state with
  | none => simp [ho, heq]
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
    (prefix : ∀ i, i < t → a i = b i) :
    M.run x a t = M.run x b t := by
  induction t with
  | zero => rfl
  | succ t ih =>
      have p : ∀ i, i < t → a i = b i :=
        fun i hi => prefix i (Nat.lt_trans hi (Nat.lt_succ_self t))
      change M.step x (a t) (M.run x a t) =
        M.step x (b t) (M.run x b t)
      rw [ih p, prefix t (Nat.lt_succ_self t)]

end Metalogic.OpenAIMath.ModelSemantics
