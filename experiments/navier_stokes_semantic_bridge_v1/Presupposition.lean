import Mathlib

/-!
Source: Bastounis, Circelli, Hansen, arXiv:2610.08144v1, section 4.2,
page 15. PaperCode reproduces the displayed code, preserving its Int/Nat/Rat
domains, `!=` predicate and totalised sInf definition. Only the namespace
is added. The source contract below is an explicitly authored interpretation
of "the least natural number satisfying B, then 1/(n+1)". The kernel checks
mathematical correspondence with this contract, not NL interpretation.
No Navier-Stokes estimate or general autoformalisation theorem is claimed.
-/
namespace PaperCode

def p_e (n x1 x2 : Int) : Int := x1 + x2 - n
def B_e (n : Nat) : Prop :=
  forall (x1 x2 : Nat), p_e (n : Int) (x1 : Int) (x2 : Int) != 0
noncomputable def n_e : Nat := sInf {n : Nat | B_e n}
noncomputable def r_e : Rat := 1 / (n_e + 1)
theorem example_3_1 : (r_e + 1) ^ 2 = r_e ^ 2 + 2 * r_e + 1 := by ring

end PaperCode

namespace MathGraph.Presupposition

/-- Independent specification: retain membership, leastness and the value. -/
def MinimumValueSpec (S : Set Nat) (r : Rat) : Prop :=
  ∃ n : Nat, n ∈ S ∧ (∀ m : Nat, m ∈ S → n ≤ m) ∧
    r = 1 / ((n : Rat) + 1)

/-- The total implementation under audit, including its empty-set behavior. -/
noncomputable def totalizedValue (S : Set Nat) : Rat :=
  1 / (((sInf S : Nat) : Rat) + 1)

/-- The exact prerequisite, not a procedure deciding arbitrary nonemptiness. -/
theorem minimum_spec_iff_nonempty (S : Set Nat) :
    MinimumValueSpec S (totalizedValue S) ↔ S.Nonempty := by
  constructor
  · rintro ⟨n, hn, _, _⟩
    exact ⟨n, hn⟩
  · intro hS
    refine ⟨sInf S, Nat.sInf_mem hS, ?_, rfl⟩
    intro m hm
    exact Nat.sInf_le hm

/-- Full contract correspondence: both necessity and sufficiency, all S and r. -/
theorem minimum_spec_iff_value (S : Set Nat) (r : Rat) :
    MinimumValueSpec S r ↔ S.Nonempty ∧ r = totalizedValue S := by
  constructor
  · rintro ⟨n, hn, hleast, hr⟩
    have hS : S.Nonempty := ⟨n, hn⟩
    have hnmin : n = sInf S :=
      le_antisymm (hleast (sInf S) (Nat.sInf_mem hS)) (Nat.sInf_le hn)
    refine ⟨hS, ?_⟩
    simpa only [hnmin, totalizedValue] using hr
  · rintro ⟨hS, rfl⟩
    exact (minimum_spec_iff_nonempty S).mpr hS

/-- An independently written ordinary nonzero predicate for the source text. -/
def SourceNoRoot (n : Nat) : Prop :=
  ∀ x y : Nat, (x : Int) + (y : Int) - (n : Int) ≠ 0

def SourceClaim (r : Rat) : Prop :=
  MinimumValueSpec {n : Nat | SourceNoRoot n} r

/-- The explicit root (n,0) refutes the source presupposition for every n. -/
theorem source_no_root_false (n : Nat) : ¬ SourceNoRoot n := by
  intro hn
  exact hn n 0 (by simp)

/-- Check the same fact for the paper's actual Boolean-inequality code. -/
theorem paper_no_root_false (n : Nat) : ¬ PaperCode.B_e n := by
  intro hn
  have h := hn n 0
  simp [PaperCode.p_e] at h

theorem source_predicate_matches (n : Nat) :
    SourceNoRoot n ↔ PaperCode.B_e n := by
  simp only [source_no_root_false n, paper_no_root_false n]

theorem paper_set_empty : {n : Nat | PaperCode.B_e n} = ∅ := by
  ext n
  change PaperCode.B_e n ↔ False
  exact iff_false_intro (paper_no_root_false n)

theorem paper_minimum_is_zero : PaperCode.n_e = 0 := by
  unfold PaperCode.n_e
  rw [paper_set_empty]
  exact Nat.sInf_empty

