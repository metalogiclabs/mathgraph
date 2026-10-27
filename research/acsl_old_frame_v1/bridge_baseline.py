"""Independent source-aware bounded comparator for constructed safe adapter."""
import hashlib,json,sys
from pathlib import Path
VALUES=(-5,-2,0,3,7)
def sha(b):return hashlib.sha256(b).hexdigest()
def check(path):
 path=Path(path);report=json.loads((path/"BRIDGE_REPORT.json").read_text())
 if report.get("category")!="CONSTRUCTED_ADAPTER_NOT_ORIGINAL_TRANSLATION":
  raise ValueError("ADAPTER_PUBLISHED_SOURCE_CONFUSION")
 if report.get("c_blob")!="318943f87c2faffa9a4aa3e6cd0bd5be9dcc2286" or report.get("rust_blob")!="4590f8472cb8fa99e37a4925fa05955b1c418b36":
  raise ValueError("SOURCE_PIN_DRIFT")
 raw=(path/"bridge_observations.jsonl").read_bytes()
 if sha(raw)!=report.get("observations_sha256"):raise ValueError("OBSERVATIONS_CHANGED")
 records=[json.loads(row) for row in raw.decode().splitlines()]
 planned=[("SAME",x,x) for x in VALUES]+[("DISTINCT",x,y) for x in VALUES for y in VALUES]
 if len(records)!=30:raise ValueError("UNEXPECTED_CASE_CENSUS")
 bad=[]
 for i,(record,(topo,a,b)) in enumerate(zip(records,planned)):
  if record["id"]!=i or record["topology"]!=topo or record["before"]!=[a,b]:
   raise ValueError("CASE_TOPOLOGY_DRIFT")
  expected=[a,a] if topo=="SAME" else [b,a]
  if record["native_c"]!=expected or record["constructed_safe_rust"]!=expected:
   bad.append(record)
 verdict="BASELINE_TIE" if not bad else "BASELINE_CAUGHT_BRIDGE_ERROR"
 result={"verdict":verdict,"count":30,"failed":len(bad),"first":bad[:1],
         "source_contract_independent":"C swap with same pointer is no-op, with distinct pointers exchanges values.",
         "relative_advantage":"NOT_SHOWN"}
 (path/"BRIDGE_BASELINE.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps(result,sort_keys=True))
 return result
if __name__=="__main__":
 r=check(sys.argv[1])
 if r["verdict"]!="BASELINE_TIE":raise SystemExit(1)
