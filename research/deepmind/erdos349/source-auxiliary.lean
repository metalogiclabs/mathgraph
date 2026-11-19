import FormalConjectures.ErdosProblems.«349»
import Mathlib.Tactic

/-!
MathGraph bounded review of Erdős 349 source versus Lean semantics.
The binary-expansion lemma below is adapted from the independently linked
cepadugato/formal-conjectures proof at 19e39e33 (ErdosProblems/349.lean).
This file is a test of source-fidelity and never claims the open Erdős problem is solved.
-/

open Filter Erdos349

/-- Finite binary expansions. Adapted from cepadugato's original proof. -/
theorem binary_nat (k : ℕ) :
    ∃ E : Finset ℕ, k = ∑ i ∈ E, 2 ^ i := by
  induction k using Nat.strong_induction_on with
  | _ k ih =>
    rcases Nat.eq_zero_or_pos k with hk0 | hkpos
    · exact ⟨∅, by simp [hk0]⟩
    · set m := Nat.log 2 k with hm
      have hmle : 2 ^ m ≤ k := Nat.pow_log_le_self 2 hkpos.ne'
      have hltsucc : k < 2 ^ (m + 1) := Nat.lt_pow_succ_log_self (by norm_num) k
      set r := k - 2 ^ m with hr
      have hr_lt_pow : r < 2 ^ m := by
        have : k < 2 ^ m + 2 ^ m := by
          have : (2 : ℕ) ^ (m + 1) = 2 ^ m + 2 ^ m := by ring
          omega
        omega
      have hr_lt_k : r < k := by omega
      obtain ⟨E, hE⟩ := ih r hr_lt_k
      have hElt : ∀ i ∈ E, i < m := by
        intro i hi
        by_contra hge
        rw [not_lt] at hge
        have hpow_le : 2 ^ m ≤ 2 ^ i := Nat.pow_le_pow_right (by norm_num) hge
        have hle : 2 ^ i ≤ r := by
          calc 2 ^ i = ∑ j ∈ ({i} : Finset ℕ), 2 ^ j := by simp
            _ ≤ ∑ j ∈ E, 2 ^ j := by
                apply Finset.sum_le_sum_of_subset_of_nonneg
                · simpa using hi
                · intro j _ _; positivity
            _ = r := hE.symm
        omega
      have hmnotin : m ∉ E := fun hmem => (lt_irrefl m (hElt m hmem))
      refine ⟨insert m E, ?_⟩
      rw [Finset.sum_insert hmnotin]
      omega

/-- The positive dyadic source pair is (1/2,2), not the 0-indexed legacy (1,2). -/
theorem source_half_two_complete : IsGoodPairIndexed (1 / 2) 2 := by
  change ∀ᶠ k : ℤ in Filter.atTop,
    ∃ B : Finset ℕ, k = ∑ i ∈ B, (⌊(1 / 2 : ℝ) * 2 ^ (i + 1)⌋ : ℤ)
  refine Filter.eventually_atTop.2 ⟨0, ?_⟩
  intro k hk
  obtain ⟨E, hE⟩ := binary_nat k.toNat
  refine ⟨E, ?_⟩
  have hterm (i : ℕ) : (⌊(1 / 2 : ℝ) * 2 ^ (i + 1)⌋ : ℤ) = (2 : ℤ) ^ i := by
    have heq : (1 / 2 : ℝ) * 2 ^ (i + 1) = ((2 : ℤ) ^ i : ℝ) := by
      calc
        (1 / 2 : ℝ) * 2 ^ (i + 1) = (1 / 2 : ℝ) * (2 ^ i * 2) := by rw [pow_succ]
        _ = (2 : ℝ) ^ i := by ring
        _ = ((2 : ℤ) ^ i : ℝ) := by norm_cast
    rw [heq]
    exact (Int.floor_intCast (R := ℝ) ((2 : ℤ) ^ i))
  simp_rw [hterm]
  have hcast : (∑ i ∈ E, (2 : ℤ) ^ i) = ((∑ i ∈ E, 2 ^ i : ℕ) : ℤ) := by
    push_cast
    ring
  rw [hcast, ← hE]
  omega

/-- Shifting exponent start by one is exactly compensated by t ↦ t*α.
This transport does NOT restore value multiplicity after taking a Set.range. -/
theorem source_index_shift (t α : ℝ) :
    IsGoodPairIndexed t α ↔
      IsAddCompleteNatSeq' (fun n : ℕ ↦ (⌊(t * α) * α ^ n⌋ : ℤ)) := by
  unfold IsGoodPairIndexed
  have hseq : (fun n : ℕ ↦ (⌊t * α ^ (n + 1)⌋ : ℤ)) =
              (fun n : ℕ ↦ (⌊(t * α) * α ^ n⌋ : ℤ)) := by
    funext n
    congr 1
    rw [pow_succ]
    ring
  rw [hseq]

#print axioms binary_nat
#print axioms source_half_two_complete
#print axioms source_index_shift
