import ChallengeDeps
import TailComposition

open LeanEval.Algebra
open Polynomial
open scoped Classical Topology

/-- If the next Sturm remainder vanishes at a point, the following remainder
has value opposite to the current entry. -/
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

/-- Squarefree polynomials and their derivatives have no common real root. -/
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

/-- No-common-zero is preserved by a negated-remainder Sturm step. -/
theorem sturm_step_no_common_zero (a b : ℝ[X]) (r : ℝ)
    (hab : ¬ (a.eval r = 0 ∧ b.eval r = 0)) :
    ¬ (b.eval r = 0 ∧ (-(a % b)).eval r = 0) := by
  rintro ⟨hb, hc⟩
  have hnext := sturm_next_after_zero a b r hb
  have ha : a.eval r = 0 := by
    rw [hnext] at hc
    simpa using hc
  exact hab ⟨ha, hb⟩

/-- Safety of active adjacent states. -/
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

/-- The missing boundary condition from the failed arbitrary-fuel probe:
not only are active adjacent states regular, but if fuel ends, the displayed
terminal entry is nonzero at the reference point. -/
noncomputable def SturmRegularAt (r : ℝ) : ℝ[X] → ℝ[X] → ℕ → Prop
  | a, _, 0 => a.eval r ≠ 0
  | a, b, n + 1 =>
      if b = 0 then a.eval r ≠ 0
      else (¬ (a.eval r = 0 ∧ b.eval r = 0)) ∧ SturmRegularAt r b (-(a % b)) n

/-- A Sturm computation is never empty and its head is its first argument. -/
theorem sturmAux_eq_cons_tail (a b : ℝ[X]) (n : ℕ) :
    sturmAux a b n = a :: (sturmAux a b n).tail := by
  cases n with
  | zero => simp [sturmAux]
  | succ n =>
      by_cases hb : b = 0 <;> simp [sturmAux, hb]

/-- Explicit two-head composition law.  This avoids unfolding the benchmark's
zip/filter representation inside the recursive proof. -/
theorem signChanges_cons_cons_of_ne_zero
    (a b : ℝ) (xs : List ℝ) (ha : a ≠ 0) (hb : b ≠ 0) :
    signChanges (a :: b :: xs) =
      (if a * b < 0 then 1 else 0) + signChanges (b :: xs) := by
  rw [signChanges_eq_pairChanges_filter, signChanges_eq_pairChanges_filter]
  simp [ha, hb, pairChanges]

