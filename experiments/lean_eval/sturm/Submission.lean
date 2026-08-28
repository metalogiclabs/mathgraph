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
  have hsign := simple_root_local_crossing_sign p r hr hd
  have hU : U ∈ 𝓝 r := by
    rcases hsign with ⟨hleft, hright⟩
    filter_upwards [hleft, hright] with x hxleft hxright
    exact ⟨hxleft, hxright⟩
  refine ⟨U, hU, ?_⟩
  intro x hx y hy hxr hry
  have hxsign : p.eval x * p.derivative.eval r < 0 := hx.1 hxr
  have hysign : 0 < p.eval y * p.derivative.eval r := hy.2 hry
  exact signChanges_simple_crossing _ _ _ hxsign hysign
