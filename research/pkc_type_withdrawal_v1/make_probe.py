#!/usr/bin/env python3
"""Generate lane-specific assertion wrapper from EXACT V6 interpretation bytes.

No lane changes tokenExpr / interpret / declaration / classify. In particular, an
unexpected observed status is never used to regenerate or adapt the interpreter.
"""
import argparse
import hashlib
from pathlib import Path

V6_GIT_BLOB = "88914d5c6cd38dc55ffe555d11320f15aeb88bfe"
CASES = ("typed_match", "false_mismatch", "typed_mismatch",
         "wrong_citation", "unsupported", "true_unsupported", "no_statement")
BASE_WITNESS = """example : PropertyKindCalculus.Iso80000.Part3.Edge
    PropertyKindCalculus.Iso80000.Part3.width.kind
    PropertyKindCalculus.Iso80000.Part3.length.kind :=
  .width_length
"""
MUTANT_WITNESS = """example : PropertyKindCalculus.Iso80000.Part3.Edge
    PropertyKindCalculus.Iso80000.Part3.width.kind
    PropertyKindCalculus.Iso80000.Part3.height.kind :=
  .width_length

example : PropertyKindCalculus.Iso80000.Part3.Edge
    PropertyKindCalculus.Iso80000.Part3.width.kind
    PropertyKindCalculus.Iso80000.Part3.length.kind :=
  .width_length_original
"""
def make(original: Path, output: Path, lane: str):
    src = original.read_text()
    import subprocess
    actual = subprocess.check_output(["git", "hash-object", str(original)], text=True).strip()
    assert actual == V6_GIT_BLOB, f"V6 source blob changed: {actual}"
    before = src.index("-- Native kernel witness, authored independently")
    parser_start = src.index("private def tokenExpr")
    parser_end = src.index("private def expected")
    assert before < parser_start < parser_end
    method_bytes = src[parser_start:parser_end].encode()
    assert "private def classify" in method_bytes.decode()
    assert "withTransparency .all" in method_bytes.decode()
    assert "isDefEq term ci.type" in method_bytes.decode()
    assert "getConstInfo declName" in method_bytes.decode()
    prefix = src[:before] + src[parser_start:parser_end]
    witness = MUTANT_WITNESS if lane == "MUTANT" else BASE_WITNESS
    case_literal = "[" + ", ".join(f'"{x}"' for x in CASES) + "]"
    suffix = f"""
-- This assertion witness must be checked by the ACTUAL Lean kernel in each lane.
{witness}
run_meta do
  let cases := {case_literal}
  for c in cases do
    let raw ← IO.FS.readFile s!".lake/build/sysml/typed-v1/{{c}}.api.json"
    let .ok (model, warnings) := ApiJson.read raw
      | throwError "V7_NATIVE_API_READ_FAILED: {{c}}"
    unless warnings.isEmpty do
      throwError "V7_NATIVE_API_WARNINGS: {{c}}"
    let some kind := model.kind? "width"
      | throwError "V7_MISSING_WIDTH: {{c}}"
    let [citation] := kind.checked
      | throwError "V7_NOT_EXACTLY_ONE_CITATION: {{c}}"
    let outcome ← classify citation.decl citation.statement
    IO.println s!"V7_TYPE_RESULT lane={lane} case={{c}} status={{outcome}} decl={{citation.decl}}"
  IO.println "V7_NATIVE_V6_EXACT_INTERPRETATION_PASS lane={lane} count=7"

end MathGraphPKCTypedV1
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(prefix + suffix)
    print("V7_V6_INTERPRETATION_COPIED_UNCHANGED", hashlib.sha256(method_bytes).hexdigest(),
          "source_git_blob", actual, "lane", lane)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--v6-check", required=True, type=Path)
    p.add_argument("--lane", required=True, choices=["BASE", "MUTANT", "RESTORED"])
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    make(a.v6_check, a.out, a.lane)
