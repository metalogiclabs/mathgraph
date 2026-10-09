import BooleanClassBridge

/-!
# Independently specified probabilistic language classes on finite-symbol
Boolean source machines, with exact-clock transport to pinned OAI RL / BPL.

This is a separate definition of machine execution, visited-site space,
halting, and probability on the source side. The finite coin-prefix measure,
input geometry, and fixed number of work heads are intentionally shared with
the pinned OpenAI formal model. No universal textbook TM adequacy is claimed.
-/

namespace Metalogic.OpenAIMath.BooleanProbabilisticClassBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolRunBridge
open Metalogic.OpenAIMath.SymbolResourceBridge
open Metalogic.OpenAIMath.SymbolProbabilityBridge
open Metalogic.OpenAIMath.SymbolReverseBridge
open Metalogic.OpenAIMath.SymbolReverseConsequences
open Metalogic.OpenAIMath.BooleanClassBridge

variable {q w h : ℕ}

/-- Halting at a fixed clock under every coin tape in the independent source
semantics; unlike SourceDecides, this does not require a fixed output bit. -/
def sourceHaltsBy (M : SymbolMachine Bool q w h) (x : Word) (t : ℕ) : Prop :=
  ∀ coins : CoinTape, ∃ b : Bool,
    M.output (sourceRun M false x coins t).state = some b

/-- Source-side analogue of the exact published one-sided probabilistic
machine-class definition, using source rather than OAI executions. -/
def BooleanSourceRL : Set Language :=
  { A | ∃ (q w h : ℕ) (M : SymbolMachine Bool q w h),
    SourceLogSpace M false ∧
    ∃ (c k : ℕ), 0 < c ∧ ∀ x : Word,
      sourceHaltsBy M x (polynomialClock c k x.length) ∧
      (x ∈ A →
        (1 / 2 : ℚ) ≤
          sourceAcceptanceProbability M false x (polynomialClock c k x.length)) ∧
      (x ∉ A →
        sourceAcceptanceProbability M false x (polynomialClock c k x.length) = 0) }

/-- Source-side analogue of the bounded-error probabilistic definition. -/
def BooleanSourceBPL : Set Language :=
  { A | ∃ (q w h : ℕ) (M : SymbolMachine Bool q w h),
    SourceLogSpace M false ∧
    ∃ (c k : ℕ), 0 < c ∧ ∀ x : Word,
      sourceHaltsBy M x (polynomialClock c k x.length) ∧
      (x ∈ A →
        (2 / 3 : ℚ) ≤
          sourceAcceptanceProbability M false x (polynomialClock c k x.length)) ∧
      (x ∉ A →
        sourceAcceptanceProbability M false x (polynomialClock c k x.length) ≤ (1 / 3 : ℚ)) }

theorem compiled_haltsBy_source (M : SymbolMachine Bool q w h)
    (x : Word) (t : ℕ) (hs : sourceHaltsBy M x t) :
    (compileMachine boolCodec M).HaltsBy x t := by
  intro coins
  obtain ⟨b, hb⟩ := hs coins
  refine ⟨b, ?_⟩
  rw [compiled_output_eq_source boolCodec M x coins t]
  exact hb

theorem reverse_haltsBy_OAI (M : Machine q w h)
    (x : Word) (t : ℕ) (hs : M.HaltsBy x t) :
    sourceHaltsBy (fromOAIMachine M) x t := by
  intro coins
  obtain ⟨b, hb⟩ := hs coins
  refine ⟨b, ?_⟩
  rw [reverse_output_eq M x coins t]
  exact hb

/-- Forward: every Boolean source RL witness gives a pinned OAI RL witness
with EXACTLY the same polynomial clock parameters, not just a slowdown. -/
theorem boolean_source_RL_subset_OAI_RL : BooleanSourceRL ⊆ RL := by
  intro A hA
  obtain ⟨q, w, h, M, hs, c, k, hc, hcases⟩ := hA
  refine ⟨q, w * 2, h, compileMachine boolCodec M,
    compiled_LogSpace_of_source boolCodec M hs, c, k, hc, ?_⟩
  intro x
  obtain ⟨hhalt, hyes, hno⟩ := hcases x
  refine ⟨compiled_haltsBy_source M x (polynomialClock c k x.length) hhalt,
    ?_, ?_⟩
  · intro hx
    rw [compiled_acceptanceProbability_eq_source boolCodec M x
      (polynomialClock c k x.length)]
    exact hyes hx
  · intro hx
    rw [compiled_acceptanceProbability_eq_source boolCodec M x
      (polynomialClock c k x.length)]
    exact hno hx

