import VerifiedDevelopmentalNavigation.Routing

namespace VerifiedDevelopmentalNavigation.CrossCorpusDemo

def PositiveFLTFor (n : Nat) : Prop :=
  ∀ a b c : Nat, 0 < a → 0 < b → 0 < c → a ^ n + b ^ n ≠ c ^ n

def NonzeroFLTFor (n : Nat) : Prop :=
  ∀ a b c : Nat, a ≠ 0 → b ≠ 0 → c ≠ 0 → a ^ n + b ^ n ≠ c ^ n

theorem positiveFLTFor_iff_nonzeroFLTFor (n : Nat) :
    PositiveFLTFor n ↔ NonzeroFLTFor n := by
  simpa [PositiveFLTFor, NonzeroFLTFor] using
    (positiveNat3Surface_iff_nonzeroNat3Surface
      (fun a b c => a ^ n + b ^ n ≠ c ^ n))

theorem source_zero : PositiveFLTFor 0 := by
  intro a b c ha hb hc
  simp

theorem consumer_zero_from_source : NonzeroFLTFor 0 :=
  (positiveFLTFor_iff_nonzeroFLTFor 0).mp source_zero

end VerifiedDevelopmentalNavigation.CrossCorpusDemo
