#!/usr/bin/env python3
"""Real-output falsification: altered observations and coordinated forged hashes."""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from conventional_baseline import run

def digest(content):return hashlib.sha256(content).hexdigest()
def exercise(evidence):
    evidence=Path(evidence)
    if run(evidence)["verdict"]!="BASELINE_TIE":
        raise ValueError("UNMODIFIED_POSITIVE_CONTROL_NOT_GREEN")
    cases=("signed_absence_forgery","unsigned_absence_forgery",
           "modified_c_source_result","deleted_observation",
           "shuffled_observations","forged_target_blob")
    outcomes={"unmodified":"BASELINE_TIE"}
    for name in cases:
        with tempfile.TemporaryDirectory(prefix="qwen-sentinel-challenge-") as d:
            copied=Path(d)
            for item in ("native_report.json","observations.jsonl"):
                shutil.copy2(evidence/item,copied/item)
            report=json.loads((copied/"native_report.json").read_text())
            observations=[json.loads(s) for s in (copied/"observations.jsonl").read_text().splitlines()]
            if name=="signed_absence_forgery":
                i=next(i for i,x in enumerate(observations) if x["kind"]=="sorted_minus_one" and x["rust"]==-1 and len(x["row"])>1)
                observations[i]["rust"]=0
            elif name=="unsigned_absence_forgery":
                i=next(i for i,x in enumerate(observations) if x["kind"]=="unsorted_uintmax" and x["rust"]==4294967295 and len(x["row"])>1)
                observations[i]["rust"]=0
            elif name=="modified_c_source_result":
                i=next(i for i,x in enumerate(observations) if x["kind"]=="sorted_minus_one" and x["c"]==-1 and len(x["row"])>0)
                observations[i]["c"]=0
            elif name=="deleted_observation":
                observations.pop(2)
            elif name=="shuffled_observations":
                observations[0],observations[1]=observations[1],observations[0]
            elif name=="forged_target_blob":
                report["target_blob_ids"]["unsorted_uintmax"]="0"*40
            content="".join(json.dumps(x,sort_keys=True)+"\n" for x in observations).encode()
            (copied/"observations.jsonl").write_bytes(content)
            report["observations_sha256"]=digest(content)
            (copied/"native_report.json").write_text(json.dumps(report,sort_keys=True)+"\n")
            try:
                outcome=run(copied)["verdict"]
            except (ValueError,KeyError,IndexError) as e:
                outcome="REJECTED:"+str(e)
            if not (outcome.startswith("REJECTED:") or outcome=="BASELINE_CAUGHT_COUNTEREXAMPLE"):
                raise AssertionError("FALSE_ACCEPT:"+name+":"+str(outcome))
            outcomes[name]=outcome
    if len(outcomes)!=7:raise AssertionError("NEGATIVE_CENSUS_WRONG")
    (evidence/"negative_controls.json").write_text(json.dumps(outcomes,indent=2,sort_keys=True)+"\n")
    print(json.dumps(outcomes,sort_keys=True))
if __name__=="__main__":
    exercise(sys.argv[1])
