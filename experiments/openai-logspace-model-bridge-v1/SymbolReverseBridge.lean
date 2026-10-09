import SymbolProbabilityBridge

/-!
# Reverse Boolean-machine bridge, pinned OpenAI -> independent symbol semantics

This reverse embedding uses the actual Bool alphabet and copies the exact
OpenAI transition table. The two configuration types are independently
defined structures; their transition functions and runs must be checked
rather than assumed identical.
-/-

namespace Metalogic.OpenAIMath.SymbolReverseBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge
open Metalogic.OpenAIMath.SymbolStepSimulation
open Metalogic.OpenAIMath.SymbolRunBridge
open Metalogic.OpenAIMath.SymbolResourceBridge
open Metalogic.OpenAIMath.SymbolProbabilityBridge

variable {q w h : ℕ}

/-- Reverse translation of the exact pinned OAI Boolean machine. -/
def fromOAIMachine (M : Machine q w h) : SymbolMachine Bool q w h where
  initialState := M.initialState
  output := M.output
  transition := fun st inp reads coin =>
    let a := M.transition st inp reads coin
    { nextState := a.nextState
      write := a.write
      workMove := a.workMove
      inputMove := a.inputMove }

/-- Represent an actual OAI Boolean configuration as an independent source
symbol configuration, preserving its entire tapes rather than observations. -/
def asSourceConfiguration {n : ℕ} (c : Configuration q w h n) :
    SymbolConfiguration Bool q w h n where
  state := c.state
  inputPos := c.inputPos
  workPos := c.workPos
  work := c.work

theorem source_initial_eq_OAI (M : Machine q w h) (n : ℕ) :
    sourceInitial (fromOAIMachine M) false n =
      asSourceConfiguration (M.initial n) := by
  rfl

/-- No compiler theorem is used to assume this: verify the equality of the
independently defined one-step transition functions on arbitrary OAI states. -/
theorem source_step_eq_OAI
    (M : Machine q w h) (x : Word) (coin : Bool)
    (c : Configuration q w h x.length) :
    sourceStep (fromOAIMachine M) x coin (asSourceConfiguration c) =
      asSourceConfiguration (M.step x coin c) := by
  cases ho : M.output c.state with
  | some a =>
      simp [sourceStep, Machine.step, fromOAIMachine,
        asSourceConfiguration, ho]
  | none =>
      apply SymbolConfiguration.ext
      · simp [sourceStep, Machine.step, fromOAIMachine,
          asSourceConfiguration, ho]
      · simp [sourceStep, Machine.step, fromOAIMachine,
          asSourceConfiguration, ho]
      · simp [sourceStep, Machine.step, fromOAIMachine,
          asSourceConfiguration, ho]
      · funext k z
        simp [sourceStep, Machine.step, fromOAIMachine,
          asSourceConfiguration, writeAllSource, Function.update, ho]

/-- Exact Boolean-source execution agrees with the pinned OpenAI run at
every clock, input and coin stream, including the complete work tapes. -/
theorem source_run_eq_OAI
    (M : Machine q w h) (x : Word) (coins : CoinTape) (t : ℕ) :
    sourceRun (fromOAIMachine M) false x coins t =
      asSourceConfiguration (M.run x coins t) := by
  induction t with
  | zero =>
      exact source_initial_eq_OAI M x.length
  | succ t ih =>
      change sourceStep (fromOAIMachine M) x (coins t)
          (sourceRun (fromOAIMachine M) false x coins t) =
        asSourceConfiguration (M.step x (coins t) (M.run x coins t))
      rw [ih]
      exact source_step_eq_OAI M x (coins t) (M.run x coins t)

/-- The reverse direction preserves the visited-sites space measure exactly,
not just asymptotically. -/
theorem source_spaceThrough_eq_OAI
    (M : Machine q w h) (x : Word) (coins : CoinTape) (t : ℕ) :
    sourceSpaceThrough (fromOAIMachine M) false x coins t =
      M.spaceThrough x coins t := by
  unfold sourceSpaceThrough Machine.spaceThrough
  apply Finset.sum_congr rfl
  intro k _
  congr 1
  funext u
  have hr := source_run_eq_OAI M x coins u
  exact congrArg (fun c : SymbolConfiguration Bool q w h x.length =>
    c.workPos k) hr

end Metalogic.OpenAIMath.SymbolReverseBridge
