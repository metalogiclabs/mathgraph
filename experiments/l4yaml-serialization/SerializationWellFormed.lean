import L4YAML.Scanner.Scanner
import L4YAML.Parser.TokenParser

/-!
# SerializationWellFormed v1

Independent semantic state for the two stateful acceptance families identified
by the L4YAML grammar-completeness audit:

* anchor definitions / alias uses;
* %TAG declarations / named tag-handle uses.

The specification is deliberately not a wrapper around `scanFiltered` or
`parseStream`.  It is a small trace semantics with its own state and
well-formedness predicate.  Runtime-local bridge lemmas then show that the
actual scanner/parser guards implement the same decisions at their respective
boundaries.

This is the first brick toward:

  ExactSurfaceLanguage input ∧ SerializationWellFormed input
    ↔ InExecutableLanguage input

No `native_decide` is used in the generalized claims in this file.
-/

namespace L4YAMLSerializationWellFormed

open L4YAML

/-- Stateful serialization events, independent of scanner/parser state types. -/
inductive Event where
  | beginDocument
  | endDocument
  | defineAnchor (name : String)
  | useAlias (name : String)
  | declareTag (handle : String)
  | useTag (handle : String)
  deriving Repr, DecidableEq

/-- Minimal semantic environment needed by the two currently identified
stateful acceptance families. -/
structure Env where
  anchors : List String := []
  tagHandles : List String := []
  deriving Repr, Inhabited

def Env.reset (_ : Env) : Env := {}

/-- The handles that do not require an explicit %TAG declaration. -/
def BuiltinTagHandle (h : String) : Prop :=
  h = "" ∨ h = "!" ∨ h = "!!"

instance (h : String) : Decidable (BuiltinTagHandle h) := by
  unfold BuiltinTagHandle
  infer_instance

def AliasAllowed (env : Env) (name : String) : Prop :=
  name ∈ env.anchors

instance (env : Env) (name : String) : Decidable (AliasAllowed env name) := by
  unfold AliasAllowed
  infer_instance

def TagHandleAllowed (env : Env) (handle : String) : Prop :=
  BuiltinTagHandle handle ∨ handle ∈ env.tagHandles

instance (env : Env) (handle : String) : Decidable (TagHandleAllowed env handle) := by
  unfold TagHandleAllowed
  infer_instance

/-- Declarative trace well-formedness.

Document boundaries reset both environments.  A definition/declaration extends
the current document state; a use is permitted exactly when its corresponding
state condition holds. -/
def WellFormedFrom : Env → List Event → Prop
  | _, [] => True
  | env, .beginDocument :: rest =>
      WellFormedFrom env.reset rest
  | env, .endDocument :: rest =>
      WellFormedFrom env.reset rest
  | env, .defineAnchor name :: rest =>
      WellFormedFrom { env with anchors := name :: env.anchors } rest
  | env, .useAlias name :: rest =>
      AliasAllowed env name ∧ WellFormedFrom env rest
  | env, .declareTag handle :: rest =>
      WellFormedFrom { env with tagHandles := handle :: env.tagHandles } rest
  | env, .useTag handle :: rest =>
      TagHandleAllowed env handle ∧ WellFormedFrom env rest

def SerializationWellFormed (events : List Event) : Prop :=
  WellFormedFrom {} events

/-- Executable checker for the independent semantic specification.
It exists to prove decidability/completeness of the trace relation; it is not
defined in terms of L4YAML's scanner/parser. -/
def checkFrom : Env → List Event → Bool
  | _, [] => true
  | env, .beginDocument :: rest =>
      checkFrom env.reset rest
  | env, .endDocument :: rest =>
      checkFrom env.reset rest
  | env, .defineAnchor name :: rest =>
      checkFrom { env with anchors := name :: env.anchors } rest
  | env, .useAlias name :: rest =>
      if _h : AliasAllowed env name then checkFrom env rest else false
  | env, .declareTag handle :: rest =>
      checkFrom { env with tagHandles := handle :: env.tagHandles } rest
  | env, .useTag handle :: rest =>
      if _h : TagHandleAllowed env handle then checkFrom env rest else false

/-- Family-level correctness of the independent semantic checker. -/
lemma checkFrom_correct (env : Env) (events : List Event) :
    checkFrom env events = true ↔ WellFormedFrom env events := by
  induction events generalizing env with
  | nil =>
      simp [checkFrom, WellFormedFrom]
  | cons e rest ih =>
      cases e <;> simp [checkFrom, WellFormedFrom, ih]

lemma serializationWellFormed_iff_check (events : List Event) :
    SerializationWellFormed events ↔ checkFrom {} events = true := by
  simpa [SerializationWellFormed] using (checkFrom_correct (env := ({} : Env)) events).symm

/-! ## Scope laws: independent semantic consequences -/

lemma define_then_use_alias (env : Env) (name : String) (rest : List Event) :
    WellFormedFrom env (.defineAnchor name :: .useAlias name :: rest) ↔
      WellFormedFrom { env with anchors := name :: env.anchors } rest := by
  simp [WellFormedFrom, AliasAllowed]

