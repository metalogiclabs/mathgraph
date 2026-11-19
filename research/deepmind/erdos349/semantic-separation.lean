import FormalConjectures.ErdosProblems.«349»
import Mathlib.Tactic

/-! Kernel-checked semantic separation for the literal one-based, indexed sequence. -/
open Filter Erdos349

theorem constant_one_source_complete : IsGoodPairIndexed 1 1 := by
  change ∀ᶠ k : ℤ in Filter.atTop,
    ∃ B : Finset ℕ, k = ∑ i ∈ B, (⌊(1 : ℝ) * 1 ^ (i + 1)⌋ : ℤ)
  refine Filter.eventually_atTop.2 ⟨0, ?_⟩
  intro k hk
  refine ⟨Finset.range k.toNat, ?_⟩
  have hcast : (k.toNat : ℤ) = k := by omega
  simpa using hcast.symm

theorem two_source_not_complete : ¬ IsGoodPairIndexed 1 2 := by
  intro h
  change ∀ᶠ k : ℤ in Filter.atTop,
    ∃ B : Finset ℕ, k = ∑ i ∈ B, (⌊(1 : ℝ) * 2 ^ (i + 1)⌋ : ℤ) at h
  obtain ⟨m, hm⟩ := Filter.eventually_atTop.1 h
  let k : ℤ := 2 * max m 0 + 1
  have hmk : m ≤ k := by dsimp [k]; omega
  obtain ⟨B, hB⟩ := hm k hmk
  have hterm (i : ℕ) : (2 : ℤ) ∣ (⌊(1 : ℝ) * 2 ^ (i + 1)⌋ : ℤ) := by
    have hi : (⌊(1 : ℝ) * 2 ^ (i + 1)⌋ : ℤ) = (2 : ℤ) ^ (i + 1) := by
      have hpow : (2 : ℝ) ^ (i + 1) = ((2 : ℤ) ^ (i + 1) : ℝ) := by
        norm_cast
      rw [one_mul, hpow]
      simpa only [Int.cast_pow] using (Int.floor_intCast (R := ℝ) ((2 : ℤ) ^ (i + 1)))
    rw [hi, pow_succ]
    refine ⟨(2 : ℤ) ^ i, ?_⟩
    simp [mul_comm]
  have hsum : (2 : ℤ) ∣ ∑ i ∈ B, (⌊(1 : ℝ) * 2 ^ (i + 1)⌋ : ℤ) := by
    apply Finset.dvd_sum
    intro i hi
    exact hterm i
  have hkdiv : (2 : ℤ) ∣ k := by rw [hB]; exact hsum
  have hnot : ¬ (2 : ℤ) ∣ k := by dsimp [k]; omega
  exact hnot hkdiv

#print axioms constant_one_source_complete
#print axioms two_source_not_complete
