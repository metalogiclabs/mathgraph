import FormalConjectures.ErdosProblems.«349»
import Mathlib.Tactic

/-!
Erdős 349: positive integer pair characterization with the actual one-based,
index-distinct source predicate. This is a standalone independent Lean test
against the source-patched FC module, not a proof of the open full problem.
-/

open Erdos349 Filter

/-- If a fixed integer c ≥ 2 divides every sequence term, its indexed
finite sums cannot contain every sufficiently large integer. -/
private theorem no_cofinite_multiples (c : ℤ) (hc : 2 ≤ c)
    (A : ℕ → ℤ) (hdiv : ∀ n, c ∣ A n) :
    ¬ IsAddCompleteNatSeq' A := by
  intro h
  change ∀ᶠ k : ℤ in Filter.atTop, ∃ B : Finset ℕ, k = ∑ i ∈ B, A i at h
  obtain ⟨N, hN⟩ := Filter.eventually_atTop.1 h
  let k : ℤ := c * max N 0 + 1
  have hk : N ≤ k := by
    have hmax : N ≤ max N 0 := le_max_left _ _
    have hnon : 0 ≤ max N 0 := le_max_right _ _
    have hmul : max N 0 ≤ c * max N 0 := by
      calc
        max N 0 = 1 * max N 0 := by ring
        _ ≤ c * max N 0 := mul_le_mul_of_nonneg_right (by omega) hnon
    dsimp [k]
    omega
  obtain ⟨B, hB⟩ := hN k hk
  have hkdiv : c ∣ k := by
    rw [hB]
    apply Finset.dvd_sum
    intro i hi
    exact hdiv i
  have hone : c ∣ (1 : ℤ) := by
    have hm : c ∣ c * max N 0 := ⟨max N 0, rfl⟩
    have hh := dvd_sub hkdiv hm
    simpa [k] using hh
  have hcle : c ≤ 1 := Int.le_of_dvd (by norm_num) hone
  omega

/-- For positive integer parameters, an integer base >= 2 obstructs
the one-based source sequence (all values are divisible by that base). -/
theorem source_int_base_ge_two_not (t α : ℤ) (ht : 1 ≤ t) (hα : 2 ≤ α) :
    ¬ IsGoodPairIndexed (t : ℝ) (α : ℝ) := by
  unfold IsGoodPairIndexed
  apply no_cofinite_multiples α hα
  intro n
  have hf : (⌊(t : ℝ) * (α : ℝ) ^ (n + 1)⌋ : ℤ) = t * α ^ (n + 1) := by
    have hcast : (t : ℝ) * (α : ℝ) ^ (n + 1) =
        ((t * α ^ (n + 1) : ℤ) : ℝ) := by norm_cast
    rw [hcast]
    exact (Int.floor_intCast (R := ℝ) (t * α ^ (n + 1)))
  rw [hf, pow_succ]
  refine ⟨t * α ^ n, ?_⟩
  ring

/-- An integer coefficient at least two also obstructs completeness,
including the constant-base case α = 1. -/
theorem source_int_coeff_ge_two_not (t α : ℤ) (ht : 2 ≤ t) (hα : 1 ≤ α) :
    ¬ IsGoodPairIndexed (t : ℝ) (α : ℝ) := by
  unfold IsGoodPairIndexed
  apply no_cofinite_multiples t ht
  intro n
  have hf : (⌊(t : ℝ) * (α : ℝ) ^ (n + 1)⌋ : ℤ) = t * α ^ (n + 1) := by
    have hcast : (t : ℝ) * (α : ℝ) ^ (n + 1) =
        ((t * α ^ (n + 1) : ℤ) : ℝ) := by norm_cast
    rw [hcast]
    exact (Int.floor_intCast (R := ℝ) (t * α ^ (n + 1)))
  rw [hf]
  exact ⟨α ^ (n + 1), rfl⟩

/-- Exact positive-integer slice of the source problem.
The sole good positive INTEGER pair is (1,1), not the legacy (1,2). -/
theorem source_integer_pairs_iff (t α : ℤ) (ht : 1 ≤ t) (hα : 1 ≤ α) :
    IsGoodPairIndexed (t : ℝ) (α : ℝ) ↔ t = 1 ∧ α = 1 := by
  constructor
  · intro h
    have hbase : α = 1 := by
      by_contra hn
      have hge : 2 ≤ α := by omega
      exact (source_int_base_ge_two_not t α ht hge) h
    have hcoeff : t = 1 := by
      by_contra hn
      have hge : 2 ≤ t := by omega
      exact (source_int_coeff_ge_two_not t α hge hα) h
    exact ⟨hcoeff, hbase⟩
  · rintro ⟨rfl, rfl⟩
    change ∀ᶠ k : ℤ in Filter.atTop,
      ∃ B : Finset ℕ, k = ∑ i ∈ B, (⌊(1 : ℝ) * 1 ^ (i + 1)⌋ : ℤ)
    refine Filter.eventually_atTop.2 ⟨0, ?_⟩
    intro k hk
    refine ⟨Finset.range k.toNat, ?_⟩
    have hcast : (k.toNat : ℤ) = k := by omega
    simpa using hcast.symm

#print axioms source_int_base_ge_two_not
#print axioms source_int_coeff_ge_two_not
#print axioms source_integer_pairs_iff
