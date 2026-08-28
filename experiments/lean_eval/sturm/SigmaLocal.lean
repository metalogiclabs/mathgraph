import ChallengeDeps
import TailComposition

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- If the next Sturm remainder vanishes at a point, the following remainder
has value opposite to the current entry. This is the local regularity law
used to quotient an interior zero out of the chain. -/
theorem sturm_next_after_zero (a b : ℝ[X]) (r : ℝ)
    (hb : b.eval r = 0) :
    (-(a % b)).eval r = -a.eval r := by
  have h := congrArg (fun q : ℝ[X] => q.eval r) (EuclideanDomain.mod_add_div a b)
  have hrem : (a % b).eval r = a.eval r := by
    simpa [hb] using h
  simp [hrem]

/-- A nonzero polynomial evaluation is locally nonzero. -/
theorem polynomial_eval_eventually_ne_zero (p : ℝ[X]) (r : ℝ)
    (hp : p.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r, p.eval x ≠ 0 := by
  have hcont : ContinuousAt (fun x : ℝ => p.eval x) r := p.continuousAt
  have hopen : ({0}ᶜ : Set ℝ) ∈ 𝓝 (p.eval r) := by
    exact IsOpen.mem_nhds isOpen_compl_singleton hp
  change (fun x : ℝ => p.eval x) ⁻¹' ({0}ᶜ : Set ℝ) ∈ 𝓝 r
  exact hcont hopen

/-- Two nonzero adjacent Sturm entries have locally constant pair variation. -/
theorem polynomial_pair_signchange_locally_constant
    (a b : ℝ[X]) (r : ℝ) (ha : a.eval r ≠ 0) (hb : b.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r,
      (if a.eval x * b.eval x < 0 then 1 else 0) =
      (if a.eval r * b.eval r < 0 then 1 else 0) := by
  let f : ℝ → ℝ := fun x => a.eval x * b.eval x
  have hf : ContinuousAt f r := a.continuousAt.mul b.continuousAt
  have hfr : f r ≠ 0 := by simpa [f] using mul_ne_zero ha hb
  rcases lt_or_gt_of_ne hfr with hneg | hpos
  · have hmem : Set.Iio (0 : ℝ) ∈ 𝓝 (f r) := IsOpen.mem_nhds isOpen_Iio hneg
    have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
      change f ⁻¹' Set.Iio 0 ∈ 𝓝 r
      exact hf hmem
    filter_upwards [hev] with x hx
    simp [f, hx, hneg]
  · have hmem : Set.Ioi (0 : ℝ) ∈ 𝓝 (f r) := IsOpen.mem_nhds isOpen_Ioi hpos
    have hev : ∀ᶠ x in 𝓝 r, 0 < f x := by
      change f ⁻¹' Set.Ioi 0 ∈ 𝓝 r
      exact hf hmem
    filter_upwards [hev] with x hx
    have hnx : ¬ f x < 0 := not_lt.mpr (le_of_lt hx)
    have hnr : ¬ f r < 0 := not_lt.mpr (le_of_lt hpos)
    simp [f, hnx, hnr]

/-- Squarefreeness protects the Sturm start pair: a real root of `p` cannot
also be a root of `p'`. -/
theorem squarefree_root_derivative_ne_zero (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) (hr : p.eval r = 0) :
    p.derivative.eval r ≠ 0 := by
  have hsep : p.Separable := (PerfectField.separable_iff_squarefree).2 hp
  exact hsep.eval₂_derivative_ne_zero (RingHom.id ℝ) hr

theorem squarefree_sturm_start_no_common_root (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) :
    ¬ (p.eval r = 0 ∧ p.derivative.eval r = 0) := by
  rintro ⟨hr, hdr⟩
  exact squarefree_root_derivative_ne_zero p r hp hr hdr

/-- The no-common-zero condition is preserved by one negated-remainder Sturm
step. -/
theorem sturm_step_no_common_zero (a b : ℝ[X]) (r : ℝ)
    (hab : ¬ (a.eval r = 0 ∧ b.eval r = 0)) :
    ¬ (b.eval r = 0 ∧ (-(a % b)).eval r = 0) := by
  rintro ⟨hb, hc⟩
  have hnext := sturm_next_after_zero a b r hb
  have ha : a.eval r = 0 := by
    rw [hnext] at hc
    simpa using hc
  exact hab ⟨ha, hb⟩

noncomputable def SturmSafeAt (r : ℝ) : ℝ[X] → ℝ[X] → ℕ → Prop
  | _, _, 0 => True
  | a, b, n + 1 =>
      if b = 0 then True
      else (¬ (a.eval r = 0 ∧ b.eval r = 0)) ∧ SturmSafeAt r b (-(a % b)) n

theorem sturmSafeAt_of_no_common_zero (a b : ℝ[X]) (r : ℝ) (n : ℕ)
    (hab : ¬ (a.eval r = 0 ∧ b.eval r = 0)) :
    SturmSafeAt r a b n := by
  induction n generalizing a b with
  | zero => simp [SturmSafeAt]
  | succ n ih =>
      by_cases hbpoly : b = 0
      · simp [SturmSafeAt, hbpoly]
      · simp only [SturmSafeAt, hbpoly, if_false]
        exact ⟨hab, ih b (-(a % b)) (sturm_step_no_common_zero a b r hab)⟩

theorem squarefree_sturmChain_safe (p : ℝ[X]) (r : ℝ)
    (hp : Squarefree p) :
    SturmSafeAt r p p.derivative (p.natDegree + 2) := by
  exact sturmSafeAt_of_no_common_zero p p.derivative r (p.natDegree + 2)
    (squarefree_sturm_start_no_common_root p r hp)

/-- Prefixing a nonzero real value adds exactly the sign-change contribution
of the first surviving tail entry.  This is the composition interface used by
the arbitrary-fuel induction. -/
theorem signChanges_cons_of_head_ne_zero (a : ℝ) (xs : List ℝ) (ha : a ≠ 0) :
    signChanges (a :: xs) =
      match xs.filter (· ≠ 0) with
      | [] => 0
      | b :: _ => (if a * b < 0 then 1 else 0) + signChanges xs := by
  simp [signChanges, ha]
  cases h : xs.filter (· ≠ 0) with
  | nil => simp [h, signChanges]
  | cons b bs => simp [h, signChanges]

/-- Arbitrary-fuel local constancy for a Sturm tail whose current head is
nonzero at the reference point. `SturmSafeAt` rules out the terminal-zero
pathology; interior zeros are quotiented by the opposite-neighbour law. -/
theorem sturmAux_variation_locally_constant
    (a b : ℝ[X]) (r : ℝ) (n : ℕ)
    (ha : a.eval r ≠ 0) (hsafe : SturmSafeAt r a b n) :
    ∀ᶠ x in 𝓝 r,
      signChanges ((sturmAux a b n).map (fun q => q.eval x)) =
      signChanges ((sturmAux a b n).map (fun q => q.eval r)) := by
  induction n using Nat.strong_induction_on generalizing a b with
  | h n ih =>
      cases n with
      | zero =>
          simpa [sturmAux, signChanges] using polynomial_eval_eventually_ne_zero a r ha
      | succ n =>
          by_cases hbpoly : b = 0
          · have haev := polynomial_eval_eventually_ne_zero a r ha
            filter_upwards [haev] with x hax
            simp [sturmAux, hbpoly, signChanges, ha, hax]
          · have hsafe' :
                (¬ (a.eval r = 0 ∧ b.eval r = 0)) ∧
                  SturmSafeAt r b (-(a % b)) n := by
              simpa [SturmSafeAt, hbpoly] using hsafe
            let c : ℝ[X] := -(a % b)
            have hrecSafe : SturmSafeAt r b c n := by simpa [c] using hsafe'.2
            by_cases hb : b.eval r = 0
            · have hc : c.eval r = -a.eval r := by
                dsimp [c]
                exact sturm_next_after_zero a b r hb
              have hcne : c.eval r ≠ 0 := by simpa [hc] using ha
              cases n with
              | zero =>
                  have hac : a.eval r * c.eval r < 0 := by
                    rw [hc]
                    have hpos : 0 < a.eval r * a.eval r := mul_self_pos.mpr ha
                    nlinarith
                  let f : ℝ → ℝ := fun x => a.eval x * c.eval x
                  have hf : ContinuousAt f r := a.continuousAt.mul c.continuousAt
                  have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
                    apply hf.eventually_lt_const
                    simpa [f] using hac
                  filter_upwards [hev] with x hx
                  simp [sturmAux, hbpoly, c, signChanges, hb, hc, f] at hx ⊢
              | succ m =>
                  have hcpoly : c ≠ 0 := by
                    intro hz
                    subst c
                    simpa using hcne
                  let d : ℝ[X] := -(b % c)
                  have hcdsafe : SturmSafeAt r c d m := by
                    simpa [SturmSafeAt, c, d, hcpoly] using hrecSafe
                  have htail := ih m (Nat.lt_succ_self m) c d hcne hcdsafe
                  have hac : a.eval r * c.eval r < 0 := by
                    rw [hc]
                    have hpos : 0 < a.eval r * a.eval r := mul_self_pos.mpr ha
                    nlinarith
                  let f : ℝ → ℝ := fun x => a.eval x * c.eval x
                  have hf : ContinuousAt f r := a.continuousAt.mul c.continuousAt
                  have hev : ∀ᶠ x in 𝓝 r, f x < 0 := by
                    apply hf.eventually_lt_const
                    simpa [f] using hac
                  filter_upwards [htail, hev] with x htx hx
                  rw [show sturmAux a b (Nat.succ (Nat.succ m)) =
                    a :: b :: sturmAux c d m by
                      simp [sturmAux, hbpoly, c, d, hcpoly]]
                  simp only [List.map_cons]
                  have hxdrop := signChanges_context_three_of_opposite_ends
                    ([] : List ℝ) (a.eval x) (b.eval x) (c.eval x)
                    ((sturmAux c d m).map (fun q => q.eval x)).tail
                    (by simpa [f] using hx)
                  have hrdrop := signChanges_context_three_of_opposite_ends
                    ([] : List ℝ) (a.eval r) (b.eval r) (c.eval r)
                    ((sturmAux c d m).map (fun q => q.eval r)).tail hac
                  simpa [sturmAux] using hxdrop.trans (congrArg (fun z => z) htx) |>.trans hrdrop.symm
            · have hbne := hb
              have hb_ev := polynomial_eval_eventually_ne_zero b r hbne
              have hp := polynomial_pair_signchange_locally_constant a b r ha hbne
              have htail := ih n (Nat.lt_succ_self n) b c hbne hrecSafe
              filter_upwards [hb_ev, hp, htail, polynomial_eval_eventually_ne_zero a r ha]
                with x hbx hpair htailx hax
              rw [show sturmAux a b (Nat.succ n) = a :: sturmAux b c n by
                simp [sturmAux, hbpoly, c]]
              simp only [List.map_cons]
              rw [signChanges_cons_of_head_ne_zero _ _ hax,
                  signChanges_cons_of_head_ne_zero _ _ ha]
              simpa [sturmAux, hbpoly, c, hbx, hbne] using congrArg (fun k => k + signChanges ((sturmAux b c n).map (fun q => q.eval x))) hpair

/-- The benchmark-facing corollary: away from a root of a squarefree
polynomial, its complete Sturm-chain variation is locally constant. -/
theorem squarefree_sigma_locally_constant_at_nonroot
    (p : ℝ[X]) (r : ℝ) (hp : Squarefree p) (hr : p.eval r ≠ 0) :
    ∀ᶠ x in 𝓝 r, sigma p x = sigma p r := by
  simpa [sigma, sturmChain] using
    sturmAux_variation_locally_constant p p.derivative r (p.natDegree + 2) hr
      (squarefree_sturmChain_safe p r hp)