lemma undeclared_alias_rejected (env : Env) (name : String)
    (h : name ∉ env.anchors) (rest : List Event) :
    ¬ WellFormedFrom env (.useAlias name :: rest) := by
  simp [WellFormedFrom, AliasAllowed, h]

lemma declare_then_use_tag (env : Env) (handle : String) (rest : List Event) :
    WellFormedFrom env (.declareTag handle :: .useTag handle :: rest) ↔
      WellFormedFrom { env with tagHandles := handle :: env.tagHandles } rest := by
  simp [WellFormedFrom, TagHandleAllowed]

lemma undeclared_named_tag_rejected (env : Env) (handle : String)
    (h_builtin : ¬ BuiltinTagHandle handle)
    (h_decl : handle ∉ env.tagHandles)
    (rest : List Event) :
    ¬ WellFormedFrom env (.useTag handle :: rest) := by
  simp [WellFormedFrom, TagHandleAllowed, h_builtin, h_decl]

lemma document_reset_forgets_anchor (env : Env) (name : String) (rest : List Event) :
    WellFormedFrom env
      (.defineAnchor name :: .endDocument :: .beginDocument :: .useAlias name :: rest) →
      False := by
  intro h
  simpa [WellFormedFrom, AliasAllowed, Env.reset] using h

lemma document_reset_forgets_custom_tag (env : Env) (handle : String)
    (h_builtin : ¬ BuiltinTagHandle handle) (rest : List Event) :
    WellFormedFrom env
      (.declareTag handle :: .endDocument :: .beginDocument :: .useTag handle :: rest) →
      False := by
  intro h
  simpa [WellFormedFrom, TagHandleAllowed, Env.reset, h_builtin] using h

/-! ## Runtime bridge: scanner alias guard -/

/-- Projection of exactly the alias-relevant part of the scanner state into
our independent semantic environment. -/
def ofScannerAliases (s : L4YAML.Scanner.ScannerState) : Env :=
  { anchors := s.definedAnchors.toList }

/-- The scanner's family-level alias guard agrees with the independent
specification: an alias name is accepted exactly when it is in the semantic
anchor environment. -/
lemma scanner_alias_guard_exact (s : L4YAML.Scanner.ScannerState) (name : String) :
    s.definedAnchors.any (fun x => x == name) = true ↔
      AliasAllowed (ofScannerAliases s) name := by
  simp [AliasAllowed, ofScannerAliases, Array.mem_iff_getElem]

/-! ## Runtime bridge: parser tag-handle guard -/

/-- Projection of exactly the tag-relevant part of parser state. -/
def ofParserTags (ps : L4YAML.TokenParser.ParseState) : Env :=
  { tagHandles := ps.tagHandles.toList.map Prod.fst }

/-- Boolean form of the guard implemented inside `parseNodeProperties`.
Built-in handles need no declaration; every other handle must occur in the
per-document tag-handle environment. -/
def parserTagGuard (ps : L4YAML.TokenParser.ParseState) (handle : String) : Bool :=
  (handle == "") || (handle == "!") || (handle == "!!") ||
    ps.tagHandles.any (fun p => p.1 == handle)

/-- Presence of a named handle in the parser's richer handle→prefix table
is exactly presence of that handle in the minimal semantic projection.  The
prefix is intentionally discarded: it affects tag resolution, but not the
accept/reject decision for declaration well-formedness. -/
lemma parser_declared_handle_exact
    (ps : L4YAML.TokenParser.ParseState) (handle : String) :
    ps.tagHandles.any (fun p => p.1 == handle) = true ↔
      handle ∈ ps.tagHandles.toList.map Prod.fst := by
  constructor
  · rw [Array.any_eq_true]
    rintro ⟨i, hi, hname⟩
    apply List.mem_map.mpr
    exact ⟨ps.tagHandles[i], by simpa using Array.getElem_mem hi, hname⟩
  · intro h
    rw [Array.any_eq_true]
    obtain ⟨entry, hmem, hname⟩ := List.mem_map.mp h
    have hmem' : entry ∈ ps.tagHandles := by simpa using hmem
    rw [Array.mem_iff_getElem] at hmem'
    obtain ⟨i, hi, heq⟩ := hmem'
    exact ⟨i, hi, by simpa [heq] using hname⟩

/-- The parser's tag-handle decision agrees with the independent semantic
specification for every parser state and handle. -/
lemma parser_tag_guard_exact (ps : L4YAML.TokenParser.ParseState) (handle : String) :
    parserTagGuard ps handle = true ↔
      TagHandleAllowed (ofParserTags ps) handle := by
  simp only [parserTagGuard, Bool.or_eq_true, beq_iff_eq,
    TagHandleAllowed, BuiltinTagHandle, ofParserTags]
  rw [parser_declared_handle_exact]
  simp [or_assoc]

end L4YAMLSerializationWellFormed

#print axioms L4YAMLSerializationWellFormed.checkFrom_correct
#print axioms L4YAMLSerializationWellFormed.scanner_alias_guard_exact
#print axioms L4YAMLSerializationWellFormed.parser_tag_guard_exact
