#!/usr/bin/env python3
"""Falsification and anti-overclaim controls on copies of real C/Rust evidence."""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from conventional_baseline import check
def h(data):return hashlib.sha256(data).hexdigest()
def exercise(evidence):
 evidence=Path(evidence)
 clean=check(evidence)
 if clean["status"]!="BASELINE_TIE" or clean["cases"]!=356:
  raise AssertionError("AUTHENTIC_CLEAN_CONTROL_MISSING")
 mutations={
  "reset_b_frame_breach":"reject",
  "reset_false_branch_wrong":"reject",
  "increment_wrong_prestate":"reject",
  "swap_missing_second_update":"reject",
  "weak_array_written_guarantee_broken":"reject",
  "pointer_sum_wrong_return":"reject",
  "plus_five_input_modified":"reject",
  "truncated_native_receipt":"reject",
  "forged_source_blob":"reject",
  "promoted_unknown_relational_proof":"reject",
  "weak_array_unconstrained_other_position":"accept",
  "increment_return_unconstrained":"accept"}
 outcomes={"authentic_unmodified":"BASELINE_TIE"}
 for label,intent in mutations.items():
  with tempfile.TemporaryDirectory(prefix="oldframe-evidence-control-") as tmp:
   path=Path(tmp)
   for name in ("SOURCE_ONLY_PACKET.json","NATIVE_REPORT.json","observations.jsonl"):
    shutil.copy2(evidence/name,path/name)
   report=json.loads((path/"NATIVE_REPORT.json").read_text())
   rows=[json.loads(line) for line in (path/"observations.jsonl").read_text().splitlines()]
   def take(case,condition=lambda row:True):
    return next(x for x in rows if x["case"]==case and condition(x))
   if label=="reset_b_frame_breach":
    x=take(0,lambda r:r["pre"][1]!=0);x["rust_post"][1]+=1
   elif label=="reset_false_branch_wrong":
    x=take(0,lambda r:r["pre"][0]!=0 and r["pre"][1]==0);x["rust_post"][0]=0
   elif label=="increment_wrong_prestate":
    x=take(1);x["rust_post"][0]+=1
   elif label=="swap_missing_second_update":
    x=take(2,lambda r:r["pre"][0]!=r["pre"][1]);x["rust_post"][1]=x["pre"][1]
   elif label=="weak_array_written_guarantee_broken":
    x=take(3,lambda r:r["pre"][0][r["pre"][1]]!=r["pre"][0][r["pre"][2]])
    row,i,j=x["pre"];x["rust_post"][j]=row[j]
   elif label=="pointer_sum_wrong_return":
    x=take(4);x["rust_result"]+=1
   elif label=="plus_five_input_modified":
    x=take(5);x["rust_post"][0]+=1
   elif label=="truncated_native_receipt":
    rows.pop(2)
   elif label=="forged_source_blob":
    report["original_and_translated"][0]["c_blob"]="0"*40
   elif label=="promoted_unknown_relational_proof":
    report["cases"][-1]["verdict"]="WARRANTED_BOUNDED_MATCH"
   elif label=="weak_array_unconstrained_other_position":
    x=take(3,lambda r:len(r["pre"][0])>=2 and r["pre"][2]!=0)
    row,i,j=x["pre"];x["rust_post"][0]=999
   elif label=="increment_return_unconstrained":
    x=take(1);x["rust_result"]=99999
   else:raise AssertionError("UNHANDLED_CONTROL")
   data=("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows)).encode()
   (path/"observations.jsonl").write_bytes(data)
   report["observations_sha256"]=h(data)
   (path/"NATIVE_REPORT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
   try:result=check(path);verdict=result["status"]
   except (ValueError,KeyError,IndexError,AssertionError) as e:verdict="REJECTED_EVIDENCE:"+str(e)
   permitted=(verdict=="BASELINE_TIE") if intent=="accept" else (
       verdict=="BASELINE_CAUGHT_SOURCE_OR_TARGET_ERROR" or verdict.startswith("REJECTED_EVIDENCE:"))
   if not permitted:raise AssertionError("WRONG_CONTROL_RESULT:"+label+":"+verdict)
   outcomes[label]=verdict
 answer={"real_authentic_migration_defects":0,
         "positive_permissive_controls_passed":2,
         "synthetic_negative_controls_rejected_or_detected":10,
         "total_controls_passed":12,
         "honest_claim":"bounded empirical source fidelity; no comparative advantage proven",
         "results":outcomes}
 (evidence/"SYNTHETIC_CONTROLS.json").write_text(json.dumps(answer,indent=2,sort_keys=True)+"\n")
 print(json.dumps(answer,sort_keys=True))
 return answer
if __name__=="__main__":exercise(sys.argv[1])
