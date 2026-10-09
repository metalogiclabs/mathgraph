import LeftWallComplete

/-!
# Deterministic class inclusion from an independently authored left-bounded,
single-work-tape model into pinned OAI L.

The source has Nat-indexed cells and a saturating left wall; the target has
two synchronized integer-indexed work heads. An initially halted source
requires one target startup transition, so decisions transfer at clock t+1.
No reverse textbook-model simulation is claimed.
-/

namespace Metalogic.OpenAIMath.LeftWallDeterministicClass

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler
open Metalogic.OpenAIMath.LeftWallFusedCompiler
open Metalogic.OpenAIMath.LeftWallComplete

variable {q h : ℕ}

/-- Determinism in the source's own finite-control transition table. -/
def LeftDeterministic (M : LeftMachine q h) : Prop :=
  ∀ (st : Fin (q + 1)) (inp : Fin h → InputSymbol) (bit : Bool),
    M.transition st inp bit false = M.transition st inp bit true

/-- Source output/decider contract on actual independently defined runs. -/
def LeftDecides (M : LeftMachine q h) (A : Language) : Prop :=
  ∀ x : Word, ∃ (t : ℕ) (b : Bool),
    (b = true ↔ x ∈ A) ∧ ∀ coins : CoinTape,
      M.output (LeftBoundedMachine.run M x coins t).state = some b

def LeftL : Set Language :=
  { A | ∃ (q h : ℕ) (M : LeftMachine q h),
    LeftDeterministic M ∧ LeftLogSpace M ∧ LeftDecides M A }

/-- Compiling a coin-independent source transition preserves the pinned
OAI transition's coin-independence even in its fused startup state. -/
theorem compiled_deterministic_of_left (M : LeftMachine q h)
    (hd : LeftDeterministic M) :
    (compileFused M).Deterministic := by
  intro st inp read
  cases hs : decodeActive st with
  | none =>
      cases hout : M.output M.initialState with
      | some b =>
          simp [compileFused, hs, hout]
      | none =>
          have ht := hd M.initialState inp false
          simpa [compileFused, hs, hout, ht]
  | some sourceState =>
      have ht := hd sourceState inp (read 0)
      simpa [compileFused, hs, ht]

/-- A source configuration with an output has absorbing transition
semantics; once halted, the next source clock has the same output. -/
theorem source_output_persists_one
    (M : LeftMachine q h) (x : Word) (coins : CoinTape)
    (t : ℕ) (b : Bool)
    (hb : M.output (LeftBoundedMachine.run M x coins t).state = some b) :
    M.output (LeftBoundedMachine.run M x coins (t + 1)).state = some b := by
  change M.output (LeftBoundedMachine.step M x (coins t)
      (LeftBoundedMachine.run M x coins t)).state = some b
  simp [LeftBoundedMachine.step, hb]

/-- Convert a source decision at clock t to the exact same verdict at the
target's positive clock t+1. This handles initially halting sources, too. -/
theorem compiled_decides_of_left (M : LeftMachine q h)
    (A : Language) (hd : LeftDecides M A) :
    (compileFused M).Decides A := by
  intro x
  obtain ⟨t, b, hclass, hout⟩ := hd x
  refine ⟨t + 1, b, hclass, ?_⟩
  intro coins
  rw [LeftWallFullRun.positive_clock_output_commutes M x coins t]
  exact source_output_persists_one M x coins t b (hout coins)

/-- Forward class inclusion for a genuinely left-bounded, one-work-tape
machine convention, using exactly two OAI Boolean work heads. -/
theorem left_L_subset_OAI_L : LeftL ⊆ L := by
  intro A hA
  obtain ⟨q, h, M, hd, hs, hdec⟩ := hA
  exact ⟨q + 1, 2, h, compileFused M,
    compiled_deterministic_of_left M hd,
    compiled_LogSpace_of_left M hs,
    compiled_decides_of_left M A hdec⟩

end Metalogic.OpenAIMath.LeftWallDeterministicClass
