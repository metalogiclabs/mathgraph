import Init

-- Control: ordinary function eta is accepted by Lean.
variable (a : Unit → Bool)
example : (fun h => a h) = a := rfl

variable (b : Bool × Bool → Bool)
example : (fun h => b h) = b := rfl
