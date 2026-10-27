"""Independent conventional reading of C admissible pairs and Rust borrow output."""
import hashlib,json,re,sys
from pathlib import Path
PACKET="1710221dfdfb31911b21ecd472ec5dffc83a93be3b69d723093bc4be5b4985b3"
ALLOWED={"add_read":[("p","q")],"add_output":[("p","q")],
"max_mut_behaviors":[("a","b")],"max_read":[("a","b")],
"max_mut_old":[("a","b")],"max_read_cases":[("a","b")],
"max_nullable":[("a","b")],"array_equal":[("a_1","a_2")],
"vector_sum":[("v1","v2")]}
FORBIDDEN={"add_output":[("p","r"),("q","r")],
"vector_sum":[("v1","v_res"),("v2","v_res")]}
TARGET={"add_read":"40776acb8f6b8613ce2523e803b12b831d2efc25",
"add_output":"0af446a465027b7ae458e05833ddb21cee794cc8",
"max_mut_behaviors":"acba66aebd6813bb129e08fc215e44b4e01534a4",
"max_read":"6f9017d89b91631960a77be6d1c40f5378ff3e81",
"max_mut_old":"eb413aa48c528322b5b42e67837d963b72455ec1",
"max_read_cases":"9567028bd64b93f8b9afece9f33c4beff6ee1b75",
"max_nullable":"b4cf82e670797861c4736e43884d895aad4bf656",
"array_equal":"ef83a75a5a7bf87834e0cd525e14c51253a3e512",
"vector_sum":"b5a4a47c145e3a052742e3a2e09cd240f7f1c114"}
def sha(b):return hashlib.sha256(b).hexdigest()
def compare(root):
 root=Path(root)
 r=json.loads((root/"NATIVE_REPORT.json").read_text())
 if r.get("source_only_packet_sha256")!=PACKET or sha((root/"FROZEN_PACKET.json").read_bytes())!=PACKET:
  raise ValueError("SOURCE_PACKET_CHANGED")
 found=r.get("findings",[])
 if len(found)!=9 or {x["id"] for x in found}!=set(ALLOWED):
  raise ValueError("MISSING_CASE")
 counts={"allowed":0,"forbidden":0,"accepted":0,"rejected":0,"nullable":0}
 issues=[]
 for item in found:
  key=item["id"]
  if item.get("target_blob")!=TARGET[key]:raise ValueError("WRONG_TARGET_BLOB:"+key)
  if item.get("distinct",{}).get("status")!="ACCEPTED":
   raise ValueError("DISTINCT_CONTROL_FAILED:"+key)
  observed={tuple(x["pair"]):x for x in item.get("pairs",[])}
  if set(observed)!=(set(ALLOWED[key])|set(FORBIDDEN.get(key,[]))):
   raise ValueError("PAIR_CENSUS:"+key)
  for pair in ALLOWED[key]:
   datum=observed[pair];counts["allowed"]+=1
   if datum["c"]["status"]!="C_SAME_POINTER_EXECUTED":raise ValueError("NO_C_WITNESS:"+key)
   st=datum["rust"]["status"]
   if st=="ACCEPTED":counts["accepted"]+=1
   elif st=="BORROW_REJECTED":
    counts["rejected"]+=1
    if not (set(datum["rust"]["errors"])&{"E0499","E0502"}):
     raise ValueError("MISSING_NATIVE_BORROW_DIAGNOSTIC")
    issues.append({"source":key,"pointer_pair":pair,"finding":"DIRECT_SAFE_RUST_ALIAS_REFUSED"})
   else:raise ValueError("COMPILATION_UNKNOWN:"+key)
   name=key+"_"+"_".join(pair)
   data=(root/(name+".log")).read_bytes()
   if sha(data)!=datum["rust"]["log_sha256"]:raise ValueError("NATIVE_LOG_DIGEST_DRIFT")
   if st=="BORROW_REJECTED" and not ("cannot borrow" in data.decode("utf8","replace")):
    raise ValueError("BORROW_REJECTION_NOT_GROUNDED")
  for pair in FORBIDDEN.get(key,[]):
   counts["forbidden"]+=1
   if observed[pair]["status"]!="SOURCE_FORBIDS_ALIAS":
    raise ValueError("SOURCE_SEPARATION_PROMOTED")
  for nullable in item.get("nullable",[]):
   if nullable["rust"]["status"]!="ACCEPTED":
    raise ValueError("NULL_POSITIVE_CONTROL_FAILED")
   counts["nullable"]+=1
 if counts!={"allowed":9,"forbidden":4,"accepted":7,"rejected":2,"nullable":2}:
  raise ValueError("UNEXPECTED_OBSERVATION_COUNTS:"+str(counts))
 output={"verdict":"BASELINE_TIE","counts":counts,"independent_source_aware":True,
         "admissibility_mismatches":issues,"relative_detection_advantage":"NONE",
         "relative_cost_advantage":"NOT_MEASURED",
         "universal_C_Rust_refinement_claim":False}
 (root/"BASELINE_REPORT.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
 print(json.dumps(output,sort_keys=True))
 return output
if __name__=="__main__":compare(sys.argv[1])
