import LeftWallComplete

/-!
# Quantitative reverse tape-coordinate embedding

Use Mathlib's existing kernel-checked ℤ ≃ ℕ equivalence rather than proving
a new bijection. This moves an OAI bi-infinite Boolean tape to a Nat-indexed
left-bounded tape while preserving every cell and exposing the linear
bounded-window radius distortion needed by a later reverse compiler.

No claim is made that copying tape cells simulates several independently
moving OAI work heads with one physical source head.
-/

namespace Metalogic.OpenAIMath.ReverseTapeCoordinate

open OAI.ExactDerandomization

/-- Mathlib's even/odd signed-coordinate encoding, reused directly. -/
def tapePosition : ℤ ≃ ℕ := Equiv.intEquivNat

def packWork (work : ℤ → Bool) : ℕ → Bool :=
  fun n => work (tapePosition.symm n)

def unpackWork (work : ℕ → Bool) : ℤ → Bool :=
  fun z => work (tapePosition z)

theorem unpack_packWork (work : ℤ → Bool) :
    unpackWork (packWork work) = work := by
  funext z
  simp [unpackWork, packWork, tapePosition]

theorem pack_unpackWork (work : ℕ → Bool) :
    packWork (unpackWork work) = work := by
  funext n
  simp [unpackWork, packWork, tapePosition]

/-- The canonical zigzag sends +n to 2n and -n-1 to 2n+1. -/
theorem tapePosition_ofNat (n : ℕ) :
    tapePosition (Int.ofNat n) = 2 * n := by
  change Equiv.natSumNatEquivNat (Sum.inl n) = 2 * n
  simp [Equiv.natSumNatEquivNat_apply]

theorem tapePosition_negSucc (n : ℕ) :
    tapePosition (Int.negSucc n) = 2 * n + 1 := by
  change Equiv.natSumNatEquivNat (Sum.inr n) = 2 * n + 1
  simp [Equiv.natSumNatEquivNat_apply]

/-- Every signed coordinate of absolute value at most s occupies a
nonnegative address at most 2s+1. Quantitative resource overhead is explicit. -/
theorem tapePosition_radius (z : ℤ) (s : ℕ)
    (hz : z.natAbs ≤ s) :
    tapePosition z ≤ 2 * s + 1 := by
  cases z with
  | ofNat n =>
      have hn : n ≤ s := by simpa using hz
      rw [tapePosition_ofNat]
      omega
  | negSucc n =>
      have hn : n + 1 ≤ s := by simpa using hz
      rw [tapePosition_negSucc]
      omega

/-- Finite-support preservation: a tape blank outside the signed radius s
is blank beyond the natural-number address 2s+1. -/
theorem packWork_blank_beyond
    (work : ℤ → Bool) (s : ℕ)
    (hblank : ∀ z, s < z.natAbs → work z = false)
    (n : ℕ) (hn : 2 * s + 1 < n) :
    packWork work n = false := by
  have hlarge : s < (tapePosition.symm n).natAbs := by
    by_contra hnlarge
    have hsmall : (tapePosition.symm n).natAbs ≤ s := by omega
    have hbound := tapePosition_radius (tapePosition.symm n) s hsmall
    rw [tapePosition.apply_symm_apply] at hbound
    omega
  exact hblank (tapePosition.symm n) hlarge

end Metalogic.OpenAIMath.ReverseTapeCoordinate
