import Presupposition

/-!
V3: source-bound, proof-carrying admission for the V2 minimum-value contract.

The cases below are *declared formal contracts*. Names referencing the PDF do
not supply independent natural-language interpretation approval. In
particular, an `Admission` proof certifies a mathematical claim relative to
`caseSet`, not that the PDF text was independently interpreted correctly.
No production MathGraph acceptance logic is changed.
-/

namespace MathGraph.SourceBoundAdmission

open MathGraph.Presupposition

/-- These are the only scopes in the bounded qualification corpus. -/
inductive Case where
  | paperPage15
  | singletonZero
  | singletonThree
  deriving DecidableEq, Repr

/-- The source predicate must be committed independently of the output. -/
def caseSet : Case → Set Nat
  | .paperPage15 => {n : Nat | PaperCode.B_e n}
  | .singletonZero => {0}
  | .singletonThree => {3}

/-- The return value is not allowed to define its own source-set semantics. -/
noncomputable def caseValue (c : Case) : Rat :=
  totalizedValue (caseSet c)

/-- Proof-carrying admission relative to the declared source specification.
    There is NO constructor accepting a Boolean flag, document link, or value
    alone. A term of this Prop requires evidence of membership and leastness. -/
structure Admission (c : Case) (r : Rat) : Prop where
  contract : MinimumValueSpec (caseSet c) r

/-- Admissibility of this value is equivalent to a real witness plus equality
    to the formal evaluator, not to arbitrary evidence metadata. -/
theorem admission_iff_witness_and_value (c : Case) (r : Rat) :
    Admission c r ↔ (caseSet c).Nonempty ∧ r = caseValue c := by
  constructor
  · rintro ⟨h⟩
    exact (minimum_spec_iff_value (caseSet c) r).mp h
  · intro h
    exact ⟨(minimum_spec_iff_value (caseSet c) r).mpr h⟩

theorem admission_requires_witness (c : Case) (r : Rat)
    (h : Admission c r) : (caseSet c).Nonempty :=
  ((admission_iff_witness_and_value c r).mp h).1

/-- No output and no metadata value can turn the paper's empty source set
    into a valid source contract. -/
theorem page15_rejected (r : Rat) : ¬ Admission .paperPage15 r := by
  intro h
  obtain ⟨n, hn⟩ := admission_requires_witness .paperPage15 r h
  exact paper_no_root_false n hn

/-- Positive controls require genuine proofs of source membership/leastness. -/
theorem singleton_zero_admitted : Admission .singletonZero (1 : Rat) := by
  exact ⟨zero_spec_valid⟩

theorem singleton_three_admitted : Admission .singletonThree (1 / 4 : Rat) := by
  exact ⟨three_spec_valid⟩

/-- Even when the original Lean identity is valid, source admission is not. -/
theorem verified_identity_without_source_admission :
    ((PaperCode.r_e + 1) ^ 2 = PaperCode.r_e ^ 2 + 2 * PaperCode.r_e + 1) ∧
      ¬ Admission .paperPage15 PaperCode.r_e := by
  exact ⟨PaperCode.example_3_1, page15_rejected PaperCode.r_e⟩

theorem page15_and_zero_same_value :
    caseValue .paperPage15 = caseValue .singletonZero := by
  change totalizedValue {n : Nat | PaperCode.B_e n} =
    totalizedValue ({0} : Set Nat)
  rw [paper_set_empty]
  exact empty_and_zero_same_value

/-- Not even an unlimited noncomputable classifier of the *returned value*
    alone can correctly decide admissibility across the declared source cases. -/
theorem no_value_only_case_admission :
    ¬ ∃ D : Rat → Prop, ∀ c : Case, D (caseValue c) ↔ Admission c (caseValue c) := by
  rintro ⟨D, hD⟩
  have hvalue : caseValue .singletonZero = (1 : Rat) := by
    change totalizedValue ({0} : Set Nat) = (1 : Rat)
    exact zero_value_is_one
  have hpositive : Admission .singletonZero (caseValue .singletonZero) := by
    rw [hvalue]
    exact singleton_zero_admitted
  have hdZero : D (caseValue .singletonZero) :=
    (hD .singletonZero).mpr hpositive
  have hdPaper : D (caseValue .paperPage15) := by
    rw [page15_and_zero_same_value]
    exact hdZero
  exact page15_rejected (caseValue .paperPage15) ((hD .paperPage15).mp hdPaper)

/-- Even True does not add a missing mathematical source witness. -/
theorem metadata_flag_cannot_admit_page15 (metadataFlag : Bool) :
    ¬ Admission .paperPage15 (if metadataFlag then 1 else 0) :=
  page15_rejected _

end MathGraph.SourceBoundAdmission

#print axioms MathGraph.SourceBoundAdmission.admission_iff_witness_and_value
#print axioms MathGraph.SourceBoundAdmission.admission_requires_witness
#print axioms MathGraph.SourceBoundAdmission.page15_rejected
#print axioms MathGraph.SourceBoundAdmission.singleton_zero_admitted
#print axioms MathGraph.SourceBoundAdmission.singleton_three_admitted
#print axioms MathGraph.SourceBoundAdmission.verified_identity_without_source_admission
#print axioms MathGraph.SourceBoundAdmission.page15_and_zero_same_value
#print axioms MathGraph.SourceBoundAdmission.no_value_only_case_admission
#print axioms MathGraph.SourceBoundAdmission.metadata_flag_cannot_admit_page15
