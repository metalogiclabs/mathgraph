import ChallengeDeps

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- Recursive adjacent sign-change counter on an already zero-free list. -/
noncomputable def pairChanges : List ℝ → ℕ
  | [] => 0
  | [_] => 0
  | a :: b :: xs => (if a * b < 0 then 1 else 0) + pairChanges (b :: xs)

/-- The recursive counter is the benchmark's zip/filter adjacent-pair count. -/
theorem pairChanges_eq_zip_filter_length (xs : List ℝ) :
    pairChanges xs = ((xs.zip xs.tail).filter (fun q => q.1 * q.2 < 0)).length := by
  induction xs with
  | nil => simp [pairChanges]
  | cons a xs ih =>
      cases xs with
      | nil => simp [pairChanges]
      | cons b xs =>
          by_cases h : a * b < 0 <;>
            simp [pairChanges, h, ih, Nat.add_comm]

/-- `signChanges` is `pairChanges` after quotienting away zero entries. -/
theorem signChanges_eq_pairChanges_filter (xs : List ℝ) :
    signChanges xs = pairChanges (xs.filter (· ≠ 0)) := by
  simp only [signChanges]
  exact (pairChanges_eq_zip_filter_length (xs.filter (· ≠ 0))).symm

/-- If the endpoints are opposite, a nonzero middle state can be erased from
an adjacent three-entry block without changing its contribution. -/
theorem pairChanges_three_elim_of_opposite_ends
    (a b c : ℝ) (ys : List ℝ) (hb : b ≠ 0) (hac : a * c < 0) :
    pairChanges (a :: b :: c :: ys) = pairChanges (a :: c :: ys) := by
  rcases (mul_neg_iff.mp hac) with h | h
  · rcases h with ⟨ha, hc⟩
    rcases lt_or_gt_of_ne hb with hbneg | hbpos
    · have hab : a * b < 0 := mul_neg_of_pos_of_neg ha hbneg
      have hbc : ¬ b * c < 0 := by
        have : 0 < b * c := mul_pos_of_neg_of_neg hbneg hc
        linarith
      simp [pairChanges, hac, hab, hbc, Nat.add_comm]
    · have hab : ¬ a * b < 0 := by
        have : 0 < a * b := mul_pos ha hbpos
        linarith
      have hbc : b * c < 0 := mul_neg_of_pos_of_neg hbpos hc
      simp [pairChanges, hac, hab, hbc, Nat.add_comm]
  · rcases h with ⟨ha, hc⟩
    rcases lt_or_gt_of_ne hb with hbneg | hbpos
    · have hab : ¬ a * b < 0 := by
        have : 0 < a * b := mul_pos_of_neg_of_neg ha hbneg
        linarith
      have hbc : b * c < 0 := mul_neg_of_neg_of_pos hbneg hc
      simp [pairChanges, hac, hab, hbc, Nat.add_comm]
    · have hab : a * b < 0 := mul_neg_of_neg_of_pos ha hbpos
      have hbc : ¬ b * c < 0 := by
        have : 0 < b * c := mul_pos hbpos hc
        linarith
      simp [pairChanges, hac, hab, hbc, Nat.add_comm]

/-- Arbitrary-prefix context lift of the three-entry elimination law. -/
theorem pairChanges_context_three_elim_of_opposite_ends
    (xs ys : List ℝ) (a b c : ℝ) (hb : b ≠ 0) (hac : a * c < 0) :
    pairChanges (xs ++ a :: b :: c :: ys) =
      pairChanges (xs ++ a :: c :: ys) := by
  induction xs with
  | nil =>
      simpa using pairChanges_three_elim_of_opposite_ends a b c ys hb hac
  | cons x xs ih =>
      cases xs with
      | nil =>
          change
            (if x * a < 0 then 1 else 0) + pairChanges (a :: b :: c :: ys) =
            (if x * a < 0 then 1 else 0) + pairChanges (a :: c :: ys)
          rw [pairChanges_three_elim_of_opposite_ends a b c ys hb hac]
      | cons y zs =>
          change
            (if x * y < 0 then 1 else 0) +
                pairChanges ((y :: zs) ++ a :: b :: c :: ys) =
            (if x * y < 0 then 1 else 0) +
                pairChanges ((y :: zs) ++ a :: c :: ys)
          rw [ih]

/-- Full behavioural quotient in arbitrary list context, including the zero
middle case handled by the benchmark's zero-filtering semantics. -/
theorem signChanges_context_three_elim_of_opposite_ends
    (xs ys : List ℝ) (a b c : ℝ) (hac : a * c < 0) :
    signChanges (xs ++ [a, b, c] ++ ys) =
      signChanges (xs ++ [a, c] ++ ys) := by
  have ha : a ≠ 0 := by
    intro h
    simp [h] at hac
  have hc : c ≠ 0 := by
    intro h
    simp [h] at hac
  by_cases hb : b = 0
  · subst b
    simp [signChanges, List.filter_append, ha, hc]
  · rw [signChanges_eq_pairChanges_filter, signChanges_eq_pairChanges_filter]
    simpa [List.filter_append, ha, hb, hc] using
      pairChanges_context_three_elim_of_opposite_ends
        (xs.filter (· ≠ 0)) (ys.filter (· ≠ 0)) a b c hb hac

/-- Continuous arbitrary-context lift for polynomial evaluation. -/
theorem polynomial_context_triple_elim_locally
    (xs ys : List ℝ[X]) (a b c : ℝ[X]) (r : ℝ)
    (hac : a.eval r * c.eval r < 0) :
    ∀ᶠ x in 𝓝 r,
      signChanges ((xs ++ [a, b, c] ++ ys).map (fun q => q.eval x)) =
      signChanges ((xs ++ [a, c] ++ ys).map (fun q => q.eval x)) := by
  let f : ℝ → ℝ := fun x => a.eval x * c.eval x
  have hf : ContinuousAt f r := a.continuousAt.mul c.continuousAt
  have hmem : Set.Iio (0 : ℝ) ∈ 𝓝 (f r) := by
    exact IsOpen.mem_nhds isOpen_Iio (by simpa [f] using hac)
  have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
    change f ⁻¹' Set.Iio 0 ∈ 𝓝 r
    exact hf hmem
  filter_upwards [hev] with x hx
  simpa [List.map_append] using
    signChanges_context_three_elim_of_opposite_ends
      (xs.map (fun q => q.eval x)) (ys.map (fun q => q.eval x))
      (a.eval x) (b.eval x) (c.eval x) (by simpa [f] using hx)