theorem paper_value_is_one : PaperCode.r_e = 1 := by
  simp [PaperCode.r_e, paper_minimum_is_zero]

theorem no_source_value (r : Rat) : ¬ SourceClaim r := by
  rintro ⟨n, hn, _, _⟩
  exact source_no_root_false n hn

/-- Actual source/target counterexample, not a comparison of labels. -/
theorem paper_identity_and_missing_source :
    ((PaperCode.r_e + 1) ^ 2 = PaperCode.r_e ^ 2 + 2 * PaperCode.r_e + 1) ∧
      ¬ SourceClaim PaperCode.r_e :=
  ⟨PaperCode.example_3_1, no_source_value PaperCode.r_e⟩

theorem identity_does_not_supply_source_witness :
    ¬ (((PaperCode.r_e + 1) ^ 2 = PaperCode.r_e ^ 2 + 2 * PaperCode.r_e + 1) →
      SourceClaim PaperCode.r_e) := by
  intro h
  exact no_source_value PaperCode.r_e (h PaperCode.example_3_1)

theorem empty_spec_invalid (r : Rat) : ¬ MinimumValueSpec (∅ : Set Nat) r := by
  rintro ⟨n, hn, _, _⟩
  exact hn

/-- Positive control: zero is also a perfectly legitimate minimum. -/
theorem zero_spec_valid : MinimumValueSpec ({0} : Set Nat) (1 : Rat) := by
  refine ⟨0, by simp, ?_, ?_⟩
  · intro m _
    exact Nat.zero_le m
  · norm_num

theorem empty_value_is_one : totalizedValue (∅ : Set Nat) = 1 := by
  simp [totalizedValue, Nat.sInf_empty]

theorem zero_value_is_one : totalizedValue ({0} : Set Nat) = 1 :=
  ((minimum_spec_iff_value ({0} : Set Nat) 1).mp zero_spec_valid).2.symm

theorem empty_and_zero_same_value :
    totalizedValue (∅ : Set Nat) = totalizedValue ({0} : Set Nat) :=
  empty_value_is_one.trans zero_value_is_one.symm

/-- Consequential separator: the result alone cannot recover definedness,
regardless of whether the proposed recovery predicate is computable. -/
theorem no_value_only_definedness_rule :
    ¬ ∃ D : Rat → Prop, ∀ S : Set Nat,
      D (totalizedValue S) ↔ S.Nonempty := by
  rintro ⟨D, hD⟩
  have hzero : D (totalizedValue ({0} : Set Nat)) :=
    (hD ({0} : Set Nat)).mpr ⟨0, by simp⟩
  have hempty : D (totalizedValue (∅ : Set Nat)) := by
    rw [empty_and_zero_same_value]
    exact hzero
  rcases (hD (∅ : Set Nat)).mp hempty with ⟨n, hn⟩
  exact hn

/-- A nonzero positive control guards against hard-coding the default value. -/
theorem three_spec_valid : MinimumValueSpec ({3} : Set Nat) (1 / 4 : Rat) := by
  refine ⟨3, by simp, ?_, ?_⟩
  · intro m hm
    have h : m = 3 := Set.mem_singleton_iff.mp hm
    subst m
    exact le_rfl
  · norm_num

theorem three_value_is_quarter : totalizedValue ({3} : Set Nat) = (1 / 4 : Rat) :=
  ((minimum_spec_iff_value ({3} : Set Nat) (1 / 4 : Rat)).mp three_spec_valid).2.symm

end MathGraph.Presupposition

#print axioms PaperCode.example_3_1
#print axioms MathGraph.Presupposition.minimum_spec_iff_nonempty
#print axioms MathGraph.Presupposition.minimum_spec_iff_value
#print axioms MathGraph.Presupposition.source_predicate_matches
#print axioms MathGraph.Presupposition.paper_minimum_is_zero
#print axioms MathGraph.Presupposition.paper_value_is_one
#print axioms MathGraph.Presupposition.paper_identity_and_missing_source
#print axioms MathGraph.Presupposition.identity_does_not_supply_source_witness
#print axioms MathGraph.Presupposition.empty_spec_invalid
#print axioms MathGraph.Presupposition.zero_spec_valid
#print axioms MathGraph.Presupposition.empty_and_zero_same_value
#print axioms MathGraph.Presupposition.no_value_only_definedness_rule
#print axioms MathGraph.Presupposition.three_value_is_quarter