theorem OAI_RL_subset_boolean_source_RL : RL ⊆ BooleanSourceRL := by
  intro A hA
  obtain ⟨q, w, h, M, hs, c, k, hc, hcases⟩ := hA
  refine ⟨q, w, h, fromOAIMachine M, (reverse_LogSpace_iff M).mpr hs,
    c, k, hc, ?_⟩
  intro x
  obtain ⟨hhalt, hyes, hno⟩ := hcases x
  refine ⟨reverse_haltsBy_OAI M x (polynomialClock c k x.length) hhalt,
    ?_, ?_⟩
  · intro hx
    rw [reverse_acceptanceProbability_eq M x (polynomialClock c k x.length)]
    exact hyes hx
  · intro hx
    rw [reverse_acceptanceProbability_eq M x (polynomialClock c k x.length)]
    exact hno hx

/-- Complete equivalence for the independently defined source RL class,
under the shared explicitly declared probabilistic-machine conventions. -/
theorem boolean_source_RL_eq_OAI_RL : BooleanSourceRL = RL :=
  Set.Subset.antisymm boolean_source_RL_subset_OAI_RL
    OAI_RL_subset_boolean_source_RL

theorem boolean_source_BPL_subset_OAI_BPL : BooleanSourceBPL ⊆ BPL := by
  intro A hA
  obtain ⟨q, w, h, M, hs, c, k, hc, hcases⟩ := hA
  refine ⟨q, w * 2, h, compileMachine boolCodec M,
    compiled_LogSpace_of_source boolCodec M hs, c, k, hc, ?_⟩
  intro x
  obtain ⟨hhalt, hyes, hno⟩ := hcases x
  refine ⟨compiled_haltsBy_source M x (polynomialClock c k x.length) hhalt,
    ?_, ?_⟩
  · intro hx
    rw [compiled_acceptanceProbability_eq_source boolCodec M x
      (polynomialClock c k x.length)]
    exact hyes hx
  · intro hx
    rw [compiled_acceptanceProbability_eq_source boolCodec M x
      (polynomialClock c k x.length)]
    exact hno hx

theorem OAI_BPL_subset_boolean_source_BPL : BPL ⊆ BooleanSourceBPL := by
  intro A hA
  obtain ⟨q, w, h, M, hs, c, k, hc, hcases⟩ := hA
  refine ⟨q, w, h, fromOAIMachine M, (reverse_LogSpace_iff M).mpr hs,
    c, k, hc, ?_⟩
  intro x
  obtain ⟨hhalt, hyes, hno⟩ := hcases x
  refine ⟨reverse_haltsBy_OAI M x (polynomialClock c k x.length) hhalt,
    ?_, ?_⟩
  · intro hx
    rw [reverse_acceptanceProbability_eq M x (polynomialClock c k x.length)]
    exact hyes hx
  · intro hx
    rw [reverse_acceptanceProbability_eq M x (polynomialClock c k x.length)]
    exact hno hx

/-- Complete equivalence for independently defined bounded-error semantics,
with exact finite-clock coin acceptance probability preservation. -/
theorem boolean_source_BPL_eq_OAI_BPL : BooleanSourceBPL = BPL :=
  Set.Subset.antisymm boolean_source_BPL_subset_OAI_BPL
    OAI_BPL_subset_boolean_source_BPL

/-- An independently defined deterministic Boolean-source logspace decider
belongs to the independently defined source one-sided probabilistic class. -/
theorem boolean_source_L_subset_source_RL :
    BooleanSourceL ⊆ BooleanSourceRL :=
  Set.Subset.trans
    (Set.Subset.trans boolean_source_L_subset_OAI_L L_subset_RL)
    OAI_RL_subset_boolean_source_RL

theorem boolean_source_L_subset_source_BPL :
    BooleanSourceL ⊆ BooleanSourceBPL :=
  Set.Subset.trans
    (Set.Subset.trans boolean_source_L_subset_OAI_L L_subset_BPL)
    OAI_BPL_subset_boolean_source_BPL

end Metalogic.OpenAIMath.BooleanProbabilisticClassBridge
