import L4YAML.Surface.Basic
import SerializationWellFormed

/-!
# Source-event lexemes for SerializationWellFormed

This module moves the semantic specification one layer closer to raw input
without calling the L4YAML scanner or token parser.

It defines small, independent character-list recognizers for the four source
lexemes that create the state relevant to `SerializationWellFormed`:

* `&name`  -> defineAnchor
* `*name`  -> useAlias
* `%TAG !h! ...` -> declareTag
* `!h!suffix` -> useTag

The recognizers intentionally operate on `List Char` and the YAML character
predicates only.  They are not a second YAML parser and are not yet claimed to
find every semantic occurrence inside an arbitrary YAML document.  The point
of this layer is to pin the *local source meaning* independently, so that the
remaining whole-input traversal problem is isolated from the semantic-state
problem.

All generalized lemmas below are ordinary kernel proofs; no `native_decide`.
-/

namespace L4YAMLSerializationSourceEvents

open L4YAML
open L4YAML.CharPredicates
open L4YAML.Surface
open L4YAMLSerializationWellFormed

/-- Boolean spelling of the surface grammar's anchor-name character class. -/
def isAnchorCharBool (c : Char) : Bool :=
  decide (isNsAnchorChar c)

/-- Independent maximal-prefix splitter. -/
def spanWhile (p : Char → Bool) : List Char → List Char × List Char
  | [] => ([], [])
  | c :: cs =>
      if p c then
        let (front, back) := spanWhile p cs
        (c :: front, back)
      else
        ([], c :: cs)

/-- Drop source horizontal whitespace. -/
def dropHSpace : List Char → List Char
  | ' ' :: cs => dropHSpace cs
  | '\t' :: cs => dropHSpace cs
  | cs => cs

/-- Parse an anchor definition or alias use at the *current source position*.
The returned remainder begins immediately after the anchor name. -/
def anchorEventAt : List Char → Option (Event × List Char)
  | '&' :: cs =>
      let (name, rest) := spanWhile isAnchorCharBool cs
      if name.isEmpty then none
      else some (.defineAnchor (String.ofList name), rest)
  | '*' :: cs =>
      let (name, rest) := spanWhile isAnchorCharBool cs
      if name.isEmpty then none
      else some (.useAlias (String.ofList name), rest)
  | _ => none

/-- Parse a *custom named* tag use `!h!suffix` at the current source
position. Builtin `!`, `!!`, and verbatim `!<...>` forms do not create a
well-formedness obligation and therefore return `none` here. -/
def namedTagUseAt : List Char → Option (Event × List Char)
  | '!' :: '<' :: _ => none
  | '!' :: '!' :: _ => none
  | '!' :: cs =>
      let (body, rest) := spanWhile isWordCharBool cs
      match body, rest with
      | [], _ => none
      | _, '!' :: suffix =>
          some (.useTag ("!" ++ String.ofList body ++ "!"), suffix)
      | _, _ => none
  | _ => none

/-- Parse a custom named handle declaration from a `%TAG` directive at the
current source position.  Prefix contents are irrelevant to the declaration
accept/reject state, so this projection deliberately stops after the handle. -/
def namedTagDeclarationAt : List Char → Option (Event × List Char)
  | '%' :: 'T' :: 'A' :: 'G' :: cs =>
      let cs := dropHSpace cs
      match cs with
      | '!' :: afterBang =>
          let (body, rest) := spanWhile isWordCharBool afterBang
          match body, rest with
          | [], _ => none
          | _, '!' :: tail =>
              some (.declareTag ("!" ++ String.ofList body ++ "!"), tail)
          | _, _ => none
      | _ => none
  | _ => none

/-! ## Generic prefix algebra -/

lemma spanWhile_all (p : Char → Bool) (xs : List Char)
    (h : ∀ c ∈ xs, p c = true) :
    spanWhile p xs = (xs, []) := by
  induction xs with
  | nil => rfl
  | cons c cs ih =>
      have hc : p c = true := h c (by simp)
      have htail : ∀ d ∈ cs, p d = true := by
        intro d hd
        exact h d (by simp [hd])
      simp [spanWhile, hc, ih htail]

