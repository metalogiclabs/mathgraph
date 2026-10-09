import LeftWallFullRun
import LeftWallBootstrapInduction

/-!
# Exact resource and acceptance preservation for the actual fused compiler

All premises of the generic source/target transfer theorems are discharged
using separately qualified complete first-step and arbitrary active-step
equality. The only excluded clock is time zero, where the target deliberately
occupies a special startup control state. Work-head space agrees for all
times, including zero.
-/

namespace Metalogic.OpenAIMath.LeftWallComplete

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler
open Metalogic.OpenAIMath.LeftWallFusedCompiler

variable {q h : ℕ}

/-- Each physical target head visits the same integer-coded coordinate as
the source head, even at zero time before marker initialization. -/
theorem all_time_workhead_match (M : LeftMachine q h)
    (x : Word) (coins : CoinTape) (u : ℕ) (j : Fin 2) :
    ((compileFused M).run x coins u).workPos j =
      ((LeftBoundedMachine.run M x coins u).workPos : ℤ) := by
  cases u with
  | zero =>
      rfl
  | succ t =>
      change ((compileFused M).run x coins (t + 1)).workPos j =
        ((LeftBoundedMachine.run M x coins (t + 1)).workPos : ℤ)
      rw [LeftWallFullRun.positive_clock_full_run M x coins t]
      rfl

/-- The compiled two-track OAI machine incurs exactly factor two in the
pinned visited-sites space metric, not merely an upper bound. -/
theorem exact_two_track_space (M : LeftMachine q h)
    (x : Word) (coins : CoinTape) (t : ℕ) :
    (compileFused M).spaceThrough x coins t =
      2 * LeftBoundedMachine.spaceThrough M x coins t :=
  LeftWallSpace.compiled_space_eq_two_of_head_simulation M x coins t
    (all_time_workhead_match M x coins)

/-- Independent logarithmic-space specification for the Nat-indexed source. -/
def LeftLogSpace (M : LeftMachine q h) : Prop :=
  ∃ c : ℕ, 0 < c ∧ ∀ (x : Word) (coins : CoinTape) (t : ℕ),
    LeftBoundedMachine.spaceThrough M x coins t ≤
      c * Nat.clog 2 (x.length + 2)

/-- Exact two-track accounting promotes source LogSpace to OAI's pinned
LogSpace condition without any assumed finite-state encoding. -/
theorem compiled_LogSpace_of_left (M : LeftMachine q h)
    (hs : LeftLogSpace M) : (compileFused M).LogSpace := by
  obtain ⟨c, hc, hb⟩ := hs
  refine ⟨2 * c, by omega, ?_⟩
  intro x coins t
  rw [exact_two_track_space M x coins t]
  calc
    2 * LeftBoundedMachine.spaceThrough M x coins t ≤
        2 * (c * Nat.clog 2 (x.length + 2)) :=
          Nat.mul_le_mul_left 2 (hb x coins t)
    _ = (2 * c) * Nat.clog 2 (x.length + 2) := by ring

/-- The actual fused compiler—not an abstract interface—preserves the same
uniform finite coin-prefix acceptance probability at each positive clock. -/
theorem exact_positive_clock_probability (M : LeftMachine q h)
    (x : Word) (t : ℕ) :
    (compileFused M).acceptanceProbability x (t + 1) =
      LeftWallBootstrapInduction.leftAcceptanceProbability M x (t + 1) := by
  exact LeftWallBootstrapInduction.positive_clock_acceptance_equal
    M (compileFused M) x t
    (LeftWallSimulation.first_step_commutes M x)
    (LeftWallActiveStep.active_step_commutes M x)
    (fused_output_active M)

end Metalogic.OpenAIMath.LeftWallComplete
