"""Independent source-aware conventional reviewer for sealed old-state/frames.

No calls to MathGraph's normalizer. Authoritative postconditions are
independently encoded from authentic ACSL. Equal inputs and evidence.
"""
import hashlib,itertools,json,sys
from pathlib import Path

REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
PACKET="cb7e59d238a0bfaf9b033048deec4914ae2b9417e451ee215cc9ee2ea8dc0d79"
IDS=("reset","increment","swap","array_swap","sum","plus_five","relational_unknown")
BLOBS=("b22649522e7f9ebac53a08f01ac2328ec9165ac9",
"822e4580ecd398c163e6f85ba79feaa4e3474f83",
"4590f8472cb8fa99e37a4925fa05955b1c418b36",
"d688af3f3d3900cc3582c37a0b0f4b60f77e926e",
"1f65adb2da4cbf2d3c45216737f548ebf56eea07",
"210074be2f34602e4cac03c714375944b12bdff1",
"8b137891791fe96927ad78e64b0aad7bded08bdc")
SOURCE_BLOBS=("70147e46d8d74e10bfe3fbb000d2498b77d9d52b",
"ba53e415d8a68276a1a71e26a9756cb8f54318cf",
"318943f87c2faffa9a4aa3e6cd0bd5be9dcc2286",
"117d6f05e60ef146c94c2e1323c6f5c04d055eb1",
"bc9fe7c71d4079a8bfa1173edcf951726e912ca8",
"2ec0b5ab03f572237fc370b6d230493df9295904",
"6a3c32fee4927d20cf747c60668810c95b167e4d")
def digest(x):return hashlib.sha256(x).hexdigest()
def expected_cases(idx):
 if idx==0:
  yield from itertools.product((-3,0,5),(-2,0,1,4))
 elif idx==1:
  yield from itertools.product((-5,-1,0,3,5),(-3,0,2))
 elif idx==2:
  yield from itertools.product((-3,-1,0,2,5),(-3,0,2,5))
 elif idx==3:
  for n in range(1,4):
   for a in itertools.product((-2,0,2),repeat=n):
    for i in range(n):
     for j in range(n):yield (a,i,j)
 elif idx==4:
  yield from itertools.product((-5,-2,0,2,5),(-5,0,3,5))
 elif idx==5:
  for a in (-5,-2,-1,0,1,2,5):yield (a,)
def admissible(idx,pre,post,ret):
 if idx==0:
  a,b=pre
  return post==[0 if b else a,b]
 if idx==1:
  a,b=pre
  return post==[a+b,b]
 if idx==2:
  a,b=pre
  return post==[b,a]
 if idx==3:
  row,i,j=pre
  return len(post)==len(row) and post[j]==row[i]
 if idx==4:
  a,b=pre
  return post==[a,b] and ret==a+b
 if idx==5:
  (a,)=pre
  return post==[a] and ret==a+5
 return False
def check(root):
 root=Path(root)
 report=json.loads((root/"NATIVE_REPORT.json").read_text())
 packet=(root/"SOURCE_ONLY_PACKET.json").read_bytes()
 if digest(packet)!=PACKET or report.get("source_packet_sha256")!=PACKET:
  raise ValueError("SOURCE_PACKET_DRIFT")
 if report.get("revision")!=REV or report.get("case_count")!=356:
  raise ValueError("SOURCE_REVISION_OR_CENSUS")
 identities=report.get("original_and_translated",[])
 if len(identities)!=7 or [x["id"] for x in identities]!=list(IDS):
  raise ValueError("IDENTITY_CENSUS")
 if [x["rust_blob"] for x in identities]!=list(BLOBS):
  raise ValueError("TARGET_BLOB_DRIFT")
 if [x["c_blob"] for x in identities]!=list(SOURCE_BLOBS):
  raise ValueError("C_SOURCE_IDENTITY_CHANGED")
 native_cases=report.get("cases",[])
 if len(native_cases)!=7 or [x["id"] for x in native_cases]!=list(IDS):
  raise ValueError("NATIVE_CASE_CENSUS_CHANGED")
 if (native_cases[-1].get("verdict")!="UNKNOWN_UNSUPPORTED" or
     native_cases[-1].get("native_count")!=0):
  raise ValueError("UNSUPPORTED_RELATIONAL_CLAIM_PROMOTED")
 raw=(root/"observations.jsonl").read_bytes()
 if digest(raw)!=report.get("observations_sha256"):raise ValueError("OBSERVATION_RECEIPT_DRIFT")
 rows=[json.loads(line) for line in raw.decode().splitlines()]
 if len(rows)!=356:raise ValueError("INCOMPLETE_OBSERVATIONS")
 index=0;failures=[];differences=0
 for idx in range(6):
  for pre in expected_cases(idx):
   if index>=len(rows):raise ValueError("PREMATURE_EOF")
   row=rows[index]
   ground=json.loads(json.dumps(pre))
   if row["index"]!=index or row["case"]!=idx or row["pre"]!=ground:
    raise ValueError("AUTHENTIC_CASE_ORDER_OR_VALUES_CHANGED:"+str(index))
   source_ok=admissible(idx,pre,row["c_post"],row["c_result"])
   target_ok=admissible(idx,pre,row["rust_post"],row["rust_result"])
   if not source_ok or not target_ok:
    failures.append({"index":index,"case":idx,"source_ok":source_ok,"target_ok":target_ok,"observation":row})
   if row["c_post"]!=row["rust_post"] or row["c_result"]!=row["rust_result"]:
    differences+=1
   index+=1
 if index!=len(rows):raise ValueError("EXTRA_OBSERVATIONS")
 verdict="BASELINE_CAUGHT_SOURCE_OR_TARGET_ERROR" if failures else "BASELINE_TIE"
 result={"status":verdict,"cases":index,"failures":len(failures),
         "first_counterexample":failures[:2],"differential_disagreements":differences,
         "supported_contracts":6,"relational_unsupported":1,
         "pointer_alias_scope":"NOT_TESTED","cost_advantage":"UNKNOWN",
         "independence":"Independent manually authored ACSL finite comparator; no MathGraph contract code"}
 (root/"BASELINE_REPORT.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print(json.dumps(result,sort_keys=True))
 return result
if __name__=="__main__":
 r=check(sys.argv[1])
 if r["status"]!="BASELINE_TIE":raise SystemExit(1)
