import Theorems.Thm_AdicCompletion_exists_isRegular_pair_of_isIntegrallyClosed_of_ringKrullDim_eq_two
import Theorems.Thm_IsIntegrallyClosed_exists_isRegular_pair_of_two_le_ringKrullDim
import Theorems.Thm_IsLocalRing_exists_ofList_pair_eq_maximalIdeal_and_isRegular_of_isDiscreteValuationRing_quotient
import Theorems.Thm_IsLocalRing_isRegular_of_systemOfParameters
import Theorems.Thm_MvPowerSeries_isRegular_C_cons_X
import Theorems.Thm_RingTheory_Sequence_isRegular_pair_of_isSMulRegular_of_isReduced_of_forall_notMem_minimalPrimes

open IsLocalRing RingTheory
open scoped AdicCompletion.GaloisAction

theorem crystal_weak_adic_pair
    {O : Type} [CommRing O] [IsRegularLocalRing O]
    (hdimO : ringKrullDim O = 2)
    {C : Type} [CommRing C] [IsDomain C] (hCic : IsIntegrallyClosed C)
    [Algebra O C] [Module.Finite O C] [FaithfulSMul O C]
    (𝔫 : Ideal C) [𝔫.IsMaximal] [𝔫.LiesOver (maximalIdeal O)] :
    ∃ a b : AdicCompletion 𝔫 C,
      RingTheory.Sequence.IsWeaklyRegular (AdicCompletion 𝔫 C) [a, b] := by
  rcases
      AdicCompletion.exists_isRegular_pair_of_isIntegrallyClosed_of_ringKrullDim_eq_two
        hdimO hCic 𝔫 with ⟨a, b, h⟩
  exact ⟨a, b, h.toIsWeaklyRegular⟩

theorem crystal_weak_integrally_closed_pair
    {B : Type*} [CommRing B] [IsDomain B] [IsNoetherianRing B]
    [IsLocalRing B] [IsIntegrallyClosed B]
    (hdim : 2 ≤ ringKrullDim B) (t : B)
    (ht : t ∈ IsLocalRing.maximalIdeal B) (ht0 : t ≠ 0) :
    ∃ b : B, b ∈ IsLocalRing.maximalIdeal B ∧
      RingTheory.Sequence.IsWeaklyRegular B [t, b] := by
  rcases
      IsIntegrallyClosed.exists_isRegular_pair_of_two_le_ringKrullDim
        hdim t ht ht0 with ⟨b, hb, h⟩
  exact ⟨b, hb, h.toIsWeaklyRegular⟩

theorem crystal_weak_dvr_quotient_pair
    {A : Type*} [CommRing A] [IsDomain A] [IsLocalRing A]
    (ϖ : A) (hϖ : ϖ ∈ IsLocalRing.maximalIdeal A) (hϖ0 : ϖ ≠ 0)
    [IsDomain (A ⧸ Ideal.span {ϖ})]
    [IsDiscreteValuationRing (A ⧸ Ideal.span {ϖ})] :
    ∃ t : A, Ideal.ofList [ϖ, t] = IsLocalRing.maximalIdeal A ∧
      RingTheory.Sequence.IsWeaklyRegular A [ϖ, t] := by
  rcases
      IsLocalRing.exists_ofList_pair_eq_maximalIdeal_and_isRegular_of_isDiscreteValuationRing_quotient
        ϖ hϖ hϖ0 with ⟨t, ht, h⟩
  exact ⟨t, ht, h.toIsWeaklyRegular⟩

theorem crystal_weak_system_of_parameters
    {R : Type*} [CommRing R] [IsLocalRing R] [IsNoetherianRing R]
    (hCM : (Module.depth R R : WithBot ℕ∞) = ringKrullDim R)
    {d : ℕ} (hdim : ringKrullDim R = d)
    (xs : List R) (hlen : xs.length = d)
    (hmem : ∀ y ∈ xs, y ∈ maximalIdeal R)
    (hsop : ringKrullDim (R ⧸ Ideal.ofList xs) = 0) :
    RingTheory.Sequence.IsWeaklyRegular R xs :=
  (IsLocalRing.isRegular_of_systemOfParameters
    hCM hdim xs hlen hmem hsop).toIsWeaklyRegular

theorem crystal_weak_mvPowerSeries
    {R : Type u} [CommRing R] (n : ℕ) {ϖ : R}
    (hϖ : ϖ ∈ nonZeroDivisors R) (hu : ¬ IsUnit ϖ) :
    RingTheory.Sequence.IsWeaklyRegular (MvPowerSeries (Fin n) R)
      (MvPowerSeries.C ϖ ::
        List.ofFn (MvPowerSeries.X : Fin n → MvPowerSeries (Fin n) R)) :=
  (MvPowerSeries.isRegular_C_cons_X n hϖ hu).toIsWeaklyRegular

theorem crystal_weak_regular_pair
    {A : Type*} [CommRing A] [IsLocalRing A]
    {B : Type*} [CommRing B] [Nontrivial B] [Algebra A B] [Module.Finite A B]
    (a b : A)
    (ha𝔪 : a ∈ IsLocalRing.maximalIdeal A)
    (hb𝔪 : b ∈ IsLocalRing.maximalIdeal A)
    (ha : IsSMulRegular B (algebraMap A B a))
    (hred : IsReduced (B ⧸ Ideal.span {algebraMap A B a}))
    (hb : ∀ P ∈ minimalPrimes (B ⧸ Ideal.span {algebraMap A B a}),
      Ideal.Quotient.mk (Ideal.span {algebraMap A B a}) (algebraMap A B b) ∉ P) :
    RingTheory.Sequence.IsWeaklyRegular B [a, b] :=
  (RingTheory.Sequence.isRegular_pair_of_isSMulRegular_of_isReduced_of_forall_notMem_minimalPrimes
    a b ha𝔪 hb𝔪 ha hred hb).toIsWeaklyRegular
