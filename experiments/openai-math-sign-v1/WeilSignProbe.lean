import Lean

/-!
# Bounded independent arithmetic certificate for the Weil withdrawal

This Lean theorem takes the reverse-trace sign contribution (-1 per trace)
as an EXTERNAL premise of the withdrawal notice; it does not prove that
geometric cusp orientation determines that sign.
-/

namespace Metalogic.OpenAIMath.WeilSign

/-- The obsolete +1-per-trace convention would algebraically cancel -m. -/
theorem claimed_cancellation (m : ℕ) :
    (-(m : ℤ)) + (m : ℤ) = 0 := by
  omega

/-- Under the publisher's corrected -1-per-trace premise, the signed
    count is -2m and cannot vanish when m > 0. -/
theorem corrected_signed_count_nonzero (m : ℕ) (hm : 0 < m) :
    (-(m : ℤ)) - (m : ℤ) ≠ 0 := by
  omega

/-- The corrected expression is exactly -2m, for all natural m. -/
theorem corrected_signed_count_eq (m : ℕ) :
    (-(m : ℤ)) - (m : ℤ) = -2 * (m : ℤ) := by
  omega

end Metalogic.OpenAIMath.WeilSign
