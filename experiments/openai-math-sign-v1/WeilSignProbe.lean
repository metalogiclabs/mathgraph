import Lean

/-!
A kernel-checked conditional arithmetic witness only.
The publisher's orientation premise (-1 per reverse trace) is EXTERNAL.
-/

namespace Metalogic.OpenAIMath.WeilSign

/-- The incorrect +1-per-trace convention would have cancelled the initial count. -/
theorem claimed_cancellation (m : Int) :
    -m + m = 0 := by
  omega

/-- If each reverse trace contributes -1, then m positive
    leaves nonzero signed count; this does not verify the geometric premise. -/
theorem corrected_signed_count_nonzero (m : Int) (hm : 0 < m) :
    -m - m ≠ 0 := by
  omega

/-- The resulting signed count is exactly -2m. -/
theorem corrected_signed_count_eq (m : Int) :
    -m - m = -2 * m := by
  omega

end Metalogic.OpenAIMath.WeilSign
