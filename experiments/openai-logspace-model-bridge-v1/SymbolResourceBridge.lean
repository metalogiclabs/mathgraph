import SymbolFullRunBridge

/-! Exact resource accounting for the independently specified finite-alphabet
machine compiled to OpenAI's pinned Boolean-track machine. -/

namespace Metalogic.OpenAIMath.SymbolResourceBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge
open Metalogic.OpenAIMath.SymbolRunBridge
open Metalogic.OpenAIMath.SymbolFullRunBridge

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

/-- The source space measure counts all distinct visited work-head positions,
for each finite-symbol source tape, exactly as the pinned OAI measure does. -/
def sourceSpaceThrough (M : SymbolMachine α q w h) (blank : α)
    (x : Word) (coins : CoinTape) (t : ℕ) : ℕ :=
  ∑ k : Fin w, ((Finset.range (t + 1)).image
    (fun u => (sourceRun M blank x coins u).workPos k)).card

/-- Every source work-head position is copied into every Boolean bit track
at every time, by the previously checked complete-run simulation. -/
theorem compiled_workhead_eq_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (coins : CoinTape) (t : ℕ) (j : Fin (w * K)) :
    ((compileMachine codec M).run x coins t).workPos j =
      (sourceRun M codec.blank x coins t).workPos
        ((finProdFinEquiv (m := w) (n := K)).symm j).1 := by
  rw [← compiled_run_commutes codec M x coins t]
  rfl

/-- No overcounting is hidden by the simulation: each original head's visited
position set is duplicated exactly K times, so the space measure scales by K. -/
theorem compiled_spaceThrough_eq
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (coins : CoinTape) (t : ℕ) :
    (compileMachine codec M).spaceThrough x coins t =
      K * sourceSpaceThrough M codec.blank x coins t := by
  classical
  let e := finProdFinEquiv (m := w) (n := K)
  let f : Fin w → ℕ := fun k =>
    ((Finset.range (t + 1)).image
      (fun u => (sourceRun M codec.blank x coins u).workPos k)).card
  have hj (j : Fin (w * K)) :
      ((Finset.range (t + 1)).image
        (fun u => ((compileMachine codec M).run x coins u).workPos j)).card =
        f (e.symm j).1 := by
    have hfun :
        (fun u : ℕ => ((compileMachine codec M).run x coins u).workPos j) =
        (fun u : ℕ => (sourceRun M codec.blank x coins u).workPos (e.symm j).1) := by
      funext u
      exact compiled_workhead_eq_source codec M x coins u j
    simp only [f, hfun]
  calc
    (compileMachine codec M).spaceThrough x coins t =
        ∑ j : Fin (w * K), f (e.symm j).1 := by
          unfold Machine.spaceThrough
          exact Finset.sum_congr rfl (fun j _ => hj j)
    _ = ∑ p : Fin w × Fin K, f p.1 := by
          exact (Equiv.sum_comp e.symm (fun p : Fin w × Fin K => f p.1)).symm
    _ = ∑ k : Fin w, ∑ i : Fin K, f k := by
          rw [Fintype.sum_prod_type]
    _ = ∑ k : Fin w, K * f k := by
          simp [Finset.sum_const, nsmul_eq_mul]
    _ = K * (∑ k : Fin w, f k) := by
          rw [Finset.mul_sum]
    _ = K * sourceSpaceThrough M codec.blank x coins t := rfl

/-- A source logarithmic-space bound is sufficient for the compiled OAI machine.
No textbook-machine equivalence is assumed. -/
def SourceLogSpace (M : SymbolMachine α q w h) (blank : α) : Prop :=
  ∃ c : ℕ, 0 < c ∧ ∀ (x : Word) (coins : CoinTape) (t : ℕ),
    sourceSpaceThrough M blank x coins t ≤ c * Nat.clog 2 (x.length + 2)

theorem compiled_LogSpace_of_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (hs : SourceLogSpace M codec.blank) :
    (compileMachine codec M).LogSpace := by
  obtain ⟨c, hc, hbound⟩ := hs
  refine ⟨K * c + 1, by omega, ?_⟩
  intro x coins t
  calc
    (compileMachine codec M).spaceThrough x coins t =
        K * sourceSpaceThrough M codec.blank x coins t :=
          compiled_spaceThrough_eq codec M x coins t
    _ ≤ K * (c * Nat.clog 2 (x.length + 2)) :=
          Nat.mul_le_mul_left K (hbound x coins t)
    _ = (K * c) * Nat.clog 2 (x.length + 2) := by ring
    _ ≤ (K * c + 1) * Nat.clog 2 (x.length + 2) :=
          Nat.mul_le_mul_right _ (Nat.le_succ (K * c))

theorem compiled_deterministic_of_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (hdet : ∀ st inp bits,
      M.transition st inp bits false = M.transition st inp bits true) :
    (compileMachine codec M).Deterministic := by
  intro st inp bits
  change lowerAction codec.indices codec.blank
      (M.transition st inp (decodeTrackReads codec bits) false) =
    lowerAction codec.indices codec.blank
      (M.transition st inp (decodeTrackReads codec bits) true)
  exact congrArg (lowerAction codec.indices codec.blank)
    (hdet st inp (decodeTrackReads codec bits))

theorem compiled_output_eq_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (coins : CoinTape) (t : ℕ) :
    (compileMachine codec M).output
        ((compileMachine codec M).run x coins t).state =
      M.output (sourceRun M codec.blank x coins t).state := by
  rw [← compiled_run_commutes codec M x coins t]
  rfl

/-- Source acceptance is defined directly on the separately authored
finite-symbol operational semantics. -/
def SourceDecides (M : SymbolMachine α q w h) (blank : α)
    (A : Language) : Prop :=
  ∀ x : Word, ∃ (t : ℕ) (b : Bool),
    (b = true ↔ x ∈ A) ∧ ∀ coins : CoinTape,
      M.output (sourceRun M blank x coins t).state = some b

theorem compiled_decides_of_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (A : Language) (hs : SourceDecides M codec.blank A) :
    (compileMachine codec M).Decides A := by
  intro x
  obtain ⟨t, b, hb, ho⟩ := hs x
  refine ⟨t, b, hb, ?_⟩
  intro coins
  rw [compiled_output_eq_source codec M x coins t]
  exact ho coins

end Metalogic.OpenAIMath.SymbolResourceBridge
