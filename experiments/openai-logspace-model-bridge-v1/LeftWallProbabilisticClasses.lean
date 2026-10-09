import LeftWallComplete

/-!
# One-sided, single-tape, Nat-indexed source probabilistic classes

This is a genuinely different work-tape geometry from the pinned OAI
bi-infinite, multihead target. Input-head geometry, finite coin distribution
and Boolean work alphabet are intentionally shared. We prove forward class
inclusions only; reverse textbook-machine equivalence remains UNKNOWN.
-/

namespace Metalogic.OpenAIMath.LeftWallProbabilisticClasses

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler
open Metalogic.OpenAIMath.LeftWallFusedCompiler
open Metalogic.OpenAIMath.LeftWallComplete
open Metalogic.OpenAIMath.LeftWallBootstrapInduction

variable {q h : ℕ}

/-- Source halting under all coin tapes at the given physical clock. -/
def LeftHaltsBy (M : LeftMachine q h) (x : Word) (t : ℕ) : Prop :=
  ∀ coins : CoinTape, ∃ b : Bool,
    M.output (LeftBoundedMachine.run M x coins t).state = some b

/-- Source RL under its own Nat-indexed left-bounded work-tape semantics. -/
def LeftRL : Set Language :=
  { A | ∃ (q h : ℕ) (M : LeftMachine q h),
    LeftLogSpace M ∧ ∃ (c k : ℕ), 0 < c ∧ ∀ x : Word,
      LeftHaltsBy M x (polynomialClock c k x.length) ∧
      (x ∈ A → (1 / 2 : ℚ) ≤
        leftAcceptanceProbability M x (polynomialClock c k x.length)) ∧
      (x ∉ A →
        leftAcceptanceProbability M x (polynomialClock c k x.length) = 0) }

/-- Source BPL with the same protected rational thresholds as pinned OAI. -/
def LeftBPL : Set Language :=
  { A | ∃ (q h : ℕ) (M : LeftMachine q h),
    LeftLogSpace M ∧ ∃ (c k : ℕ), 0 < c ∧ ∀ x : Word,
      LeftHaltsBy M x (polynomialClock c k x.length) ∧
      (x ∈ A → (2 / 3 : ℚ) ≤
        leftAcceptanceProbability M x (polynomialClock c k x.length)) ∧
      (x ∉ A →
        leftAcceptanceProbability M x (polynomialClock c k x.length) ≤ (1 / 3 : ℚ)) }

/-- Source halting at any positive clock transports without delay or
extra random bits to the actual fused OAI compiler. -/
theorem compiled_haltsBy_positive (M : LeftMachine q h)
    (x : Word) (t : ℕ)
    (hs : LeftHaltsBy M x (t + 1)) :
    (compileFused M).HaltsBy x (t + 1) := by
  intro coins
  obtain ⟨b, hb⟩ := hs coins
  refine ⟨b, ?_⟩
  rw [LeftWallFullRun.positive_clock_output_commutes M x coins t]
  exact hb

/-- All OAI polynomial clocks with positive coefficient are positive, so
the one exceptional zero-time startup state cannot affect RL/BPL semantics. -/
theorem polynomialClock_pos (c k n : ℕ) (hc : 0 < c) :
    0 < polynomialClock c k n := by
  unfold polynomialClock
  exact Nat.mul_pos hc (pow_pos (by omega) k)

/-- Every one-sided single-work-tape RL witness has a pinned OAI RL
witness with exactly the same polynomial clock and coin-prefix measure. -/
theorem left_RL_subset_OAI_RL : LeftRL ⊆ RL := by
  intro A hA
  obtain ⟨q, h, M, hs, c, k, hc, hcases⟩ := hA
  refine ⟨q + 1, 2, h, compileFused M,
    compiled_LogSpace_of_left M hs, c, k, hc, ?_⟩
  intro x
  obtain ⟨hhalt, hyes, hno⟩ := hcases x
  let clock := polynomialClock c k x.length
  have hpos : 0 < clock := polynomialClock_pos c k x.length hc
  have ht : clock - 1 + 1 = clock := by omega
  have hhaltTarget : (compileFused M).HaltsBy x clock := by
    have h := compiled_haltsBy_positive M x (clock - 1)
      (by simpa only [ht] using hhalt)
    simpa only [ht] using h
  have hprob :
      (compileFused M).acceptanceProbability x clock =
        leftAcceptanceProbability M x clock := by
    simpa only [ht] using
      (exact_positive_clock_probability M x (clock - 1))
  refine ⟨hhaltTarget, ?_, ?_⟩
  · intro hx
    rw [hprob]
    exact hyes hx
  · intro hx
    rw [hprob]
    exact hno hx

/-- Every one-sided single-work-tape bounded-error witness transfers to
pinned OAI BPL with no polynomial clock or probability distortion. -/
theorem left_BPL_subset_OAI_BPL : LeftBPL ⊆ BPL := by
  intro A hA
  obtain ⟨q, h, M, hs, c, k, hc, hcases⟩ := hA
  refine ⟨q + 1, 2, h, compileFused M,
    compiled_LogSpace_of_left M hs, c, k, hc, ?_⟩
  intro x
  obtain ⟨hhalt, hyes, hno⟩ := hcases x
  let clock := polynomialClock c k x.length
  have hpos : 0 < clock := polynomialClock_pos c k x.length hc
  have ht : clock - 1 + 1 = clock := by omega
  have hhaltTarget : (compileFused M).HaltsBy x clock := by
    have h := compiled_haltsBy_positive M x (clock - 1)
      (by simpa only [ht] using hhalt)
    simpa only [ht] using h
  have hprob :
      (compileFused M).acceptanceProbability x clock =
        leftAcceptanceProbability M x clock := by
    simpa only [ht] using
      (exact_positive_clock_probability M x (clock - 1))
  refine ⟨hhaltTarget, ?_, ?_⟩
  · intro hx
    rw [hprob]
    exact hyes hx
  · intro hx
    rw [hprob]
    exact hno hx

end Metalogic.OpenAIMath.LeftWallProbabilisticClasses
