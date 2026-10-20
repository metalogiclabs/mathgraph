#!/usr/bin/env python3
"""V6.1 *apparatus-only* adapter. Never alters V6 frozen source or scientific proposals.

Explicitly binds independently pinned source metadata to original V6 output,
then runs the original V6 evaluator at its immutable SHA. Fail closed.
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys

FROZEN_V6="dfcc088ca6f4a280272c361e043dd0f49afa1b5b"

def bind(meta, proposal):
    assert re.fullmatch("[0-9a-f]{40}", meta["source_sha"]), "UNPINNED_SOURCE"
    assert meta["repository"] and "/" in meta["repository"], "NO_REPOSITORY"
    assert proposal.get("status") in ("SOURCE_DOC_EXAMPLE_CANDIDATES",
                                       "UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE",
                                       "UNKNOWN_SCAN_BUDGET","UNKNOWN_NO_API"), "UNSUPPORTED_PROPOSAL"
    assert isinstance(proposal.get("obligations"),list) and isinstance(proposal.get("api"),dict)
    assert proposal["api"].get("module"), "MISSING_IMPORT_MODULE"
    assert isinstance(proposal.get("files"),dict), "MISSING_SOURCE_FILES"
    # Source metadata is *not* a scientific claim, just a verified provenance binder.
    forbidden={"repository","source_sha"} & set(proposal)
    if forbidden:
        assert all(proposal[k]==meta[k] for k in forbidden), "SOURCE_BINDING_CONFLICT"
    ret={**proposal,"repository":meta["repository"],"source_sha":meta["source_sha"],
         "apparatus_binding":"SOURCE_PINNED_METADATA_V6_1"}
    return ret

def main():
    p=argparse.ArgumentParser()
    for x in ("metadata","proposals","source","native_junit","evaluator","out","bound_proposals"):
        p.add_argument("--"+x.replace("_","-"),type=pathlib.Path,required=True)
    a=p.parse_args()
    meta=json.loads(a.metadata.read_text())
    original=json.loads(a.proposals.read_text())
    bound=bind(meta,original)
    a.bound_proposals.parent.mkdir(parents=True,exist_ok=True)
    a.bound_proposals.write_text(json.dumps(bound,sort_keys=True,indent=2)+"\n")
    command=[sys.executable,str(a.evaluator),"--metadata",str(a.metadata),
             "--proposals",str(a.bound_proposals),"--source",str(a.source),
             "--native-junit",str(a.native_junit),"--out",str(a.out)]
    subprocess.run(command,check=True)
    receipt=json.loads(a.out.read_text())
    assert receipt["source"]["repository"]==meta["repository"]
    assert receipt["source"]["source_sha"]==meta["source_sha"]
    assert receipt["proposals_sha256"]==hashlib.sha256(a.bound_proposals.read_bytes()).hexdigest()
    assert receipt["native_junit_sha256"]==hashlib.sha256(a.native_junit.read_bytes()).hexdigest()
    if not original["obligations"]:
        assert receipt["status"]=="UNKNOWN_NO_APPLICABLE_DOC_EXAMPLES"
        assert receipt["comparison"]=="INCONCLUSIVE_ZERO_CLAIMS"
        assert receipt["candidate_source_doc_warrants"]==0
    print("V6_1_EVALUATOR_SCHEMA_BOUND_AND_EXECUTED",receipt["status"],receipt["comparison"])

if __name__=="__main__":
    main()
