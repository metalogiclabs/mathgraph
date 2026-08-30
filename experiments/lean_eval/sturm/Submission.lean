import ChallengeDeps

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- Local Sturm invariant: at a zero of the middle polynomial, the next
negated remainder evaluates to the negative of the preceding polynomial. -/
theorem sturm_remainder_eval_at_root (a b : ℝ[X]) (x : ℝ)
    (hb : b.eval x = 0) :
    (-(a % b)).eval x = -a.eval x := by
  have h := congrArg (fun q : ℝ[X] => q.eval x) (EuclideanDomain.mod_add_div a b)
  have hrem : (a % b).eval x = a.eval x := by
    simpa [hb] using h
  simp [hrem]

/-- VDN separator probe: zeros carry no sign information, so the local
three-term Sturm configuration quotients to its two neighbours. -/
theorem signChanges_middle_zero (a c : ℝ) :
    signChanges [a, 0, c] = signChanges [a, c] := by
  by_cases ha : a = 0 <;> by_cases hc : c = 0 <;> simp [signChanges, ha, hc]

/-- Finite sign law for the interior-zero Sturm configuration. Once the
neighbours are known to be opposites, their local contribution is exactly one. -/
theorem signChanges_opposite_neighbours (a : ℝ) (ha : a ≠ 0) :
    signChanges [a, 0, -a] = 1 := by
  have hpos : 0 < a * a := mul_self_pos.mpr ha
  have hneg : a * (-a) < 0 := by
    nlinarith
  simp [signChanges, ha, hneg]

/-- Context-composition separator: inserting a zero anywhere in a list does
not change sign variation. This lifts the zero quotient through arbitrary
Sturm-chain context without introducing a new sign state. -/
theorem signChanges_insert_zero (xs ys : List ℝ) :
    signChanges (xs ++ 0 :: ys) = signChanges (xs ++ ys) := by
  have hfilter :
      (xs ++ 0 :: ys).filter (· ≠ 0) = (xs ++ ys).filter (· ≠ 0) := by
    simp [List.filter_append]
  simp only [signChanges]
  rw [hfilter]

/-- Simple-root crossing separator for the leading Sturm pair. If the value
on the left has sign opposite to the derivative and the value on the right
has the same sign, the first pair loses exactly one sign variation. -/
theorem signChanges_simple_crossing (left right deriv : ℝ)
    (hleft : left * deriv < 0) (hright : 0 < right * deriv) :
    signChanges [left, deriv] = signChanges [right, deriv] + 1 := by
  have hl0 : left ≠ 0 := by
    intro h
    simp [h] at hleft
  have hd0 : deriv ≠ 0 := by
    intro h
    simp [h] at hleft
  have hr0 : right ≠ 0 := by
    intro h
    simp [h] at hright
  have hnright : ¬ right * deriv < 0 := by
    linarith
  simp [signChanges, hl0, hd0, hr0, hleft, hnright]

