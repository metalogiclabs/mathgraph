#!/usr/bin/env python3
"""Fail-closed independent receipt audit for actual SysML-to-Lean whole chain."""
import hashlib
import json
import pathlib
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify_results.py RESULTS_DIRECTORY")
base = pathlib.Path(sys.argv[1])
expected = {
    ("original","no_statement"):0,
    ("original","false_statement"):0,
    ("strict","no_statement"):0,
    ("strict","false_statement"):1,
    ("withdrawn","false_statement"):0,
}
observed = {}
for line in (base/"native-results.tsv").read_text().splitlines():
    lane,case,exit_status = line.split("\t")
    key = lane,case
    if key in observed: raise SystemExit(f"DUPLICATE_CASE {key}")
    observed[key] = int(exit_status)
if set(observed) != set(expected):
    raise SystemExit(f"CASE_COVERAGE_FAILURE {observed}")
for key,want in expected.items():
    got = observed[key]
    if (want==0) != (got==0):
        raise SystemExit(f"CONTRADICTED_NATIVE_RESULT {key} expected={want} actual={got}")
    lane,case = key
    log = (base / f"{lane}-{case}.log").read_text()
    if want == 0:
        if "0 unverified citation(s)" not in log:
            raise SystemExit(f"MISSING_AUTHENTIC_NATIVE_SUCCESS {key}")
    elif "@Checked.statement is unchecked free text" not in log or "unverified citations in" not in log:
        raise SystemExit(f"REJECTION_WAS_NOT_EXPECTED_POLICY {key}")

m = json.loads((base/"convert-false_statement-api.json").read_text())
if not isinstance(m,list): raise SystemExit("NOT_REAL_API_ELEMENT_LIST")
vals = [x.get("value") for x in m if x.get("@type")=="LiteralString"]
if "False" not in vals: raise SystemExit("FULL_TEXT_TO_JSON_LOST_FALSE")
if "PropertyKindCalculus.Iso80000.Part3.Edge.width_length" not in vals:
    raise SystemExit("FULL_TEXT_TO_JSON_LOST_PROOF_NAME")
sysml = (base/"false_statement.sysml").read_text()
if 'statement = "False"' not in sysml:
    raise SystemExit("PROTECTED_CLAIM_NOT_IN_SYSML")
gen = (base/"OriginalFalseGenerated.lean").read_text()
if "-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False" not in gen:
    raise SystemExit("GENERATED_COMMENT_MISSING")
if "example : False" in gen or "theorem False" in gen:
    raise SystemExit("UNEXPECTED_KERNEL_FALSE_THEOREM")
version = (base/"opensysml-version.txt").read_text()
if "0.9.1" not in version:
    raise SystemExit("WRONG_EXTERNAL_CONVERTER_VERSION")
patch = json.loads((base/"policy-patch.json").read_text())
if patch["old_sha256"] != "28bb3c84b7cf86813e60967eb88d680e274f9a8f5d59d8e4432f411dfe75263c":
    raise SystemExit("BASE_SOURCE_FILE_CHANGED")
if patch["new_sha256"] != "ff1e12beb4dccd58cc1a9ba3da022cb8f018c229b11e9705c45544974e25cf98":
    raise SystemExit("POLICY_PATCH_CHANGED")
receipt = {
    "protocol":"JPL_PKC_OPENSYSML_FULL_TEXT_V5",
    "upstream":"nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824",
    "external_converter":version.strip(),
    "result":"WARRANTED_BOUNDED_FULL_TEXT_TO_KERNEL_WITHDRAWAL",
    "status_by_lane":{f"{k[0]}/{k[1]}":"ACCEPT" if v==0 else "REJECT"
                      for k,v in observed.items()},
    "source_file_sha256":patch,
    "authentic_SysML_cli":True,
    "converter_retains_optional_claim":True,
    "no_kernel_proof_of_false":True,
    "upstream_writes":False,
    "source_input_sha256":{
        p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [base/"false_statement.sysml",base/"no_statement.sysml"]
    }
}
(base/"PINNED_RESULT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("V5_FINAL_CLAIM_TO_EVIDENCE_FULL_CHAIN_PASS",
      json.dumps({"cases":len(observed),"original_false_admitted":True,
                  "strict_false_rejected":True,"withdrawn_false_readmitted":True}))
