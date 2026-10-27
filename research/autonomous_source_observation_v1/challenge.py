#!/usr/bin/env python3
"""Seven synthetic changes to copies of authentic 19,915-case evidence.

Unchanged target passes. Mutated observations do NOT represent any real Qwen
migration defect. Strong, equally-informed conventional comparator must catch
all induced errors or reject their provenance.
"""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from conventional_baseline import compare

def fingerprint(data):return hashlib.sha256(data).hexdigest()
def challenge(evidence):
    evidence=Path(evidence)
    positive=compare(evidence)
    if positive["verdict"]!="BASELINE_TIE" or positive["total"]!=19915:
        raise AssertionError("MISSING_AUTHENTIC_CLEAN_POSITIVE")
    plans={
        "boolean_absence_wrong_one":(1,"absent",1),
        "negative_one_wrong_zero":(3,"absent",0),
        "length_wrong_zero":(4,"absent",0),
        "unsupported_implication_contract_wrong_zero":(0,"absent",0),
        "source_log_corrupted":(3,"absent",0),
        "deleted_case":(None,None,None),
        "reordered_case":(None,None,None),
        "forged_source_identity":(None,None,None)
    }
    results={"authentic_unmodified":"BASELINE_TIE"}
    for name,(idx,rule,wrong) in plans.items():
        with tempfile.TemporaryDirectory(prefix="mg-autonomous-challenge-") as tmp:
            temp=Path(tmp)
            shutil.copy2(evidence/"NATIVE_REPORT.json",temp/"NATIVE_REPORT.json")
            shutil.copy2(evidence/"observations.jsonl",temp/"observations.jsonl")
            report=json.loads((temp/"NATIVE_REPORT.json").read_text())
            values=[json.loads(line) for line in (temp/"observations.jsonl").read_text().splitlines()]
            if idx is not None:
                matching=[r for r in values if r["case"]==idx and
                          r["key"] not in r["row"] and len(r["row"])>=2 and
                          (r["probe"] or idx==0)]
                if not matching:raise AssertionError("NO_PREDECLARED_SEPARATING_OBSERVATION:"+name)
                candidate=matching[0]
                if name=="source_log_corrupted":
                    # Correct C absence result was -1; inject a wrong result.
                    if candidate["source"]!=-1:raise AssertionError("INCORRECT_BASELINE_INPUT")
                    candidate["source"]=0
                else:
                    if candidate["target"]==wrong:raise AssertionError("INEFFECTUAL_MUTATION")
                    candidate["target"]=wrong
            elif name=="deleted_case":
                values.pop(12)
            elif name=="reordered_case":
                values[2],values[3]=values[3],values[2]
            elif name=="forged_source_identity":
                report["source_and_target"][0]["source_blob"]="0"*40
            data="".join(json.dumps(row,sort_keys=True)+"\n" for row in values).encode()
            (temp/"observations.jsonl").write_bytes(data)
            # Deliberately update the receipt hash too. The independent
            # checker must reject semantic falsity, not only stale hashes.
            report["observations_sha256"]=fingerprint(data)
            (temp/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
            try:
                result=compare(temp)
                verdict=result["verdict"]
            except (ValueError,KeyError,IndexError) as exc:
                verdict="REJECTED_EVIDENCE:"+str(exc)
            if verdict not in ("BASELINE_CAUGHT_REAL_COUNTEREXAMPLE",) and not verdict.startswith("REJECTED_EVIDENCE:"):
                raise AssertionError("FAIL_OPEN_SYNTHETIC_CONTROL:"+name+":"+verdict)
            results[name]=verdict
    if len(results)!=len(plans)+1:raise AssertionError("INCOMPLETE_CONTROL_CENSUS")
    result={"authentic_target_defects_found":0,
            "synthetic_controls_tested":len(plans),
            "synthetic_controls_rejected_or_caught":len(plans),
            "conventional_baseline_equal_information":True,
            "MathGraph_classification_for_array_find":"UNKNOWN_UNSUPPORTED_CONTRACT",
            "no_comparative_advantage_established":True,
            "controls":results}
    (evidence/"SYNTHETIC_CONTROLS.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
    return result
if __name__=="__main__":
    challenge(sys.argv[1])