/-- Correct arbitrary-fuel local-constancy theorem.  Unlike mere active-state
safety, `SturmRegularAt` protects the displayed terminal entry when fuel is
exhausted. -/
theorem sturmAux_variation_locally_constant
    (a b : ℝ[X]) (r : ℝ) (n : ℕ)
    (ha : a.eval r ≠ 0) (hreg : SturmRegularAt r a b n) :
    ∀ᶠ x in 𝓝 r,
      signChanges ((sturmAux a b n).map (fun q => q.eval x)) =
      signChanges ((sturmAux a b n).map (fun q => q.eval r)) := by
  induction n using Nat.strong_induction_on generalizing a b with
  | h n ih =>
      cases n with
      | zero =>
          simp [sturmAux, signChanges]
      | succ n =>
          by_cases hbpoly : b = 0
          · simp [sturmAux, hbpoly, signChanges]
          · have hreg' :
                (¬ (a.eval r = 0 ∧ b.eval r = 0)) ∧
                  SturmRegularAt r b (-(a % b)) n := by
              simpa [SturmRegularAt, hbpoly] using hreg
            let c : ℝ[X] := -(a % b)
            have hrecReg : SturmRegularAt r b c n := by
              simpa [c] using hreg'.2
            by_cases hb : b.eval r = 0
            · have hc : c.eval r = -a.eval r := by
                dsimp [c]
                exact sturm_next_after_zero a b r hb
              have hcne : c.eval r ≠ 0 := by
                rw [hc]
                exact neg_ne_zero.mpr ha
              cases n with
              | zero =>
                  have : b.eval r ≠ 0 := by simpa [SturmRegularAt] using hrecReg
                  exact (this hb).elim
              | succ m =>
                  have hcpoly : c ≠ 0 := by
                    intro hz
                    have : c.eval r = 0 := by simp [hz]
                    exact hcne this
                  let d : ℝ[X] := -(b % c)
                  have hcdreg : SturmRegularAt r c d m := by
                    simpa [SturmRegularAt, c, d, hcpoly] using hrecReg
                  have htail := ih m (by omega) c d hcne hcdreg
                  have hac : a.eval r * c.eval r < 0 := by
                    rw [hc]
                    have hpos : 0 < a.eval r * a.eval r := mul_self_pos.mpr ha
                    nlinarith
                  have hevac := polynomial_pair_signchange_locally_constant a c r ha hcne
                  have haev := polynomial_eval_eventually_ne_zero a r ha
                  have hcev := polynomial_eval_eventually_ne_zero c r hcne
                  filter_upwards [htail, hevac, haev, hcev] with x htailx hpac hax hcx
                  have hshapeX :
                      signChanges ((sturmAux a b (Nat.succ (Nat.succ m))).map (fun q => q.eval x)) =
                      signChanges (a.eval x :: b.eval x :: c.eval x ::
                        ((sturmAux c d m).tail.map (fun q => q.eval x))) := by
                    simp [sturmAux, hbpoly, c, d, hcpoly, sturmAux_eq_cons_tail]
                  have hshapeR :
                      signChanges ((sturmAux a b (Nat.succ (Nat.succ m))).map (fun q => q.eval r)) =
                      signChanges (a.eval r :: b.eval r :: c.eval r ::
                        ((sturmAux c d m).tail.map (fun q => q.eval r))) := by
                    simp [sturmAux, hbpoly, c, d, hcpoly, sturmAux_eq_cons_tail]
                  rw [hshapeX, hshapeR]
                  rw [signChanges_context_three_elim_of_opposite_ends
                        [] ((sturmAux c d m).tail.map (fun q => q.eval x))
                        (a.eval x) (b.eval x) (c.eval x)]
                  · rw [signChanges_context_three_elim_of_opposite_ends
                          [] ((sturmAux c d m).tail.map (fun q => q.eval r))
                          (a.eval r) (b.eval r) (c.eval r) hac]
                    simp only [List.nil_append, List.map_tail]
                    rw [signChanges_cons_cons_of_ne_zero _ _ _ hax hcx,
                        signChanges_cons_cons_of_ne_zero _ _ _ ha hcne]
                    have htailShapeX := sturmAux_eq_cons_tail c d m
                    have htailShapeR := sturmAux_eq_cons_tail c d m
                    simp only [List.map_cons, List.map_tail] at htailx
                    rw [htailShapeX] at htailx
                    simpa using congrArg (fun k => (if a.eval r * c.eval r < 0 then 1 else 0) + k) htailx
                  · have hpac' := hpac
                    simpa using (show a.eval x * c.eval x < 0 from by
                      by_cases h : a.eval r * c.eval r < 0
                      · simpa [h] using hpac'
                      · exact (h hac).elim)
            · have hbne : b.eval r ≠ 0 := hb
              have hb_ev := polynomial_eval_eventually_ne_zero b r hbne
              have ha_ev := polynomial_eval_eventually_ne_zero a r ha
              have hp := polynomial_pair_signchange_locally_constant a b r ha hbne
              have htail := ih n (by omega) b c hbne hrecReg
              filter_upwards [hb_ev, ha_ev, hp, htail] with x hbx hax hpair htailx
              rw [show sturmAux a b (Nat.succ n) = a :: sturmAux b c n by
                simp [sturmAux, hbpoly, c]]
              have hsx := sturmAux_eq_cons_tail b c n
              have hsr := sturmAux_eq_cons_tail b c n
              rw [hsx, hsr]
              simp only [List.map_cons, List.map_tail]
              rw [signChanges_cons_cons_of_ne_zero _ _ _ hax hbx,
                  signChanges_cons_cons_of_ne_zero _ _ _ ha hbne]
              simpa [hpair] using congrArg (fun k =>
                (if a.eval r * b.eval r < 0 then 1 else 0) + k) htailx
