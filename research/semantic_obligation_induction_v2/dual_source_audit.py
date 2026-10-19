#!/usr/bin/env python3
"""Read-only post-result audit of two independently archived, prospectively selected
source-native V2 cases. This validates receipts; it does NOT independently rerun
the pinned upstream implementations or invent any semantic relation.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

METHOD="0f5bf46ba92723f294fbdfcff42a4cc6fe7ad9b9"
CASES={
    "tomliw": {
        "repo":"hukkin/tomli-w",
        "sha":"1210bb6f5708a4dc084cc3deb4a3a3e3939f4d6d",
        "native_tests":271,
        "native_skips":2,
        "required":["external-semantics"],
        "artifact_id":12171145856,
        "run":39219102534,
        "head":"ef113f185c998ce7913e5fae3e8d0bdcd01ee0ac",
    },
    "tomlkit": {
        "repo":"python-poetry/tomlkit",
        "sha":"eddd27e43a62fe58707c311bfad2f52e72493f53",
        "native_tests":1203,
        "native_skips":0,
        "required":["external-semantics","native-roundtrip"],
        "artifact_id":12170863639,
        "run":39219770458,
        "head":"c30e8f8ffaec0b0e996cbecbf7a963de3ed1d9bf",
    },
}

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def load(root,name):
    file=root/name
    return json.loads(file.read_bytes())

def native_counts(xml):
    doc=ET.fromstring(xml)
    tests=doc.findall(".//testcase")
    if doc.tag=="testsuite":
        tests=list(doc.findall("./testcase"))
    errors=sum(1 for t in tests if t.find("error") is not None)
    failures=sum(1 for t in tests if t.find("failure") is not None)
    skipped=sum(1 for t in tests if t.find("skipped") is not None)
    return {"tests":len(tests),"errors":errors,"failures":failures,"skipped":skipped}

def assert_semantic_obligation(item, name):
    assert item["id"]==name
    assert item["relation"]==("independent_parse(writer(mapping)) == mapping" if
                             name=="external-semantics" else "reader(writer(mapping)) == mapping")
    assert item["verdict"]==("WARRANTED_BOUNDED_INDEPENDENT" if
                            name=="external-semantics" else "WARRANTED_BOUNDED_NATIVE_CONSISTENCY")
    observations=item["observations"]
    assert len(observations)==3
    assert [x["sample_index"] for x in observations]==[0,1,2]
    for x in observations:
        assert x["same_typed_meaning"] is True
        assert x["false_claim_rejected"] is True
        assert x["encoded_type"]=="str"

def validate(root, tag, md, source, candidate, expert, counts):
    expected=CASES[tag]
    assert md["method_freeze_commit"]==METHOD
    assert md["repository"]==expected["repo"]
    assert md["source_sha"]==source["source_sha"]==expected["sha"]
    assert md["no_fallback"] is True
    assert md["selected_ordinal"]==1
    assert md["pool"][0]==expected["repo"]
    assert source["status"]=="PROSPECTIVE_EXECUTED_BOUNDED"
    assert source["native"]["passed"] is True
    assert source["native"]["errors"]==source["native"]["failures"]==0
    assert source["native"]=={"tests":expected["native_tests"],"errors":0,
                               "failures":0,"skipped":expected["native_skips"],"passed":True}
    assert counts=={"tests":expected["native_tests"],"errors":0,
                    "failures":0,"skipped":expected["native_skips"]}
    assert candidate["arm"]=="candidate" and expert["arm"]=="expert"
    assert candidate["source_sha"]==expert["source_sha"]==expected["sha"]
    assert candidate["api_sha256"]==expert["api_sha256"]
    assert candidate["format"]==expert["format"]==source["format"]=="toml"
    assert candidate["status"]==expert["status"]=="CANDIDATE_PENDING_INDEPENDENT_NATIVE_VERIFICATION"
    assert candidate["obligations"]==expert["obligations"]
    assert [x["id"] for x in candidate["obligations"]]==expected["required"]
    for x in candidate["obligations"]:
        assert x["writer"]=="dumps"
        if x["id"]=="external-semantics":
            assert x["reader"] is None and x["oracle"]=="tomllib.loads"
        else:
            assert x["reader"]=="loads"
    assert source["candidate_proposal_file_sha256"]==sha256((root/"native-evidence/candidate.json").read_bytes())
    assert source["expert_proposal_file_sha256"]==sha256((root/"native-evidence/expert.json").read_bytes())
    assert source["native_junit_sha256"]==sha256((root/"native-evidence/native-junit.xml").read_bytes())
    digest_lines=(root/"native-evidence/pre-native-proposals.sha256").read_text().splitlines()
    actual={}
    for line in digest_lines:
        digest, file=line.split(maxsplit=1)
        actual[file]=digest
    assert actual=={
        "native-evidence/candidate.json":source["candidate_proposal_file_sha256"],
        "native-evidence/expert.json":source["expert_proposal_file_sha256"],
    }
    assert (root/"native-evidence/native-exit-code.txt").read_text().strip()=="0"
    assert source["comparison"]["advantage"]==0
    assert source["comparison"]["candidate_warranted_independent"]==1
    assert source["comparison"]["expert_warranted_independent"]==1
    assert source["comparison"]["baseline_type"]=="predeclared expert-authored cookbook, not a recruited external reviewer"
    for arm,proposal in (("candidate",candidate),("expert",expert)):
        entries=source[arm]["obligations"]
        assert [x["id"] for x in entries]==expected["required"]
        for item in entries:
            assert_semantic_obligation(item,item["id"])
    assert source["candidate"]["obligations"]==source["expert"]["obligations"]
    return {"source":md["repository"],"sha":md["source_sha"],"method":METHOD,
            "native_tests":counts,"positive_obligations":expected["required"],
            "independent_fixture_observations":3,"baseline":"TIE",
            "run":expected["run"],"head":expected["head"],
            "artifact_id":expected["artifact_id"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--second",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    records={}
    for tag,root in (("tomliw",a.first),("tomlkit",a.second)):
        md=load(root,"research/semantic_obligation_induction_v2/SELECTED_SOURCE.json")
        source=load(root,"native-evidence/qualified-claims.json")
        candidate=load(root,"native-evidence/candidate.json")
        expert=load(root,"native-evidence/expert.json")
        counts=native_counts((root/"native-evidence/native-junit.xml").read_bytes())
        records[tag]=validate(root,tag,md,source,candidate,expert,counts)
        # Independent fail-closed receipt forgery tests: no status string is trusted.
        for mutation in ("false_semantics","failed_native","source_rebind","baseline_advantage"):
            m=copy.deepcopy(source)
            d=copy.deepcopy(md)
            if mutation=="false_semantics":
                m["candidate"]["obligations"][0]["observations"][0]["same_typed_meaning"]=False
            elif mutation=="failed_native":
                m["native"]["failures"]=1
            elif mutation=="source_rebind":
                d["source_sha"]="0"*40
            else:
                m["comparison"]["advantage"]=1
            try:
                validate(root,tag,d,m,candidate,expert,counts)
            except AssertionError:
                continue
            raise AssertionError(f"FORGED_PACKET_ADMITTED: {tag}/{mutation}")
    assert records["tomliw"]["source"]!=records["tomlkit"]["source"]
    assert records["tomliw"]["sha"]!=records["tomlkit"]["sha"]
    assert records["tomliw"]["method"]==records["tomlkit"]["method"]==METHOD
    receipt={
      "status":"WARRANTED_BOUNDED_PROSPECTIVE_SECOND_SOURCE_API_OBLIGATION_REUSE",
      "method_freeze_commit":METHOD,
      "two_distinct_sources":records,
      "native_runtimes_included":True,
      "both_positive_on_exact_same_three_typed_semantic_fixtures":True,
      "adversarial_forgery_rejections":8,
      "expert_rule_baseline":"TIE on both; a separately implemented cookbook, not an independent human expert",
      "preserved_v1_negative":"uiri/toml alias-observation grammar no-applicability and separate stdin pytest collection apparatus failure",
      "first_v2_and_second_v2_used_identical_method_blobs":True,
      "cross_project_scope":"Two separate TOML implementations, same format and finite human-authored relation family",
      "unknowns":["autonomous observation language invention","human-expert/agent superiority",
                  "general proof of TOML semantics","semantics outside three fixed fixtures",
                  "physical change-sensitive requalification in these two TOML packages"],
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("TWO_SOURCE_UNCHANGED_OBLIGATION_METHOD_EVIDENCE_AUDIT_PASS")
    print("ADVERSARIAL_FORGED_EVIDENCE_REJECTED count=8")
    print(json.dumps({x:records[x]["native_tests"] for x in records},sort_keys=True))

if __name__=="__main__":
    main()
