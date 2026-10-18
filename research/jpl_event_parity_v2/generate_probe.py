#!/usr/bin/env python3
"""Build a deterministic Lean comparison program from frozen, public inputs.

No discovery/search occurs at execution time. All cases are loaded from the
committed source-controlled JSON; source and corpus SHAs are logged by CI.
"""
import argparse
import hashlib
import json
from pathlib import Path

UPSTREAM = "bca37392fdcb80481342a186a37ab37a5ede6e46"

PROGRAM = r"""
import L4YAML.Output.EventsIx
import L4YAML.Parser.Composition

/-!
  This checks parser/event observational parity only on frozen finite inputs.
  It is NOT a Lean theorem of general YAML 1.2.2 conformance.
-/

def auditSuccess {ε α : Type} (x : Except ε α) : Bool :=
  match x with
  | .ok _ => true
  | .error _ => false

def auditDetectOutputMismatch (a b : String) : Bool := a != b

def auditCorpus : Array (String × String × String) := #[ 
__CASES__
]

def main : IO Unit := do
  -- Required controls ensuring the comparison observer isn't vacuous.
  if !auditDetectOutputMismatch "GOOD" "MUTANT" then
    throw (IO.userError "SELF_CONTROL_FAILURE: mismatch mutant not detected")
  if auditDetectOutputMismatch "GOOD" "GOOD" then
    throw (IO.userError "SELF_CONTROL_FAILURE: identical outputs considered unequal")

  let mut count : Nat := 0
  let mut accept : Nat := 0
  let mut reject : Nat := 0
  let mut expectedChecks : Nat := 0
  let mut parityDifferences : Nat := 0
  let mut normativeDifferences : Nat := 0
  let mut firstAccept : String := ""
  let mut firstReject : String := ""
  for (ident, expected, yaml) in auditCorpus do
    let raw := L4YAML.TokenParser.parseYamlRaw yaml
    let marked := L4YAML.Events.parseYamlRawMarked yaml
    let withComments := L4YAML.TokenParser.parseYamlWithComments yaml
    let ixRaw := L4YAML.TokenParser.Indexed.parseYamlRawIx yaml
    let ixMarked := L4YAML.Events.parseYamlRawMarkedIx yaml
    let ixComments := L4YAML.TokenParser.Indexed.parseYamlWithCommentsIx yaml
    let events := L4YAML.Events.streamToEvents yaml
    let ixEvents := L4YAML.Events.streamToEventsIx yaml
    let baseline := auditSuccess raw
    let observations := #[
       auditSuccess marked, auditSuccess withComments, auditSuccess ixRaw,
       auditSuccess ixMarked, auditSuccess ixComments, auditSuccess events,
       auditSuccess ixEvents
    ]
    count := count + 1
    if baseline then
      accept := accept + 1
      if firstAccept == "" then firstAccept := ident
    else
      reject := reject + 1
      if firstReject == "" then firstReject := ident
    if observations.any (fun x => x != baseline) then
      parityDifferences := parityDifferences + 1
      IO.println s!"PARITY_STATUS_MISMATCH id={ident} baseline={baseline} others={repr observations} yaml={repr yaml}"

    match raw, marked with
    | .ok l, .ok r =>
        if l.size != r.size then
          parityDifferences := parityDifferences + 1
          IO.println s!"PARITY_MARKER_COUNT_MISMATCH id={ident} raw={l.size} marked={r.size} yaml={repr yaml}"
    | _, _ => pure ()
    match ixRaw, ixMarked with
    | .ok l, .ok r =>
        if l.size != r.size then
          parityDifferences := parityDifferences + 1
          IO.println s!"PARITY_INDEXED_MARKER_COUNT_MISMATCH id={ident} raw={l.size} marked={r.size} yaml={repr yaml}"
    | _, _ => pure ()
    match raw, ixRaw with
    | .ok l, .ok r =>
        if l.size != r.size then
          parityDifferences := parityDifferences + 1
          IO.println s!"PARITY_DOCUMENT_COUNT_MISMATCH id={ident} legacy={l.size} indexed={r.size} yaml={repr yaml}"
    | _, _ => pure ()
    match events, ixEvents with
    | .ok l, .ok r =>
        if auditDetectOutputMismatch l r then
          parityDifferences := parityDifferences + 1
          IO.println s!"PARITY_EVENT_BYTES_MISMATCH id={ident} legacy={repr l} indexed={repr r} yaml={repr yaml}"
    | _, _ => pure ()

    if expected != "unknown" then
      expectedChecks := expectedChecks + 1
      let wanted := expected == "accept"
      if baseline != wanted then
        normativeDifferences := normativeDifferences + 1
        IO.println s!"SCOPED_SPEC_CANDIDATE id={ident} expected={expected} actual={baseline} yaml={repr yaml}"

  IO.println s!"AUDIT_SUMMARY checked={count} legacy_accept={accept} legacy_reject={reject} semantic_controls={expectedChecks} parity_mismatches={parityDifferences} scoped_spec_candidates={normativeDifferences} mutant_detected=true"
  if count != __NCASES__ then
    throw (IO.userError s!"FAIL_CLOSED_WRONG_CORPUS_COUNT actual={count}")
  if expectedChecks < 7 || accept == 0 || reject == 0 then
    throw (IO.userError "FAIL_CLOSED_VACUOUS_CASES")
  if parityDifferences != 0 || normativeDifferences != 0 then
    throw (IO.userError s!"CANDIDATE_DIVERGENCES require independent source/spec adjudication: parity={parityDifferences} normative={normativeDifferences}")
"""

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = args.corpus.read_bytes()
    data = json.loads(raw)
    assert data["upstream_sha"] == UPSTREAM
    assert data["protocol"] == "L4YAML_EVENT_PARITY_REFUTE_FIRST_V2"
    entries = data["cases"]
    assert len(entries) >= 700, len(entries)
    ids = [c["id"] for c in entries]
    assert len(ids) == len(set(ids))
    assert len({c["yaml"] for c in entries}) == len(entries)
    assert sum(c["expected"] != "unknown" for c in entries) >= 7
    for case in entries:
        assert case["expected"] in ("unknown", "accept", "reject")
        assert all(isinstance(case[x], str) for x in ("id", "yaml", "expected"))
    def lean(s: str) -> str:
        # JSON has the same quotes, slash escapes and ASCII control escapes
        # as a Lean string; non-ASCII (BOM) stays literal UTF-8.
        return json.dumps(s, ensure_ascii=False)
    rows = ",\n".join(
        "  (" + lean(c["id"]) + ", " + lean(c["expected"]) + ", " + lean(c["yaml"]) + ")"
        for c in entries
    )
    source = PROGRAM.replace("__CASES__", rows).replace("__NCASES__", str(len(entries)))
    args.out.write_text(source, encoding="utf-8")
    print(json.dumps({
        "cases": len(entries),
        "normative_controls": sum(c["expected"] != "unknown" for c in entries),
        "corpus_sha256": hashlib.sha256(raw).hexdigest(),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    }))

if __name__ == "__main__":
    main()
