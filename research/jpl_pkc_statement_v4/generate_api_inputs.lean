import PropertyKindCalculus.Tests.Interchange.ApiJson
import PropertyKindCalculus.Iso80000.Part3

open Lean PropertyKindCalculus.Interchange
open PropertyKindCalculus.Tests.Interchange.ApiJson

/-!
V4: predeclared OpenSysML API-JSON element-shaped fixtures, using the JPL
test fixture's real constructors, parsed by JPL's real ApiJson.read.
The six emitted .api.json inputs are then passed to the *unchanged*
scripts/ingest-sysml.lean, and again through a tightly scoped proposed policy.
This is NOT execution of the external OpenSysML command line converter.
-/

namespace MathGraphPKCIngestV4

def validDeclaration : String :=
  "PropertyKindCalculus.Iso80000.Part3.Edge.width_length"

def makeFixture (decl : String) (statement : Option String) : String :=
  let pkcLib : List Json :=
    library ++ [lib "K_Checked_statement" "AttributeUsage" "statement"]
  let elements : List Json :=
    [ el "M" "Package" [("declaredName", Json.str "M"),
                         ("qualifiedName", Json.str "M")],
      el "M__width" "ReferenceUsage"
        [("declaredName", Json.str "width"), ("owner", ref "M"),
         ("ownedRelationship", Json.arr #[ref "M__width_mu"])],
      el "M__width_mu" "MetadataUsage"
        [("owner", ref "M__width"), ("type", Json.arr #[ref "K_Kind"])],
      el "M__width_chk" "MetadataUsage"
        [("owner", ref "M__width"), ("type", Json.arr #[ref "K_Checked"])] ]
  let fields : List Json :=
    binding "M__width" "KOP_id" "id"
      (litStr "M__width__id_v" "width") true
    ++ binding "M__width" "KOP_scale" "scale"
      (fre "M__width__scale_v" "ST_ratio") true
    ++ binding "M__width_chk" "K_Checked_decl" "decl"
      (litStr "M__width_chk__decl_v" decl)
  let statementField : List Json :=
    match statement with
    | none => []
    | some st =>
        binding "M__width_chk" "K_Checked_statement" "statement"
          (litStr "M__width_chk__statement_v" st)
  (Json.arr (pkcLib ++ elements ++ fields ++ statementField).toArray).compress

run_meta do
  let cases : List (String × String × Option String) := [
    ("no_statement", validDeclaration, none),
    ("false_statement", validDeclaration, some "False"),
    ("true_statement", validDeclaration, some "True"),
    ("missing_declaration", "No.Such.PKC.Declaration", none),
    ("data_citation", "Nat.add", none),
    ("axiom_citation", "propext", none)
  ]
  let output := ".lake/build/sysml/claim-audit-v4"
  IO.FS.createDirAll output
  let mut count := 0
  for (label, decl, statement) in cases do
    let content := makeFixture decl statement
    let .ok (model, warnings) := ApiJson.read content
      | throwError "API_JSON_PARSING_FAILED: {label}"
    unless warnings.isEmpty do
      throwError "API_JSON_WARNINGS_NOT_EMPTY: {label}: {warnings}"
    unless model.kinds.length == 1 do
      throwError "API_JSON_WRONG_KIND_COUNT: {label}: {model.kinds.length}"
    let some width := model.kind? "width"
      | throwError "API_JSON_MISSING_WIDTH: {label}"
    let expected : List Checked := [{ decl, statement }]
    unless width.checked == expected do
      throwError "API_JSON_CITATION_MISMATCH: {label}: {repr width.checked}"
    let roundTrip := PkcModel.ofJsonString model.toJsonString
    unless roundTrip == .ok model do
      throwError "API_JSON_PIVOT_ROUNDTRIP_FAILED: {label}"
    let target := s!"{output}/{label}.api.json"
    IO.FS.writeFile target content
    count := count + 1
    IO.println s!"API_JSON_CASE_READY={label} path={target} checked={repr width.checked}"
  unless count == 6 do throwError "FAIL_CLOSED_CASE_COUNT: {count}"
  IO.println s!"API_JSON_FIXTURE_GENERATION_PASS: cases={count}"

end MathGraphPKCIngestV4
