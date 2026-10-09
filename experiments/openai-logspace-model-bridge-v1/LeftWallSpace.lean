import LeftWallFusedCompiler

/-!
# Exact quantitative space transfer for a left-bounded source and its
two-track OAI target

The theorem deliberately takes the observable all-time work-head equality
as a hypothesis. That hypothesis will be discharged by the separate
first-step and active-step simulation gates. This module independently
certifies that no additional space overhead is hidden in the cardinality
calculation.
-/

namespace Metalogic.OpenAIMath.LeftWallSpace

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallFusedCompiler

variable {q h : ℕ}

/-- Casting visited Nat positions into Int preserves the cardinality of
the set of distinct visited coordinates. -/
theorem nat_cast_visited_card (f : ℕ → ℕ) (t : ℕ) :
    ((Finset.range (t + 1)).image (fun u => (f u : ℤ))).card =
      ((Finset.range (t + 1)).image f).card := by
  classical
  have hinj : Function.Injective (fun n : ℕ => (n : ℤ)) := by
    intro a b hab
    exact Int.ofNat.inj hab
  calc
    ((Finset.range (t + 1)).image (fun u => (f u : ℤ))).card =
        (((Finset.range (t + 1)).image f).image
          (fun n : ℕ => (n : ℤ))).card := by
          simp only [Finset.image_image]
          rfl
    _ = ((Finset.range (t + 1)).image f).card :=
          Finset.card_image_of_injective _ hinj

/-- Exactly twice the source's distinct visited sites are counted by the
two synchronized Boolean OAI heads; this has no halting or runtime premises. -/
theorem compiled_space_eq_two_of_head_simulation
    (M : LeftMachine q h) (x : Word) (coins : CoinTape) (t : ℕ)
    (hheads : ∀ (u : ℕ) (j : Fin 2),
       ((compileFused M).run x coins u).workPos j =
        ((LeftBoundedMachine.run M x coins u).workPos : ℤ)) :
    (compileFused M).spaceThrough x coins t =
      2 * LeftBoundedMachine.spaceThrough M x coins t := by
  classical
  let f : ℕ → ℕ := fun u => (LeftBoundedMachine.run M x coins u).workPos
  let count : ℕ := ((Finset.range (t + 1)).image f).card
  have htrack (j : Fin 2) :
      ((Finset.range (t + 1)).image
        (fun u => ((compileFused M).run x coins u).workPos j)).card = count := by
    have hf :
        (fun u : ℕ => ((compileFused M).run x coins u).workPos j) =
        (fun u : ℕ => (f u : ℤ)) := by
      funext u
      exact hheads u j
    rw [hf]
    exact nat_cast_visited_card f t
  change (∑ j : Fin 2,
      ((Finset.range (t + 1)).image
        (fun u => ((compileFused M).run x coins u).workPos j)).card) =
      2 * count
  rw [Fin.sum_univ_two, htrack 0, htrack 1]
  omega

end Metalogic.OpenAIMath.LeftWallSpace
