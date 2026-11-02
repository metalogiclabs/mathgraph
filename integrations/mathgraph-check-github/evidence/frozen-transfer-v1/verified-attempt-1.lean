import Mathlib
open Function Fintype Subgroup Ideal Polynomial Submodule Zsqrtd
open scoped BigOperators

theorem Artin_exercise_2_11_3 {G : Type*} [Group G] [Fintype G]
  (hG : Even (card G)) : ∃ x : G, orderOf x = 2 := by
  have hf : 2 ∣ Fintype.card G := even_iff_two_dvd.mp hG
  have hn : 2 ∣ Nat.card G := by
    simpa only [Nat.card_eq_fintype_card] using hf
  letI : Fact (Nat.Prime 2) := ⟨Nat.prime_two⟩
  first
  | exact exists_prime_orderOf_dvd_card (G := G) (p := 2) hn
  | exact exists_prime_orderOf_dvd_card (G := G) (p := 2) hf
  | exact exists_prime_orderOf_dvd_card (G := G) Nat.prime_two hn
  | exact exists_prime_orderOf_dvd_card (G := G) Nat.prime_two hf
  | exact exists_prime_orderOf_dvd_card (G := G) 2 hn
  | exact exists_prime_orderOf_dvd_card (G := G) 2 hf
