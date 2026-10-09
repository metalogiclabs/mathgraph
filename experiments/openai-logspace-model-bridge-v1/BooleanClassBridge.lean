import SymbolReverseConsequences

/-!
# Exact language-class correspondence at the shared Boolean-machine boundary

This compares the independently specified symbol machine (restricted to its
Boolean work alphabet and the same input/coin/head semantics) with the exact
published OAI L class. It does NOT establish equivalence with every textbook
TM convention, alternate tape geometry, or every external notion of logspace.
-/

namespace Metalogic.OpenAIMath.BooleanClassBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolResourceBridge
open Metalogic.OpenAIMath.SymbolReverseBridge
open Metalogic.OpenAIMath.SymbolReverseConsequences

/-- A concrete finite codebook for Bool, with false represented by all zeros
and true by one set bit in a two-bit block. -/
def boolIndices : Bool ≃ Fin 2 where
  toFun := fun b => if b then 1 else 0
  invFun := fun i => decide (i.val = 1)
  left_inv := by intro b; cases b <;> decide
  right_inv := by intro i; fin_cases i <;> decide

/-- Explicit executable Boolean-alphabet compiler instance. -/
def boolCodec : AlphabetCodec Bool 2 where
  indices := boolIndices
  blank := false
  decode := fun bits => bits ⟨1, by decide⟩
  decode_roundtrip := by
    intro a
    cases a <;> decide

/-- This is a distinct quantified class: an independently authored Boolean-
symbol machine with its own operational sourceRun, sourceSpaceThrough and
SourceDecides definitions. -/
def BooleanSourceL : Set Language :=
  { A | ∃ (q w h : ℕ) (M : SymbolMachine Bool q w h),
      (∀ st inp bits, M.transition st inp bits false =
        M.transition st inp bits true) ∧
      SourceLogSpace M false ∧ SourceDecides M false A }

/-- Every independent Boolean-source LogSpace decider compiles to OAI L
with exactly two Boolean tracks per source work tape. -/
theorem boolean_source_L_subset_OAI_L : BooleanSourceL ⊆ L := by
  intro A hA
  obtain ⟨q, w, h, M, hdet, hspace, hdec⟩ := hA
  exact ⟨q, w * 2, h, compileMachine boolCodec M,
    compiled_deterministic_of_source boolCodec M hdet,
    compiled_LogSpace_of_source boolCodec M hspace,
    compiled_decides_of_source boolCodec M A hdec⟩

/-- Every pinned OAI Boolean LogSpace decider is a separately specified
Boolean-symbol machine with exactly the same runs, visited-space measure and
decision outcomes (as qualified in the reverse bridge). -/
theorem OAI_L_subset_boolean_source_L : L ⊆ BooleanSourceL := by
  intro A hA
  obtain ⟨q, w, h, M, hdet, hspace, hdec⟩ := hA
  exact ⟨q, w, h, fromOAIMachine M,
    reverse_deterministic M hdet,
    (reverse_LogSpace_iff M).mpr hspace,
    (reverse_decides_iff M A).mpr hdec⟩

/-- Exact class equivalence ONLY at the declared shared Boolean operational
interface. This theorem does not redefine or independently validate OAI's
underlying external complexity-class interpretation. -/
theorem boolean_source_L_eq_OAI_L : BooleanSourceL = L :=
  Set.Subset.antisymm boolean_source_L_subset_OAI_L OAI_L_subset_boolean_source_L

end Metalogic.OpenAIMath.BooleanClassBridge
