import LeftWallSpace

/-!
# Reusable same-clock bootstrap induction and finite-coin bridge

A target with one distinguished initialization state may disagree with its
source at time zero, while exactly matching source configurations at every
positive clock. First-step and active-step hypotheses are kept explicit:
no unqualified compiler is silently accepted.
-/

namespace Metalogic.OpenAIMath.LeftWallBootstrapInduction

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler

variable {q h : ℕ}

/-- The source's finite-prefix coin distribution is counted directly from
its independent Nat-tape executions. -/
def leftAcceptanceProbability (M : LeftMachine q h) (x : Word) (t : ℕ) : ℚ :=
  ((Finset.univ.filter (fun bits : Fin t → Bool =>
    M.output (LeftBoundedMachine.run M x (Machine.extendCoins bits) t).state =
      some true)).card : ℚ) / (2 : ℚ) ^ t

/-- Generic positive-clock run law: first step plus all active steps,
not an assumed equality at the physically distinct startup configuration. -/
theorem run_succ_commutes_of_first_and_active
    (M : LeftMachine q h) (T : Machine (q + 1) 2 h)
    (x : Word) (coins : CoinTape) (t : ℕ)
    (hfirst : ∀ b : Bool,
      T.step x b (T.initial x.length) =
        encode (LeftBoundedMachine.step M x b
          (LeftBoundedMachine.initial M x.length)))
    (hactive : ∀ (b : Bool) (c : LeftConfiguration q h x.length),
      T.step x b (encode c) =
        encode (LeftBoundedMachine.step M x b c)) :
    T.run x coins (t + 1) =
      encode (LeftBoundedMachine.run M x coins (t + 1)) := by
  induction t with
  | zero =>
      change T.step x (coins 0) (T.initial x.length) =
        encode (LeftBoundedMachine.step M x (coins 0)
          (LeftBoundedMachine.initial M x.length))
      exact hfirst (coins 0)
  | succ t ih =>
      change T.step x (coins (t + 1)) (T.run x coins (t + 1)) =
        encode (LeftBoundedMachine.step M x (coins (t + 1))
          (LeftBoundedMachine.run M x coins (t + 1)))
      rw [ih]
      exact hactive (coins (t + 1)) (LeftBoundedMachine.run M x coins (t + 1))

/-- A target that preserves source output on active states has exactly the
source acceptance probability at every positive clock, with no extra coin. -/
theorem positive_clock_acceptance_equal
    (M : LeftMachine q h) (T : Machine (q + 1) 2 h)
    (x : Word) (t : ℕ)
    (hfirst : ∀ b : Bool,
      T.step x b (T.initial x.length) =
        encode (LeftBoundedMachine.step M x b
          (LeftBoundedMachine.initial M x.length)))
    (hactive : ∀ (b : Bool) (c : LeftConfiguration q h x.length),
      T.step x b (encode c) =
        encode (LeftBoundedMachine.step M x b c))
    (houtput : ∀ st : Fin (q + 1),
      T.output (activeState st) = M.output st) :
    T.acceptanceProbability x (t + 1) =
      leftAcceptanceProbability M x (t + 1) := by
  have hout (bits : Fin (t + 1) → Bool) :
      T.output (T.run x (Machine.extendCoins bits) (t + 1)).state =
      M.output (LeftBoundedMachine.run M x
        (Machine.extendCoins bits) (t + 1)).state := by
    rw [run_succ_commutes_of_first_and_active M T x
      (Machine.extendCoins bits) t hfirst hactive]
    change T.output
      (activeState (LeftBoundedMachine.run M x
        (Machine.extendCoins bits) (t + 1)).state) =
      M.output (LeftBoundedMachine.run M x
        (Machine.extendCoins bits) (t + 1)).state
    exact houtput _
  have hfilter :
      (Finset.univ.filter (fun bits : Fin (t + 1) → Bool =>
        T.output (T.run x (Machine.extendCoins bits) (t + 1)).state =
          some true)) =
      (Finset.univ.filter (fun bits : Fin (t + 1) → Bool =>
        M.output (LeftBoundedMachine.run M x
          (Machine.extendCoins bits) (t + 1)).state = some true)) := by
    ext bits
    simp only [Finset.mem_filter, Finset.mem_univ, true_and]
    rw [hout bits]
  unfold Machine.acceptanceProbability leftAcceptanceProbability
  rw [hfilter]

end Metalogic.OpenAIMath.LeftWallBootstrapInduction
