/-
Mathathon Round 1, Problem 127: official Lean statement, prepared by AI. It may contain errors.

Written by AI for Mathathon; not taken from an existing formalization.
It states the first Rogers–Ramanujan identity in the partition form given on the problem page
(MacMahon, Schur): for every `n`, the partitions of `n` into parts congruent to 1 or 4 modulo 5
are equinumerous with the partitions of `n` whose parts differ pairwise by at least 2. Partitions
are Mathlib's `Nat.Partition` (multisets of positive parts) and the first family is Mathlib's
`Nat.Partition.restricted`. "Parts differ by at least 2" is written as: no part is repeated and no
two parts are consecutive integers. The problem asks for a natural bijection; "natural" is not a
formal notion, so the statement is the equality of the two numbers, which any bijection proves.
-/

import Mathlib

namespace Mathathon.P127

/-- The partitions of `n` whose parts differ pairwise by at least `2`: no part occurs twice and,
for every part `i`, the integer `i + 1` is not a part. -/
def gapTwoPartitions (n : ℕ) : Finset n.Partition :=
  Finset.univ.filter fun p => p.parts.Nodup ∧ ∀ i ∈ p.parts, i + 1 ∉ p.parts

/-- **First Rogers–Ramanujan identity**, partition form: the number of partitions of `n` into
parts congruent to `1` or `4` modulo `5` equals the number of partitions of `n` into parts that
differ pairwise by at least `2`. -/
theorem rogers_ramanujan (n : ℕ) :
    (Nat.Partition.restricted n (fun i => i % 5 = 1 ∨ i % 5 = 4)).card =
      (gapTwoPartitions n).card := by
  sorry

end Mathathon.P127
