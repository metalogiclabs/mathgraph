import MathGraphPalomarClosure

namespace MathGraphPalomarClosure

private def NoOR (s : State) : Prop := ∀ p, s p ≠ .OR

private theorem noOR_rotate {s : State} (h : NoOR s) : NoOR (rotate s) := by
  intro p
  exact h (pred p)

private theorem noOR_ltle {s : State} (p : Pos) (h : NoOR s) :
    NoOR (replaceAt p .LT .LE s) := by
  intro q
  by_cases hqp : q = p
  · subst q
    by_cases hs : s p = .LT
    · simp [replaceAt, hs]
    · simp [replaceAt, hs, h p]
  · simp [replaceAt, hqp, h q]

private theorem step1_preserves_noOR {x y : State} (hxy : Step1 x y) (hx : NoOR x) : NoOR y := by
  cases hxy with
  | rot =>
      exact noOR_rotate hx
  | ltle _ p =>
      exact noOR_ltle p hx

private theorem reach1_preserves_noOR {x y : State} (hxy : Reach1 x y) : NoOR x → NoOR y := by
  induction hxy with
  | refl =>
      intro hx
      exact hx
  | tail hreach hstep ih =>
      intro hx
      exact step1_preserves_noOR hstep (ih hx)

theorem orbit_identity : OrbitEq r0LTLE r2LTLE := by
  refine ⟨2, by decide, ?_, rfl, rfl⟩
  rfl

theorem strict_closure_obstruction : ¬ Reach1 start target := by
  intro hreach
  have hno : NoOR target := reach1_preserves_noOR hreach (by
    intro p
    cases p <;> decide)
  exact hno .p3 rfl

theorem strict_closure_expansion : Reach2 start target := by
  have e1 : replaceAt .p1 .LT .LE start = afterO1 := by
    funext p
    cases p <;> rfl
  have e2 : replaceAt .p3 .AND .OR afterO1 = target := by
    funext p
    cases p <;> rfl
  have h0 : Reach2 start start := Reach2.refl start
  have h1 : Reach2 start afterO1 := by
    rw [← e1]
    exact Reach2.tail h0 (Step2.ltle start .p1)
  rw [← e2]
  exact Reach2.tail h1 (Step2.andor afterO1 .p3)

theorem raw_formability_boundary : RawFormable r3ANDOR := by
  exact ⟨.p3, .AND, .OR, rfl⟩

end MathGraphPalomarClosure
