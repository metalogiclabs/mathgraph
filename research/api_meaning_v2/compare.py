#!/usr/bin/env python3
"""Adjudicate pinned native tests, independent stdlib reader and equal-information baseline."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path

FIELDS=("accepted","strict_matches","strict_counterexamples","canonical_supported",
        "canonical_counterexamples","reference_supported","reference_counterexamples",
        "reference_distinct_outputs","reference_has_container",
        "reference_perturbation_rejections","strict_verdict","normal_form_verdict",
        "reference_verdict")
SAMPLE=("index","encoder","strict","normal_form","reference","negative_json")

def read_tests(path):
    if not path.is_file():return {"status":"UNKNOWN_NATIVE_MISSING_JUNIT"}
    root=ET.parse(path).getroot()
    cases=list(root.iter("testcase"))
    errors=sum(t.find("error") is not None or t.find("failure") is not None for t in cases)
    skipped=sum(t.find("skipped") is not None for t in cases)
    return {"status":"NATIVE_PASS" if cases and not errors else "UNKNOWN_NATIVE_ERRORS_OR_ZERO",
            "total":len(cases),"errors":errors,"skipped":skipped}

def main():
    ap=argparse.ArgumentParser()
    for name in ("proposal","baseline","native-junit","selected","out"):ap.add_argument("--"+name,required=True)
    p=ap.parse_args()
    candidate=json.loads(Path(p.proposal).read_text())
    expert=json.loads(Path(p.baseline).read_text())
    metadata=json.loads(Path(p.selected).read_text())
    assert candidate["protocol"]=="API_MEANING_V2"
    assert expert["protocol"]=="EQUAL_INFO_EXPERT_RULE_V2"
    assert metadata["sha"]==candidate["source_sha"]==expert["source_sha"]
    native=read_tests(Path(p.native_junit))
    cand={x["id"]:x for x in candidate["results"]}
    expt={x["id"]:x for x in expert["results"]}
    rows=[]
    for name in sorted(set(cand)|set(expt)):
        a,b=cand.get(name),expt.get(name)
        match=a is not None and b is not None
        if match:
            match=all(a[x]==b[x] for x in FIELDS)
            match=match and len(a["samples"])==len(b["samples"])
            if match:
                match=all(all(a0[k]==b0[k] for k in SAMPLE)
                          for a0,b0 in zip(a["samples"],b["samples"]))
        rows.append({"id":name,"matched":bool(match),
                     "candidate_reference":a["reference_verdict"] if a else "MISSING",
                     "baseline_reference":b["reference_verdict"] if b else "MISSING",
                     "candidate_canonical":a["normal_form_verdict"] if a else "MISSING",
                     "candidate_strict":a["strict_verdict"] if a else "MISSING",
                     "reference_supported":a["reference_supported"] if a else 0,
                     "reference_counterexamples":a["reference_counterexamples"] if a else 0,
                     "source_native_accepted":a["accepted"] if a else 0})
    agreement=bool(rows) and all(x["matched"] for x in rows)
    reference_ok=any(x["candidate_reference"]=="WARRANTED_BOUNDED_JSON_SUBSET" for x in rows)
    ref_failed=any(x["candidate_reference"]=="REJECTED_BOUNDED" for x in rows)
    if native["status"]!="NATIVE_PASS":state="UNKNOWN_NATIVE"
    elif not rows:state="UNKNOWN_NO_ELIGIBLE_PUBLIC_API_PAIR"
    elif not agreement:state="UNKNOWN_EXPERT_RULE_CONFLICT"
    elif ref_failed:state="REJECTED_BOUNDED_INDEPENDENT_REFERENCE"
    elif reference_ok:state="WARRANTED_BOUNDED_JSON_CORRESPONDENCE_WITH_BASELINE_TIE"
    else:state="UNKNOWN_NO_INDEPENDENT_INTERPRETATION"
    out={"protocol":"API_MEANING_PROSPECTIVE_V2","selected":metadata,
         "frozen_method_sha":metadata["frozen_method_sha"],"native":native,
         "candidate_pairs":rows,"qualification":state,
         "baseline_advantage":"NONE_CLAIMED",
         "bounds":"Independent standard-library JSON semantics, finite seed set and mutable-codec fresh instances only; native authored suite is additional authority.",
         "semantic_grammar_autonomously_invented":False,
         "human_or_agent_comparison_completed":False}
    dest=Path(p.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("PROSPECTIVE_V2_RESULT",state)
    print("NATIVE",json.dumps(native,sort_keys=True))
    print("MATCHED",json.dumps(rows,sort_keys=True))
if __name__=="__main__":main()
