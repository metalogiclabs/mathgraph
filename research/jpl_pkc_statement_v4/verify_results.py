#!/usr/bin/env python3
"""Post-hoc verifier of *actual* PKC native ingest CLI outcomes.

Rejects apparatus failures in place of correctly caused citation rejection.
Requires physical policy withdrawal to recover the originally admitted case.
"""
import argparse
import hashlib
import json
from pathlib import Path

CASES = (
    "no_statement", "false_statement", "true_statement",
    "missing_declaration", "data_citation", "axiom_citation",
)
EXPECTED = {
    "original": {
        "no_statement": True, "false_statement": True, "true_statement": True,
        "missing_declaration": False, "data_citation": False, "axiom_citation": False,
    },
    "strict": {
        "no_statement": True, "false_statement": False, "true_statement": False,
        "missing_declaration": False, "data_citation": False, "axiom_citation": False,
    },
    "withdrawn": {"false_statement": True},
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tsv", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--pin", type=str, required=True)
    args = p.parse_args()
    assert args.pin == "e0deb453e05ffa63297d9704ceb47d0855193824"
    evidence = args.tsv.parent
    observed = {}
    for raw in args.tsv.read_text().splitlines():
        lane, case, exitcode = raw.split("\t")
        ident = (lane, case)
        if ident in observed:
            raise RuntimeError("DUPLICATE_NATIVE_CASE " + repr(ident))
        observed[ident] = int(exitcode) == 0
    expected = {(lane, case): value
                for lane, cases in EXPECTED.items()
                for case, value in cases.items()}
    if observed != expected:
        raise RuntimeError(f"NATIVE_BEHAVIOUR_MISMATCH expected={expected} actual={observed}")
    for (lane, case), admitted in expected.items():
        log = evidence / f"{lane}-{case}.log"
        source = log.read_text(encoding="utf-8")
        if not source:
            raise RuntimeError(f"MISSING_NATIVE_LOG {lane}/{case}")
        if admitted:
            if "unverified citations in" in source:
                raise RuntimeError(f"INCONSISTENT_ACCEPTED_REPORT {lane}/{case}")
            if "0 unverified citation(s)" not in source:
                raise RuntimeError(f"NOT_AN_ACTUAL_INGEST_SUCCESS {lane}/{case}")
        else:
            if "unverified citations in" not in source:
                raise RuntimeError(f"REJECTED_BY_HARNESS_NOT_JPL_INGEST {lane}/{case}")
            if lane == "strict" and case in ("false_statement", "true_statement"):
                if "@Checked.statement is unchecked free text" not in source:
                    raise RuntimeError(f"STRICT_REASON_NOT_PRESERVED {lane}/{case}")
            if case == "missing_declaration" and "is not a declaration" not in source:
                raise RuntimeError(f"MISSING_DECL_REASON_WRONG {lane}/{case}")
            if case == "data_citation" and "not evidence" not in source and "is data" not in source:
                raise RuntimeError(f"DATA_DECL_REASON_WRONG {lane}/{case}")
            if case == "axiom_citation" and "is an axiom" not in source and "theorem" not in source:
                raise RuntimeError(f"AXIOM_DECL_REASON_WRONG {lane}/{case}")

    genfile = evidence / "OriginalFalseComment.lean"
    generated = genfile.read_text()
    if "-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False" not in generated:
        raise RuntimeError("FALSE_STATEMENT_COMMENT_MISSING")
    if "theorem False" in generated or "example : False" in generated:
        raise RuntimeError("UNEXPECTED_PROOF_OF_FALSE")
    if not (evidence / "original-generated-lean.log").exists():
        raise RuntimeError("MISSING_COMPILE_REPLAY")

    patchinfo = json.loads((evidence / "strict-patch-receipt.json").read_text())
    if patchinfo["changed_files"] != [
       "interchange/PropertyKindCalculus/Interchange/Harvest.lean"
    ]:
        raise RuntimeError("PATCH_OUT_OF_SCOPE")
    for case in CASES:
        assert (evidence / "frozen-api-inputs" / (case + ".api.json")).exists()
    receipt = {
       "protocol":"JPL_PKC_STATEMENT_INGEST_V4",
       "source":"nasa-jpl/PropertyKindCalculus",
       "source_sha":args.pin,
       "authority":"actual scripts/ingest-sysml.lean on independently generated OpenSysML-shaped API-element JSON, not external SysML text conversion",
       "case_count":len(observed),
       "result":"WARRANTED_BOUNDED_CAUSAL_FAIL_CLOSED_POLICY",
       "previous_policy":"accepts authentic checked declaration cited with optional False or True metadata",
       "strict_policy":"rejects unchecked optional textual statements and preserves existing data/axiom/missing-declaration controls",
       "withdrawal":"restores original False-statement admission",
       "observed":{f"{lane}/{case}":"ACCEPT" if outcome else "REJECT"
                    for (lane,case),outcome in sorted(observed.items())},
       "patch_receipt":patchinfo,
       "fixture_sha256":{
           c:hashlib.sha256((evidence/"frozen-api-inputs"/(c+".api.json")).read_bytes()).hexdigest()
           for c in CASES
       },
       "no_kernel_false_proof":True,
       "OpenSysML_cli_executed":False,
       "upstream_mutation":False,
    }
    args.result.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("V4_INDEPENDENT_NATIVE_AUDIT_PASS "+json.dumps({
       "cases":len(observed),
       "original_false_admitted":observed[("original","false_statement")],
       "strict_false_rejected":not observed[("strict","false_statement")],
       "withdrawn_false_readmitted":observed[("withdrawn","false_statement")],
       "good_citation_preserved":observed[("strict","no_statement")]
    }))

if __name__ == "__main__":
    main()
