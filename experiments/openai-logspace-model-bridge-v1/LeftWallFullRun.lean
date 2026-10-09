import LeftWallSimulation
import LeftWallActiveStep

/-!
# Unconditional positive-clock full-run simulation for a Nat-indexed,
left-bounded single work tape into the pinned two-track OAI machine.

The target starts in a distinct startup control state. At time zero its
configuration is not identified with any encoded source configuration.
For every positive time, the fused first-step proof and arbitrary active-step
proof imply equality of all configuration fields, including the infinite tapes.
-/

namespace Metalogic.OpenAIMath.LeftWallFullRun

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler
open Metalogic.OpenAIMath.LeftWallFusedCompiler

variable {q h : ℕ}

/-- At all positive clocks, source and compiled target have identical complete
configurations after encoding, using the same coin tape with no time shift. -/
theorem positive_clock_full_run (M : LeftMachine q h)
    (x : Word) (coins : CoinTape) (t : ℕ) :
    (compileFused M).run x coins (t + 1) =
      encode (LeftBoundedMachine.run M x coins (t + 1)) := by
  induction t with
  | zero =>
      change (compileFused M).step x (coins 0)
          ((compileFused M).initial x.length) =
        encode (LeftBoundedMachine.step M x (coins 0)
          (LeftBoundedMachine.initial M x.length))
      exact LeftWallSimulation.first_step_commutes M x (coins 0)
  | succ t ih =>
      change (compileFused M).step x (coins (t + 1))
          ((compileFused M).run x coins (t + 1)) =
        encode (LeftBoundedMachine.step M x (coins (t + 1))
          (LeftBoundedMachine.run M x coins (t + 1)))
      rw [ih]
      exact LeftWallActiveStep.active_step_commutes M x (coins (t + 1))
        (LeftBoundedMachine.run M x coins (t + 1))

/-- Protected halting/output observation commutes at every positive clock. -/
theorem positive_clock_output_commutes (M : LeftMachine q h)
    (x : Word) (coins : CoinTape) (t : ℕ) :
    (compileFused M).output
        ((compileFused M).run x coins (t + 1)).state =
      M.output (LeftBoundedMachine.run M x coins (t + 1)).state := by
  rw [positive_clock_full_run M x coins t]
  exact fused_output_active M
    (LeftBoundedMachine.run M x coins (t + 1)).state

end Metalogic.OpenAIMath.LeftWallFullRun
