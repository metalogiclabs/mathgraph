import Mathlib
open Function Fintype Subgroup Ideal Polynomial Submodule Zsqrtd
open scoped BigOperators

theorem Artin_exercise_2_4_19 {G : Type*} [Group G] {x : G}
  (hx : orderOf x = 2) (hx1 : ∀ y, orderOf y = 2 → y = x) :
  x ∈ center G := by
  have hx2 : x ^ 2 = 1 := by
    simpa only [hx] using pow_orderOf_eq_one x
  have hxne : x ≠ 1 := by
    intro h
    simp [h] at hx
  have hc (y : G) : y * x * y⁻¹ = x := by
    have hp : (y * x * y⁻¹) ^ 2 = 1 := by
      calc
        (y * x * y⁻¹) ^ 2 = y * x ^ 2 * y⁻¹ := by simp only [pow_succ, pow_zero, mul_one]; group
        _ = 1 := by simp [hx2]
    have hd : orderOf (y * x * y⁻¹) ∣ 2 :=
      orderOf_dvd_of_pow_eq_one hp
    rcases (Nat.dvd_prime Nat.prime_two).mp hd with h | h
    · have hz : y * x * y⁻¹ = 1 := by
        simpa only [h, pow_one] using pow_orderOf_eq_one (y * x * y⁻¹)
      have he : x = 1 := by
        have hh := congrArg (fun z : G => y⁻¹ * z * y) hz
        simpa [mul_assoc] using hh
      exact (hxne he).elim
    · exact hx1 _ h
  rw [Subgroup.mem_center_iff]
  intro y
  have h := congrArg (fun z : G => z * y) (hc y)
  simpa only [mul_assoc, inv_mul_cancel, mul_one] using h
