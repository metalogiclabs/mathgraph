import PropertyKindCalculus.Interchange
import PropertyKindCalculus.Iso80000.Part3

open Lean Meta PropertyKindCalculus PropertyKindCalculus.Interchange

/-!
An expressly interpreted miniature source language. This is NOT a general
natural-language parser. All tokens map to independent original-source values.
-/
namespace MathGraphPKCTypedV1

private def widthK : KindOfProperty := PropertyKindCalculus.Iso80000.Part3.width.kind
private def lengthK : KindOfProperty := PropertyKindCalculus.Iso80000.Part3.length.kind
private def heightK : KindOfProperty := PropertyKindCalculus.Iso80000.Part3.height.kind

-- Native kernel witness, authored independently of the unchecked SysML comment.
example : PropertyKindCalculus.Iso80000.Part3.Edge
    PropertyKindCalculus.Iso80000.Part3.width.kind
    PropertyKindCalculus.Iso80000.Part3.length.kind :=
  .width_length

private def tokenExpr : String → Option Expr
  | "width" => some (mkConst ``widthK)
  | "length" => some (mkConst ``lengthK)
  | "height" => some (mkConst ``heightK)
  | _ => none

private def interpret : String → Option Expr
  | "False" => some (mkConst ``False)
  | text =>
    match text.splitOn "(" with
    | ["PKC:Edge", suffix] =>
      match suffix.splitOn ")" with
      | [args, ""] =>
        match args.splitOn "," with
        | [a,b] =>
          match tokenExpr a, tokenExpr b with
          | some left, some right =>
            some <| mkAppN (mkConst ``PropertyKindCalculus.Iso80000.Part3.Edge)
              #[left, right]
          | _, _ => none
        | _ => none
      | _ => none
    | _ => none

private def declaration : String → Option Name
  | "PropertyKindCalculus.Iso80000.Part3.Edge.width_length" =>
    some ``PropertyKindCalculus.Iso80000.Part3.Edge.width_length
  | "PropertyKindCalculus.Iso80000.Part3.Edge.height_length" =>
    some ``PropertyKindCalculus.Iso80000.Part3.Edge.height_length
  | _ => none

private def classify (decl : String) (st : Option String) : MetaM String := do
  let some st := st | return "NO_ASSERTION"
  let some term := interpret st | return "UNKNOWN_UNSUPPORTED"
  let some declName := declaration decl | return "UNKNOWN_DECLARATION"
  let ci ← getConstInfo declName
  let matched ← withTransparency .all do
    isDefEq term ci.type
  return if matched then "MATCH" else "MISMATCH"

private def expected : String → Option String
  | "typed_match" => some "MATCH"
  | "false_mismatch" => some "MISMATCH"
  | "typed_mismatch" => some "MISMATCH"
  | "wrong_citation" => some "MISMATCH"
  | "unsupported" => some "UNKNOWN_UNSUPPORTED"
  | "true_unsupported" => some "UNKNOWN_UNSUPPORTED"
  | "no_statement" => some "NO_ASSERTION"
  | _ => none

run_meta do
  let cases := ["typed_match", "false_mismatch", "typed_mismatch",
    "wrong_citation", "unsupported", "true_unsupported", "no_statement"]
  let folder := ".lake/build/sysml/typed-v1"
  for c in cases do
    let raw ← IO.FS.readFile s!"{folder}/{c}.api.json"
    let .ok (model,warnings) := ApiJson.read raw
      | throwError "PKC_V6_NATIVE_API_READ_FAILED: {c}"
    unless warnings.isEmpty do
      throwError "PKC_V6_NATIVE_API_WARNINGS: {c}"
    let some kind := model.kind? "width"
      | throwError "PKC_V6_WIDTH_NOT_PRESENT: {c}"
    let [citation] := kind.checked
      | throwError "PKC_V6_NOT_SINGLE_CITATION: {c}"
    let outcome ← classify citation.decl citation.statement
    let some want := expected c
      | throwError "PKC_V6_UNREGISTERED_CASE: {c}"
    unless outcome == want do
      throwError "PKC_V6_MISCLASSIFIED: {c}: got {outcome}; expected {want}"
    IO.println s!"PKC_V6_TYPED_RESULT case={c} status={outcome} decl={citation.decl} statement={repr citation.statement}"
  IO.println "PKC_V6_PINNED_TYPED_CORRESPONDENCE_MATRIX_PASS count=7"

end MathGraphPKCTypedV1
