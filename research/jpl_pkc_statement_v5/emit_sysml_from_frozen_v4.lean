import PropertyKindCalculus.Interchange
import PropertyKindCalculus.Iso80000.Part3

open Lean PropertyKindCalculus.Interchange

/-! Emit the two frozen V4 neutral models through JPL's real SysML DSL emitter.
The output is used UNCHANGED by external OpenSysML 0.9.1. -/

run_meta do
  let base := ".lake/build/sysml/claim-audit-v4"
  for caseId in ["no_statement", "false_statement"] do
    let raw ← IO.FS.readFile s!"{base}/{caseId}.api.json"
    let .ok (m, warnings) := ApiJson.read raw
      | throwError "V5_API_JSON_READ_FAILED: {caseId}"
    unless warnings.isEmpty do
      throwError "V5_API_JSON_WARNINGS: {caseId}: {warnings}"
    let some k := m.kind? "width"
      | throwError "V5_WIDTH_MISSING: {caseId}"
    let expected := if caseId == "false_statement" then some "False" else none
    unless k.checked.any (fun c => c.statement == expected) do
      throwError "V5_SOURCE_STATEMENT_MISSING: {caseId}"
    let rendered := EmitSysml.emit m
    if caseId == "false_statement" &&
       (rendered.splitOn "statement = \"False\"").length <= 1 then
      throwError "V5_EMITTED_SYSML_LOST_FALSE_STATEMENT"
    let out := s!"{base}/{caseId}.sysml"
    IO.FS.writeFile out rendered
    IO.println s!"V5_SOURCE_SYSML_READY: {caseId}, bytes={rendered.utf8ByteSize}"
