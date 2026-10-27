#!/usr/bin/env python3
"""Replay adversarial and legitimate variations of sealed 2350-case observations.

Only COPIES are changed. No claim of defects in authentic Qwen targets.
Receipts are rehashed to ensure semantic rejection, not just SHA detection.
"""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from conventional_baseline import check
from normalizer import authorized

def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(evidence):
    evidence=Path(evidence)
    if check(evidence)["status"]!="BASELINE_TIE":raise AssertionError("AUTHENTIC_POSITIVE_NOT_GREEN")
    mutants={
        "max_below_all_members":"reject",
        "all_even_false":"reject",
        "odd_input_false_positive":"reject",
        "even_index_not_zero":"reject",
        "double_index_wrong_output":"reject",
        "odd_index_unconstrained_change":"accept",
        "deleted_observation":"reject",
        "forged_target_blob":"reject",
        "forged_source_packet":"reject"
    }
    outcomes={"authentic_unmodified":"ACCEPTED"}
    for mutation,expected in mutants.items():
        with tempfile.TemporaryDirectory(prefix="acsl-implication-control-") as td:
            d=Path(td)
            for name in ("SOURCE_ONLY_PACKET.json","NATIVE_REPORT.json","observations.jsonl"):
                shutil.copy2(evidence/name,d/name)
            report=json.loads((d/"NATIVE_REPORT.json").read_text())
            rows=[json.loads(x) for x in (d/"observations.jsonl").read_text().splitlines()]
            packet=json.loads((d/"SOURCE_ONLY_PACKET.json").read_text())
            def choose(i,predicate):
                matches=[r for r in rows if r["case"]==i and predicate(r)]
                if not matches:raise AssertionError("MISSING_PREDECLARED_CONTROL:"+mutation)
                return matches[0]
            altered=None
            if mutation=="max_below_all_members":
                altered=choose(0,lambda r:r["probe"] and max(r["input"])>=1)
                altered["rust_result"]=-99
            elif mutation=="all_even_false":
                altered=choose(1,lambda r:r["probe"] and all(x%2==0 for x in r["input"]))
                altered["rust_result"]=0
            elif mutation=="odd_input_false_positive":
                altered=choose(1,lambda r:r["probe"] and any(x%2 for x in r["input"]))
                altered["rust_result"]=1
            elif mutation=="even_index_not_zero":
                altered=choose(2,lambda r:r["probe"] and len(r["input"])>=1)
                altered["rust_post"][0]=17
            elif mutation=="double_index_wrong_output":
                altered=choose(3,lambda r:r["probe"] and len(r["input"])>=2)
                altered["rust_post"][1]=7
            elif mutation=="odd_index_unconstrained_change":
                altered=choose(2,lambda r:len(r["input"])>=2 and r["rust_post"][0]==0)
                altered["rust_post"][1]=999
            elif mutation=="deleted_observation":
                rows.pop(0)
            elif mutation=="forged_target_blob":
                first=next(iter(report["target_hashes"]))
                report["target_hashes"][first]["blob"]="0"*40
            elif mutation=="forged_source_packet":
                packet["cases"][4]["status"]="DISCOVERED_BOUNDED_CONTRACT"
                (d/"SOURCE_ONLY_PACKET.json").write_text(json.dumps(packet,sort_keys=True,indent=2)+"\n")
            if altered is not None:
                spec=packet["cases"][altered["case"]]
                observed=authorized(spec,tuple(altered["input"]),tuple(altered["rust_post"]),altered["rust_result"])
                if observed!=(expected=="accept"):
                    raise AssertionError("EXTRACTOR_FALSE_ACCEPT_OR_REJECT:"+mutation+":"+str(observed))
            newdata="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows).encode()
            (d/"observations.jsonl").write_bytes(newdata)
            report["observations_sha256"]=sha(newdata)
            (d/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
            try:
                result=check(d)
                status=result["status"]
            except (ValueError,KeyError,IndexError) as exc:
                status="REJECTED:"+str(exc)
            if expected=="accept" and status!="BASELINE_TIE":
                raise AssertionError("INVALID_FALSE_REJECTION:"+mutation+":"+status)
            if expected=="reject" and status!="BASELINE_CAUGHT_COUNTEREXAMPLE" and not status.startswith("REJECTED:"):
                raise AssertionError("INVALID_FALSE_ACCEPT:"+mutation+":"+status)
            outcomes[mutation]=status
    totals={"authentic_errors":0,"synthetic_total":len(mutants),
            "synthetic_negative_controls":sum(v=="reject" for v in mutants.values()),
            "synthetic_positive_controls":sum(v=="accept" for v in mutants.values()),
            "all_controls_passed":True,"actual_competitive_advantage":"NOT_DEMONSTRATED",
            "outcomes":outcomes}
    (evidence/"CHALLENGE_REPORT.json").write_text(json.dumps(totals,sort_keys=True,indent=2)+"\n")
    print(json.dumps(totals,sort_keys=True))
    return totals

if __name__=="__main__":
    run(sys.argv[1])
