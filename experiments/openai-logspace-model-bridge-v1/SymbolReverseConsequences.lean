import SymbolReverseBridge

/-!
# Quantitative and statistical consequences of the independently checked
reverse translation from OpenAI's Boolean machine to a Boolean-symbol source.

The goal here is exact observational/resource equivalence within these two
specified operational models, not every possible textbook TM convention.
-/

namespace Metalogic.OpenAIMath.SymbolReverseConsequences

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge
open Metalogic.OpenAIMath.SymbolRunBridge
open Metalogic.OpenAIMath.SymbolResourceBridge
open Metalogic.OpenAIMath.SymbolProbabilityBridge
open Metalogic.OpenAIMath.SymbolReverseBridge

variable {q w h : ℕ}

theorem reverse_LogSpace_iff (M : Machine q w h) :
    SourceLogSpace (fromOAIMachine M) false ↔ M.LogSpace := by
  constructor
  · rintro ⟨c, hc, hs⟩
    refine ⟨c, hc, ?_⟩
    intro x coins t
    rw [← source_spaceThrough_eq_OAI M x coins t]
    exact hs x coins t
  · rintro ⟨c, hc, hs⟩
    refine ⟨c, hc, ?_⟩
    intro x coins t
    rw [source_spaceThrough_eq_OAI M x coins t]
    exact hs x coins t

theorem reverse_deterministic
    (M : Machine q w h) (hd : M.Deterministic) :
    ∀ st inp bits,
      (fromOAIMachine M).transition st inp bits false =
        (fromOAIMachine M).transition st inp bits true := by
  intro st inp bits
  exact congrArg
    (fun a : Action q w h =>
      ({ nextState := a.nextState
         write := a.write
         workMove := a.workMove
         inputMove := a.inputMove } : ExplicitAlphabetBridge.SymbolAction q w h))
    (hd st inp bits)

theorem reverse_output_eq
    (M : Machine q w h) (x : Word) (coins : CoinTape) (t : ℕ) :
    (fromOAIMachine M).output
        (sourceRun (fromOAIMachine M) false x coins t).state =
      M.output (M.run x coins t).state := by
  rw [source_run_eq_OAI]
  rfl

theorem reverse_decides_iff (M : Machine q w h) (A : Language) :
    SourceDecides (fromOAIMachine M) false A ↔ M.Decides A := by
  constructor
  · intro hs x
    obtain ⟨t, b, hb, ho⟩ := hs x
    refine ⟨t, b, hb, ?_⟩
    intro coins
    rw [← reverse_output_eq M x coins t]
    exact ho coins
  · intro hs x
    obtain ⟨t, b, hb, ho⟩ := hs x
    refine ⟨t, b, hb, ?_⟩
    intro coins
    rw [reverse_output_eq M x coins t]
    exact ho coins

theorem reverse_acceptanceProbability_eq
    (M : Machine q w h) (x : Word) (t : ℕ) :
    sourceAcceptanceProbability (fromOAIMachine M) false x t =
      M.acceptanceProbability x t := by
  have hfilter :
      (Finset.univ.filter (fun bits : Fin t → Bool =>
        (fromOAIMachine M).output
          (sourceRun (fromOAIMachine M) false x (Machine.extendCoins bits) t).state =
            some true)) =
      (Finset.univ.filter (fun bits : Fin t → Bool =>
        M.output (M.run x (Machine.extendCoins bits) t).state =
          some true)) := by
    ext bits
    simp only [Finset.mem_filter, Finset.mem_univ, true_and]
    rw [reverse_output_eq M x (Machine.extendCoins bits) t]
  unfold sourceAcceptanceProbability Machine.acceptanceProbability
  rw [hfilter]

end Metalogic.OpenAIMath.SymbolReverseConsequences