lemma spanWhile_append_stop (p : Char → Bool) (xs : List Char) (stop : Char)
    (tail : List Char)
    (hxs : ∀ c ∈ xs, p c = true)
    (hstop : p stop = false) :
    spanWhile p (xs ++ stop :: tail) = (xs, stop :: tail) := by
  induction xs with
  | nil =>
      simp [spanWhile, hstop]
  | cons c cs ih =>
      have hc : p c = true := hxs c (by simp)
      have htail : ∀ d ∈ cs, p d = true := by
        intro d hd
        exact hxs d (by simp [hd])
      simp [spanWhile, hc, ih htail]

/-! ## Family-level source recognition -/

lemma anchor_definition_source_exact
    (nameChars : List Char)
    (hne : nameChars ≠ [])
    (hchars : ∀ c ∈ nameChars, isAnchorCharBool c = true) :
    anchorEventAt ('&' :: nameChars) =
      some (.defineAnchor (String.ofList nameChars), []) := by
  simp [anchorEventAt, spanWhile_all isAnchorCharBool nameChars hchars, hne]

lemma alias_use_source_exact
    (nameChars : List Char)
    (hne : nameChars ≠ [])
    (hchars : ∀ c ∈ nameChars, isAnchorCharBool c = true) :
    anchorEventAt ('*' :: nameChars) =
      some (.useAlias (String.ofList nameChars), []) := by
  simp [anchorEventAt, spanWhile_all isAnchorCharBool nameChars hchars, hne]

lemma named_tag_use_source_exact
    (handleChars suffix : List Char)
    (hne : handleChars ≠ [])
    (hchars : ∀ c ∈ handleChars, isWordCharBool c = true) :
    namedTagUseAt ('!' :: (handleChars ++ '!' :: suffix)) =
      some (.useTag ("!" ++ String.ofList handleChars ++ "!"), suffix) := by
  have hbang : isWordCharBool '!' = false := by decide
  simp [namedTagUseAt,
    spanWhile_append_stop isWordCharBool handleChars '!' suffix hchars hbang,
    hne]

lemma named_tag_declaration_source_exact
    (handleChars tail : List Char)
    (hne : handleChars ≠ [])
    (hchars : ∀ c ∈ handleChars, isWordCharBool c = true) :
    namedTagDeclarationAt
        ('%' :: 'T' :: 'A' :: 'G' :: ' ' :: '!' ::
          (handleChars ++ '!' :: tail)) =
      some (.declareTag ("!" ++ String.ofList handleChars ++ "!"), tail) := by
  have hbang : isWordCharBool '!' = false := by decide
  simp [namedTagDeclarationAt, dropHSpace,
    spanWhile_append_stop isWordCharBool handleChars '!' tail hchars hbang,
    hne]

/-! ## Composition with the already-proved runtime guards

These lemmas are deliberately local: the source recognizer establishes which
semantic event/name a source lexeme denotes; the existing bridge establishes
that the runtime state makes exactly the same accept/reject decision for that
name.  No scanner/parser call appears in the source recognizers themselves.
-/

lemma source_alias_allowed_iff_scanner_guard
    (s : L4YAML.Scanner.ScannerState)
    (chars rest : List Char) (name : String)
    (hsrc : anchorEventAt chars = some (.useAlias name, rest)) :
    s.definedAnchors.any (fun x => x == name) = true ↔
      AliasAllowed (ofScannerAliases s) name := by
  exact scanner_alias_guard_exact s name

lemma source_named_tag_allowed_iff_parser_guard
    (ps : L4YAML.TokenParser.ParseState)
    (chars rest : List Char) (handle : String)
    (hsrc : namedTagUseAt chars = some (.useTag handle, rest)) :
    parserTagGuard ps handle = true ↔
      TagHandleAllowed (ofParserTags ps) handle := by
  exact parser_tag_guard_exact ps handle

end L4YAMLSerializationSourceEvents

#print axioms L4YAMLSerializationSourceEvents.spanWhile_all
#print axioms L4YAMLSerializationSourceEvents.alias_use_source_exact
#print axioms L4YAMLSerializationSourceEvents.named_tag_use_source_exact
#print axioms L4YAMLSerializationSourceEvents.source_alias_allowed_iff_scanner_guard
#print axioms L4YAMLSerializationSourceEvents.source_named_tag_allowed_iff_parser_guard
