#!/usr/bin/env python3
"""Finite bounded comparison of independent API-obligation proposal vs informed rule."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path

def native(path):
    if not path.is_file():return {"status":"UNKNOWN_NATIVE_NO_JUNIT"}
    root=ET.parse(path).getroot()
    suites=[root] if root.tag=="testsuite" else root.findall(".//testsuite")
    # In nested suite XML, count only suites with direct testcase children to prevent double-counting.
    actual=[test for suite in suites for test in suite.findall("./testcase")]
    failures=sum(bool(t.find("failure") is not None or t.find("error") is not None)
                 for t in actual)
    skips=sum(t.find("skipped") is not None for t in actual)
    return {"status":"NATIVE_PASS" if actual and failures==0 else "UNKNOWN_NATIVE_FAILURE_OR_ZERO",
            "tests":len(actual),"failures":failures,"skips":skips}

def compare(a,b):
    aa={x["id"]:x for x in a["results"]}
    bb={x["id"]:x for x in b["results"]}
    rows=[]
    for key in sorted(set(aa)|set(bb)):
        l=aa.get(key);r=bb.get(key)
        if l and r:
            la=[(x["index"],x["result"]) for x in l["samples"]]
            rb=[(x["index"],x["result"]) for x in r["samples"]]
            match=(l["status"]==r["status"] and l["accepted"]==r["accepted"]
                   and l["counterexamples"]==r["counterexamples"] and la==rb)
        else: match=False
        rows.append({"id":key,"generator_status":l["status"] if l else "MISSING",
                     "expert_rule_status":r["status"] if r else "MISSING",
                     "matched":match,
                     "generator_accepted":l["accepted"] if l else 0,
                     "generator_counterexamples":l["counterexamples"] if l else 0})
    return rows

def main():
    p=argparse.ArgumentParser()
    for n in ("proposal","baseline","native-junit","selected-source","output"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args()
    proposal=json.loads(Path(a.proposal).read_text())
    expert=json.loads(Path(a.baseline).read_text())
    selected=json.loads(Path(a.selected_source).read_text())
    assert selected["sha"]==proposal["selected_sha"]==expert["selected_sha"]
    assert proposal["grammar"]=="API_OBLIGATION_V1" and expert["protocol"]=="INFORMED_EXPERT_RULE_BASELINE_V1"
    rows=compare(proposal,expert)
    orig=native(Path(a.native_junit))
    supported=bool(rows) and any(x["generator_accepted"]>0 for x in rows)
    agreement=bool(rows) and all(r["matched"] for r in rows)
    gate=("UNKNOWN_NATIVE" if orig["status"]!="NATIVE_PASS" else
          "UNKNOWN_NO_APPLICABLE_PROPOSAL" if not supported else
          "UNKNOWN_COMPARATOR_DISAGREEMENT" if not agreement else
          "WARRANTED_BOUNDED_FINITE_OBLIGATION_INSTANTIATION")
    result={
        "protocol":"API_OBLIGATION_PROSPECTIVE_V1",
        "source":selected,"native":orig,"proposals":rows,
        "selected_observation_grammar":"exact type-and-value reversible API name pair only",
        "qualification":gate,
        "comparative_advantage":"NOT_CLAIMED: equality or difference against a deterministic human-authored rule is not a human/agent cost comparison",
        "source_adaptation":False,
        "method_changed_after_open":False,
        "no_general_semantic_acquisition_claim":True
    }
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("PROSPECTIVE_QUALIFICATION",gate)
    print("MATCHED_COMPARATOR",json.dumps(rows,sort_keys=True))
    print("NATIVE_TESTS",json.dumps(orig,sort_keys=True))
if __name__=="__main__": main()
