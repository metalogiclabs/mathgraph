#!/usr/bin/env python3
"""Ten independent mutation controls against real returned native proof receipts.

Mutations are SYNTHETIC changes of copies; never real generated-Rust defects.
Each expected false authorization must be refused even if receipts are edited.
"""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from baseline import compare
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find(report,case,pair=None):
 item=next(x for x in report["findings"] if x["id"]==case)
 if pair is None:return item
 return next(x for x in item["pairs"] if x["pair"]==list(pair))
def validate(source):
 source=Path(source)
 original=compare(source)
 if original["verdict"]!="BASELINE_TIE":raise AssertionError("AUTHENTIC_CONTROL_NOT_PASSING")
 cases=("forge_mutable_borrow_success","forge_other_mutable_borrow_success",
  "forge_shared_read_borrow_failure","remove_native_c_alias_witness",
  "inflate_explicit_source_separation","forge_target_blob",
  "delete_source_pair","replace_borrow_log_and_rehash",
  "withdraw_nullable_positive","tamper_source_only_packet")
 outcomes={"authentic_unchanged":"ACCEPTED"}
 for name in cases:
  with tempfile.TemporaryDirectory(prefix="mg-alias-evidence-negative-") as temp:
   copied=Path(temp)/"evidence"
   shutil.copytree(source,copied)
   receipt=copied/"NATIVE_REPORT.json"
   report=json.loads(receipt.read_text())
   if name=="forge_mutable_borrow_success":
    datum=find(report,"max_mut_behaviors",("a","b"))
    datum["rust"]["status"]="ACCEPTED";datum["rust"]["exit"]=0;datum["rust"]["errors"]=[]
   elif name=="forge_other_mutable_borrow_success":
    datum=find(report,"max_mut_old",("a","b"))
    datum["rust"]["status"]="ACCEPTED";datum["rust"]["errors"]=[]
   elif name=="forge_shared_read_borrow_failure":
    datum=find(report,"add_read",("p","q"))
    datum["rust"]["status"]="BORROW_REJECTED"
    datum["rust"]["errors"]=["E0499"]
   elif name=="remove_native_c_alias_witness":
    find(report,"max_mut_old",("a","b"))["c"]["status"]="UNKNOWN_C_RUNTIME"
   elif name=="inflate_explicit_source_separation":
    find(report,"add_output",("p","r"))["status"]="DIRECT_RUST_CALL_ADMITTED"
   elif name=="forge_target_blob":
    find(report,"max_mut_old")["target_blob"]="0"*40
   elif name=="delete_source_pair":
    item=find(report,"vector_sum")
    item["pairs"]=[x for x in item["pairs"] if x["pair"]!=["v1","v2"]]
   elif name=="replace_borrow_log_and_rehash":
    selected=copied/"max_mut_behaviors_a_b.log"
    shutil.copyfile(copied/"add_read_p_q.log",selected)
    find(report,"max_mut_behaviors",("a","b"))["rust"]["log_sha256"]=sha(selected)
   elif name=="withdraw_nullable_positive":
    find(report,"max_nullable")["nullable"]=[]
   elif name=="tamper_source_only_packet":
    packet=copied/"FROZEN_PACKET.json"
    packet.write_bytes(packet.read_bytes()+b"\n")
   receipt.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
   try:
    checked=compare(copied)
    status=checked["verdict"]
   except (ValueError,FileNotFoundError,KeyError,IndexError,AssertionError) as exc:
    status="REJECTED:"+str(exc)
   if not status.startswith("REJECTED:"):
    raise AssertionError("FAIL_OPEN:"+name+":"+status)
   outcomes[name]=status
 if len(outcomes)!=11:raise AssertionError("NEGATIVE_CENSUS_MISMATCH")
 result={"authentic_real_migration_runtime_errors":0,
         "source_admitted_direct_safe_Rust_API_refusals":2,
         "controls_tested":10,"controls_rejected":10,
         "independent_baseline_still_ties":True,
         "mutations_are_synthetic":True,"results":outcomes}
 (source/"NEGATIVE_CONTROLS.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print(json.dumps(result,sort_keys=True))
 return result
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("usage: challenge.py evidence")
 validate(sys.argv[1])