/-- Analytic separator for a simple polynomial root. The difference quotient,
continuously filled at the root by the derivative, has positive product with
the derivative throughout a neighbourhood of the root. -/
theorem simple_root_local_quotient_positive (p : ℝ[X]) (r : ℝ)
    (hd : p.derivative.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      0 < (Function.update
        (fun x => (p.eval x - p.eval r) / (x - r))
        r (p.derivative.eval r) x) * p.derivative.eval r := by
  let q : ℝ → ℝ := Function.update
    (fun x => (p.eval x - p.eval r) / (x - r))
    r (p.derivative.eval r)
  have hq : ContinuousAt q r := by
    dsimp [q]
    exact (p.hasDerivAt r).continuousAt_div
  have hprod : ContinuousAt (fun x => q x * p.derivative.eval r) r :=
    hq.mul continuousAt_const
  have hpos : 0 < p.derivative.eval r * p.derivative.eval r := mul_self_pos.mpr hd
  have hnhds : Set.Ioi (0 : ℝ) ∈ 𝓝 ((fun x => q x * p.derivative.eval r) r) := by
    simpa [q] using (IsOpen.mem_nhds isOpen_Ioi hpos)
  change
    (fun x =>
      Function.update
        (fun x => (p.eval x - p.eval r) / (x - r))
        r (p.derivative.eval r) x * p.derivative.eval r) ⁻¹' Set.Ioi 0 ∈ 𝓝 r
  simpa [q] using hprod hnhds

/-- Local sign law at a simple root. In one neighbourhood of the root, on
the left the polynomial has sign opposite to its derivative at the root, and
immediately to the right it has the same sign. -/
theorem simple_root_local_crossing_sign (p : ℝ[X]) (r : ℝ)
    (hr : p.eval r = 0) (hd : p.derivative.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      ((x < r → p.eval x * p.derivative.eval r < 0) ∧
       (r < x → 0 < p.eval x * p.derivative.eval r)) := by
  filter_upwards [simple_root_local_quotient_positive p r hd] with x hx
  constructor
  · intro hxr
    have hne : x ≠ r := ne_of_lt hxr
    have hden : x - r ≠ 0 := sub_ne_zero.mpr hne
    have hq : 0 < (p.eval x / (x - r)) * p.derivative.eval r := by
      simpa [hne, hr] using hx
    have heq :
        p.eval x * p.derivative.eval r =
          ((p.eval x / (x - r)) * p.derivative.eval r) * (x - r) := by
      field_simp [hden]
    rw [heq]
    exact mul_neg_of_pos_of_neg hq (sub_neg.mpr hxr)
  · intro hrx
    have hne : x ≠ r := ne_of_gt hrx
    have hden : x - r ≠ 0 := sub_ne_zero.mpr hne
    have hq : 0 < (p.eval x / (x - r)) * p.derivative.eval r := by
      simpa [hne, hr] using hx
    have heq :
        p.eval x * p.derivative.eval r =
          ((p.eval x / (x - r)) * p.derivative.eval r) * (x - r) := by
      field_simp [hden]
    rw [heq]
    exact mul_pos hq (sub_pos.mpr hrx)

/-- Composed local Sturm crossing law. There is one common neighbourhood of a
simple root in which every left/right pair witnesses exactly one lost sign
variation in the leading polynomial/derivative pair. -/
theorem simple_root_local_variation_drop (p : ℝ[X]) (r : ℝ)
    (hr : p.eval r = 0) (hd : p.derivative.eval r ≠ 0) :
    ∃ U : Set ℝ, U ∈ 𝓝 r ∧
      ∀ x ∈ U, ∀ y ∈ U, x < r → r < y →
        signChanges [p.eval x, p.derivative.eval r] =
          signChanges [p.eval y, p.derivative.eval r] + 1 := by
  let U : Set ℝ := {x |
    (x < r → p.eval x * p.derivative.eval r < 0) ∧
    (r < x → 0 < p.eval x * p.derivative.eval r)}
  have hU : U ∈ 𝓝 r := by
    change {x : ℝ |
      (x < r → p.eval x * p.derivative.eval r < 0) ∧
      (r < x → 0 < p.eval x * p.derivative.eval r)} ∈ 𝓝 r
    exact simple_root_local_crossing_sign p r hr hd
  refine ⟨U, hU, ?_⟩
  intro x hx y hy hxr hry
  have hxsign : p.eval x * p.derivative.eval r < 0 := hx.1 hxr
  have hysign : 0 < p.eval y * p.derivative.eval r := hy.2 hry
  exact signChanges_simple_crossing _ _ _ hxsign hysign

/-- MSI bridge from the benchmark's global squarefree hypothesis to the local
simple-root capability used by the crossing package. -/
theorem squarefree_root_derivative_ne_zero (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) (hr : p.eval r = 0) :
    p.derivative.eval r ≠ 0 := by
  have hsep : p.Separable := (PerfectField.separable_iff_squarefree).2 hp
  exact hsep.eval₂_derivative_ne_zero (RingHom.id ℝ) hr

/-- MSI tail separator: once two adjacent chain entries are both nonzero at a
reference point, the only bit observed by `signChanges` for that pair — whether
their product is negative — is locally constant. -/
theorem polynomial_pair_negativity_locally_constant
    (a b : ℝ[X]) (r : ℝ) (ha : a.eval r ≠ 0) (hb : b.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      (a.eval x * b.eval x < 0 ↔ a.eval r * b.eval r < 0) := by
  let f : ℝ → ℝ := fun x => a.eval x * b.eval x
  have hf : ContinuousAt f r := a.continuousAt.mul b.continuousAt
  have hfr : f r ≠ 0 := by
    simpa [f] using mul_ne_zero ha hb
  rcases lt_or_gt_of_ne hfr with hneg | hpos
  · have hmem : Set.Iio (0 : ℝ) ∈ 𝓝 (f r) :=
      IsOpen.mem_nhds isOpen_Iio hneg
    have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
      change f ⁻¹' Set.Iio 0 ∈ 𝓝 r
      exact hf hmem
    filter_upwards [hev] with x hx
    simpa [f, hneg] using hx
  · have hmem : Set.Ioi (0 : ℝ) ∈ 𝓝 (f r) :=
      IsOpen.mem_nhds isOpen_Ioi hpos
    have hev : ∀ᶠ x in 𝓝 r, 0 < f x := by
      change f ⁻¹' Set.Ioi 0 ∈ 𝓝 r
      exact hf hmem
    filter_upwards [hev] with x hx
    have hnx : ¬ f x < 0 := not_lt.mpr (le_of_lt hx)
    have hnr : ¬ f r < 0 := not_lt.mpr (le_of_lt hpos)
    simpa [f, hnx, hnr]

/-- MSI quotient for a three-entry sign window: if the endpoint signs are
opposite, the middle value is behaviourally irrelevant to `signChanges`.
Every possible middle value yields exactly one variation. -/
theorem signChanges_three_of_opposite_ends (a b c : ℝ)
    (hac : a * c < 0) :
    signChanges [a, b, c] = 1 := by
  rcases (mul_neg_iff.mp hac) with h | h
  · rcases h with ⟨ha, hc⟩
    have hane : a ≠ 0 := ne_of_gt ha
    have hcne : c ≠ 0 := ne_of_lt hc
    by_cases hb0 : b = 0
    · subst b
      simp [signChanges, hane, hcne, hac]
    · rcases lt_or_gt_of_ne hb0 with hbneg | hbpos
      · have hab : a * b < 0 := mul_neg_of_pos_of_neg ha hbneg
        have hbc : ¬ b * c < 0 := by
          have : 0 < b * c := mul_pos_of_neg_of_neg hbneg hc
          linarith
        simp [signChanges, hane, hb0, hcne, hab, hbc]
      · have hab : ¬ a * b < 0 := by
          have : 0 < a * b := mul_pos ha hbpos
          linarith
        have hbc : b * c < 0 := mul_neg_of_pos_of_neg hbpos hc
        simp [signChanges, hane, hb0, hcne, hab, hbc]
  · rcases h with ⟨ha, hc⟩
    have hane : a ≠ 0 := ne_of_lt ha
    have hcne : c ≠ 0 := ne_of_gt hc
    by_cases hb0 : b = 0
    · subst b
      simp [signChanges, hane, hcne, hac]
    · rcases lt_or_gt_of_ne hb0 with hbneg | hbpos
      · have hab : ¬ a * b < 0 := by
          have : 0 < a * b := mul_pos_of_neg_of_neg ha hbneg
          linarith
        have hbc : b * c < 0 := mul_neg_of_neg_of_pos hbneg hc
        simp [signChanges, hane, hb0, hcne, hab, hbc]
      · have hab : a * b < 0 := mul_neg_of_neg_of_pos ha hbpos
        have hbc : ¬ b * c < 0 := by
          have : 0 < b * c := mul_pos hbpos hc
          linarith
        simp [signChanges, hane, hb0, hcne, hab, hbc]

/-- Continuous lift of the three-entry MSI quotient. Once the endpoint
polynomials are opposite at a reference point, one neighbourhood fixes the
whole three-entry variation at one, with no condition at all on the middle
polynomial. -/
theorem polynomial_triple_variation_locally_one
    (a b c : ℝ[X]) (r : ℝ) (hac : a.eval r * c.eval r < 0) :
    ∀ᶠ x in 𝓝 r, signChanges [a.eval x, b.eval x, c.eval x] = 1 := by
  let f : ℝ → ℝ := fun x => a.eval x * c.eval x
  have hf : ContinuousAt f r := a.continuousAt.mul c.continuousAt
  have hmem : Set.Iio (0 : ℝ) ∈ 𝓝 (f r) := by
    exact IsOpen.mem_nhds isOpen_Iio (by simpa [f] using hac)
  have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
    change f ⁻¹' Set.Iio 0 ∈ 𝓝 r
    exact hf hmem
  filter_upwards [hev] with x hx
  exact signChanges_three_of_opposite_ends _ _ _ (by simpa [f] using hx)

/-- Recursive sign-change counter on an already zero-free list. This is the
same protected observation as the zip/filter implementation, but exposes the
local composition law needed to transport the three-entry quotient through
arbitrary list context. -/
noncomputable def pairChanges : List ℝ → ℕ
  | [] => 0
  | [_] => 0
  | a :: b :: xs => (if a * b < 0 then 1 else 0) + pairChanges (b :: xs)

/-- The recursive counter is extensionally the zip/filter count on any list. -/
theorem pairChanges_eq_zip_filter_length (xs : List ℝ) :
    pairChanges xs = ((xs.zip xs.tail).filter (fun q => q.1 * q.2 < 0)).length := by
  induction xs with
  | nil => simp [pairChanges]
  | cons a xs ih =>
      cases xs with
      | nil => simp [pairChanges]
      | cons b xs =>
          by_cases h : a * b < 0 <;> simp [pairChanges, h, ih]

/-- `signChanges` is the recursive adjacent-pair counter after deleting zeros. -/
theorem signChanges_eq_pairChanges_filter (xs : List ℝ) :
    signChanges xs = pairChanges (xs.filter (· ≠ 0)) := by
  simp only [signChanges]
  exact (pairChanges_eq_zip_filter_length (xs.filter (· ≠ 0))).symm

/-- On a zero-free three-entry block with opposite endpoints, deleting the
middle state preserves the recursive sign-change observation, even with an
arbitrary suffix. -/
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
      simp [pairChanges, hac, hab, hbc]
    · have hab : ¬ a * b < 0 := by
        have : 0 < a * b := mul_pos ha hbpos
        linarith
      have hbc : b * c < 0 := mul_neg_of_pos_of_neg hbpos hc
      simp [pairChanges, hac, hab, hbc]
  · rcases h with ⟨ha, hc⟩
    rcases lt_or_gt_of_ne hb with hbneg | hbpos
    · have hab : ¬ a * b < 0 := by
        have : 0 < a * b := mul_pos_of_neg_of_neg ha hbneg
        linarith
      have hbc : b * c < 0 := mul_neg_of_neg_of_pos hbneg hc
      simp [pairChanges, hac, hab, hbc]
    · have hab : a * b < 0 := mul_neg_of_neg_of_pos ha hbpos
      have hbc : ¬ b * c < 0 := by
        have : 0 < b * c := mul_pos hbpos hc
        linarith
      simp [pairChanges, hac, hab, hbc]

/-- Context lift of the middle-state quotient through an arbitrary zero-free
prefix and suffix. This is the finite-list composition separator needed by
the Sturm tail. -/
theorem pairChanges_context_three_elim_of_opposite_ends
    (xs ys : List ℝ) (a b c : ℝ) (hb : b ≠ 0) (hac : a * c < 0) :
    pairChanges (xs ++ a :: b :: c :: ys) =
      pairChanges (xs ++ a :: c :: ys) := by
  induction xs with
  | nil =>
      simpa using pairChanges_three_elim_of_opposite_ends a b c ys hb hac
  | cons x xs ih =>
      cases xs with
      | nil => simp [pairChanges, ih]
      | cons y zs => simp [pairChanges, ih]

/-- Full behavioural context quotient: whenever two endpoints are opposite,
the middle real value can be deleted anywhere in a list without changing
`signChanges`. Zero and nonzero middle states are handled uniformly. -/
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
  rw [signChanges_eq_pairChanges_filter, signChanges_eq_pairChanges_filter]
  by_cases hb : b = 0
  · subst b
    simp [List.filter_append, ha, hc]
  · simpa [List.filter_append, ha, hb, hc] using
      pairChanges_context_three_elim_of_opposite_ends
        (xs.filter (· ≠ 0)) (ys.filter (· ≠ 0)) a b c hb hac

/-- Continuous arbitrary-context lift. If the endpoint polynomials are
opposite at a reference point, then throughout one neighbourhood the middle
polynomial can be erased from the full list without changing `signChanges`.
This is the composition step required to eliminate isolated zero states from
a Sturm tail before applying ordinary nonzero sign stability. -/
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
