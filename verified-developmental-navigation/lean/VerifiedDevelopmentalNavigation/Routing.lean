import VerifiedDevelopmentalNavigation

namespace VerifiedDevelopmentalNavigation

/-!
# Verified routing kernel

This file formalizes the smallest next-move law used by the developmental
navigator.  A live hypothesis cell induces three mutually ordered possibilities:

1. ACT when one action is lawful in every surviving world;
2. otherwise PROBE when an admitted question partitions the cell so that each
   possible outcome admits a common lawful action;
3. otherwise EXTEND_QUESTIONS: no currently admitted question can do that.

The third case is deliberately relative to the declared admitted probe family.
It does not claim that no useful question exists globally.
-/

structure DecisionProblem (H P A O : Type) where
  observe : P → H → O
  lawful : H → A → Prop

namespace DecisionProblem

variable {H P A O : Type} (D : DecisionProblem H P A O)

/-- A live hypothesis cell is represented extensionally as a predicate. -/
abbrev Cell := H → Prop

/-- An action is immediately safe when it is lawful in every surviving world. -/
def CommonLawful (cell : Cell (H := H)) (a : A) : Prop :=
  ∀ h : H, cell h → D.lawful h a

/-- The controller may ACT exactly when some common lawful action exists. -/
def CanAct (cell : Cell (H := H)) : Prop :=
  ∃ a : A, D.CommonLawful cell a

/-- The outcome subcell induced by asking `p` and observing `o`. -/
def OutcomeCell (cell : Cell (H := H)) (p : P) (o : O) : Cell (H := H) :=
  fun h => cell h ∧ D.observe p h = o

/-- A probe resolves the current commitment defect in one step when every
possible outcome subcell admits a common lawful action.  Empty outcome cells are
harmless: any action witnesses them vacuously. -/
def Resolves (cell : Cell (H := H)) (p : P) : Prop :=
  ∀ o : O, ∃ a : A, D.CommonLawful (D.OutcomeCell cell p o) a

/-- Whether the currently admitted probe family contains a resolving question. -/
def CanProbe (admitted : P → Prop) (cell : Cell (H := H)) : Prop :=
  ∃ p : P, admitted p ∧ D.Resolves cell p

/-- The exact relative obstruction that licenses development of the question
language: action is not yet safe and the admitted probes cannot resolve it. -/
def NeedsQuestionExtension (admitted : P → Prop) (cell : Cell (H := H)) : Prop :=
  ¬ D.CanAct cell ∧ ¬ D.CanProbe admitted cell

inductive Route where
  | act
  | probe
  | extendQuestions
  deriving DecidableEq, Repr

/-- Declarative routing specification.  Priority is important: if immediate
safe action exists, the navigator acts instead of gathering unnecessary data. -/
def RouteSpec (admitted : P → Prop) (cell : Cell (H := H)) : Route → Prop
  | .act => D.CanAct cell
  | .probe => ¬ D.CanAct cell ∧ D.CanProbe admitted cell
  | .extendQuestions => D.NeedsQuestionExtension admitted cell

/-- The three routing cases are logically exhaustive. -/
theorem route_complete (admitted : P → Prop) (cell : Cell (H := H)) :
    D.RouteSpec admitted cell .act ∨
    D.RouteSpec admitted cell .probe ∨
    D.RouteSpec admitted cell .extendQuestions := by
  classical
  by_cases hact : D.CanAct cell
  · exact Or.inl hact
  · by_cases hprobe : D.CanProbe admitted cell
    · exact Or.inr (Or.inl ⟨hact, hprobe⟩)
    · exact Or.inr (Or.inr ⟨hact, hprobe⟩)

/-- ACT soundness: an ACT route contains an action certified lawful in every
surviving world. -/
theorem act_sound {admitted : P → Prop} {cell : Cell (H := H)}
    (h : D.RouteSpec admitted cell .act) :
    ∃ a : A, ∀ w : H, cell w → D.lawful w a :=
  h

/-- PROBE soundness: a PROBE route provides an admitted question whose every
possible outcome leaves a cell with some common lawful action. -/
theorem probe_sound {admitted : P → Prop} {cell : Cell (H := H)}
    (h : D.RouteSpec admitted cell .probe) :
    ∃ p : P, admitted p ∧
      ∀ o : O, ∃ a : A,
        ∀ w : H, cell w ∧ D.observe p w = o → D.lawful w a := by
  rcases h with ⟨_, p, hp, hres⟩
  exact ⟨p, hp, hres⟩

/-- EXTEND_QUESTIONS is a certified *relative* obstruction: neither immediate
safe action nor any admitted resolving probe exists. -/
theorem extend_questions_sound {admitted : P → Prop} {cell : Cell (H := H)}
    (h : D.RouteSpec admitted cell .extendQuestions) :
    (¬ ∃ a : A, ∀ w : H, cell w → D.lawful w a) ∧
    (¬ ∃ p : P, admitted p ∧ D.Resolves cell p) :=
  h

/-- Any probe that resolves an EXTEND_QUESTIONS state is necessarily outside the
currently admitted family.  This is the minimal necessity theorem behind
question-language extension. -/
theorem resolving_probe_must_be_new
    {admitted : P → Prop} {cell : Cell (H := H)}
    (hneed : D.NeedsQuestionExtension admitted cell)
    {p : P} (hres : D.Resolves cell p) :
    ¬ admitted p := by
  intro hp
  exact hneed.2 ⟨p, hp, hres⟩

/-- Admitting a genuinely resolving new probe closes the question-language
obstruction, while making no claim that ACT is already safe before observing
its outcome. -/
theorem extension_closes_probe_obstruction
    {admitted : P → Prop} {cell : Cell (H := H)}
    {p : P} (hres : D.Resolves cell p) :
    D.CanProbe (fun q => admitted q ∨ q = p) cell := by
  exact ⟨p, Or.inr rfl, hres⟩

end DecisionProblem

end VerifiedDevelopmentalNavigation
