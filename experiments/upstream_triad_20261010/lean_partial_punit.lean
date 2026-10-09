import Init

-- Kernel counter-test from open leanprover/lean4 PR #15374.
variable (a : Unit → Bool)
example : @PUnit.rec (fun _ => Bool) (a ()) = a := rfl
