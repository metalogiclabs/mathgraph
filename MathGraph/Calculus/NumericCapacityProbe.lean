import Std

#check Fintype.card
#check Fintype.card_congr
#check Fintype.card_le_of_injective
#check Fintype.card_fun
#check Fintype.card_fin
#check Fintype.card_bool
#check Nat.pow
#check Nat.lt_succ_self

example (b : Nat) : Fintype.card (Fin b → Bool) = 2 ^ b := by
  simp

example (b : Nat) : Fintype.card (Fin (2 ^ b + 1)) = 2 ^ b + 1 := by
  simp
