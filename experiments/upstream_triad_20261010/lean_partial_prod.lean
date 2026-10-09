import Init

-- Kernel counter-test from open leanprover/lean4 PR #15374.
variable (a : Bool × Bool → Bool)
example : @Prod.rec Bool Bool (motive := fun _ => Bool) (fun b c => a (b,c)) = a := rfl
