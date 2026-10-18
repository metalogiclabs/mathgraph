import PropertyKindCalculus.Interchange
import PropertyKindCalculus.Iso80000.Part3

open Lean PropertyKindCalculus.Interchange

/-!
  This *checks* the real PKC interchange citation verifier, not Lean's kernel.
  Input claims and controls frozen in PROTOCOL.md before source execution.
-/

def mkClaimAuditModel (decl : String) (statement : Option String) : PkcModel :=
  { packageName := "ClaimAudit",
    kinds := [{
      name := "width", id := "width", scale := .ratio,
      checked := [{ decl := decl, statement := statement }]
    }] }

run_meta do
  let citation : String := "PropertyKindCalculus.Iso80000.Part3.Edge.width_length"
  let env ← getEnv
  let n := ``PropertyKindCalculus.Iso80000.Part3.Edge.width_length
  let some ci := env.find? n
    | throwError "FAIL_CLOSED_REFERENCE_MISSING: PKC specialization ctor"
  let actual ← Meta.ppExpr ci.type
  IO.println s!"ACTUAL_DECL_TYPE: {actual}"

  -- Positive: real proposition constructor recognized as evidence.
  let good ← Harvest.unverifiedCitations (mkClaimAuditModel citation none)
  unless good.isEmpty do
    throwError "FAIL_CLOSED_GOOD_PROOF_CITATION_REJECTED: {good}"

  -- Negative controls must reject absent, data and axiom declarations.
  let missing ← Harvest.unverifiedCitations
    (mkClaimAuditModel "No.Such.PKC.Declaration" none)
  if missing.isEmpty then
    throwError "FAIL_CLOSED_MISSING_DECLARATION_ACCEPTED"
  let data ← Harvest.unverifiedCitations (mkClaimAuditModel "Nat.add" none)
  if data.isEmpty then
    throwError "FAIL_CLOSED_DATA_AS_PROOF_ACCEPTED"
  let axiom ← Harvest.unverifiedCitations (mkClaimAuditModel "propext" none)
  if axiom.isEmpty then
    throwError "FAIL_CLOSED_AXIOM_AS_PROOF_ACCEPTED"
  IO.println "CONTROL_PASS: valid_proposition; missing_declaration_rejected; data_rejected; axiom_rejected"

  -- Source-selected falsifier. The optional metadata declares a claim that is
  -- *not* the type of the genuine cited constructor.
  let falseModel := mkClaimAuditModel citation (some "False")
  let falseReceipt ← Harvest.unverifiedCitations falseModel
  let trueReceipt ← Harvest.unverifiedCitations
    (mkClaimAuditModel citation (some "True"))
  IO.println s!"FALSE_STATEMENT_ISSUES={repr falseReceipt}"
  IO.println s!"TRUE_STATEMENT_ISSUES={repr trueReceipt}"

  let code := EmitLean.emit falseModel
  if (code.splitOn "False").length <= 1 then
    throwError "FAIL_CLOSED_FORGED_METADATA_NOT_EMITTED"
  IO.FS.createDirAll ".lake/build/sysml/Generated"
  IO.FS.writeFile ".lake/build/sysml/Generated/ClaimAudit.lean" code
  IO.println "GENERATED_FILE=.lake/build/sysml/Generated/ClaimAudit.lean"

  if falseReceipt.isEmpty && trueReceipt.isEmpty then
    IO.println "CANDIDATE_UNCHECKED_STATEMENT_METADATA: forged textual statement accepted at PKC citation gate"
  else
    IO.println "NO_UNCHECKED_STATEMENT_CANDIDATE: importer distinguished supplied statements"
