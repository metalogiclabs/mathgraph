import Theorems.Thm_Algebra_norm_of_subsingleton

universe u v

/-- Consumer theorem reuses the externally sourced Anthropic theorem object. -/
theorem crystal_real_reuse_norm {R : Type u} {A : Type v}
    [CommRing R] [Ring A] [Algebra R A] [Subsingleton A] (a : A) :
    Algebra.norm R a = 1 :=
  Algebra.norm_of_subsingleton a
