#!/usr/bin/env python3
"""Independent checker: real verifier assertion failure, never compilation failure."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
UPSTREAM="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
TOOL="a3fe3b37b2ef1b68a6ef3b22490b4e628f442da423cb56fce6afc554e19c5c04"
FILES={
"gcd":("data/tutorial_wp/ex-2-gcd.c","acd6ca718d61d14d709599d7961436ec136c13a94261d40f38911a190bc20d2d",
"RQ3_result/Full_Fixed/ex-2-gcd.rs","2536507f61a2fe83a1356c969093be18cd7aee4511c5155cf70753daa4506cab",
"assert(is_gcd(2, 0, 2));","assert(!is_gcd(2, 0, 1));"),
"fibo":("data/tutorial_wp/ex-N-fibo.c","258c311b2e665fab0ffa67c78981ccaa5689b3cad613a560298f6ce7fb5c50ec",
"RQ3_result/Full_Fixed/ex-N-fibo.rs","e207d24b404f8964bc42bf8a67245ac78dd94c6ace9cd64e04e63a47b3456849",
"assert(is_fibo(0, 1));","assert(!is_fibo(-1, 0));")}
def raw(p):
    p=Path(p)
    if not p.is_file():raise ValueError("MISSING:"+str(p))
    return p.read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def ensure(test,msg):
    if not test:raise ValueError(msg)
def check(root,tool,out):
    root,tool,out=map(Path,(root,tool,out))
    git=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    ensure(git==UPSTREAM and sha(tool)==TOOL,"SOURCE_OR_TOOL_IDENTITY")
    receipt=json.loads(raw(out/"receipt.json"))
    ensure(receipt.get("upstream")==UPSTREAM and receipt.get("tool_sha256")==TOOL,"RECEIPT_IDENTITY")
    keys={k+"/"+l for k in FILES for l in ("original","positive","negative")}
    ensure(set(receipt.get("lanes",{}))==keys,"LANE_CENSUS")
    report={}
    for name,(cp,cs,rp,rs,pos,neg) in FILES.items():
        ensure(sha(root/cp)==cs and sha(root/rp)==rs,"ORIGINAL_BYTES:"+name)
        original=raw(root/rp)
        marker=b"} // verus!"
        ensure(original.count(marker)==1,"ORIGINAL_MACRO_END")
        for lane in ("original","positive","negative"):
            key=name+"/"+lane
            receipt_lane=receipt["lanes"][key]
            source=raw(out/name/(lane+".rs"))
            logs=raw(out/name/(lane+".log"))
            ensure(hashlib.sha256(source).hexdigest()==receipt_lane["program_sha256"],"PROGRAM_DIGEST:"+key)
            ensure(hashlib.sha256(logs).hexdigest()==receipt_lane["log_sha256"],"LOG_DIGEST:"+key)
            if lane=="original":
                ensure(source==original,"ORIGINAL_TAMPER:"+key)
            else:
                ensure(source.split(marker)[0].startswith(original.split(marker)[0]),"MODIFIED_PREEXISTING_SOURCE:"+key)
                sentence=(pos if lane=="positive" else neg).encode()
                ensure(sentence in source,"MISSING_PROOF_OBLIGATION:"+key)
                ensure((neg if lane=="positive" else pos).encode() not in source,"CROSS_CONTAMINATION:"+key)
            log=logs.decode("utf-8","replace")
            ensure("verification results::" in log,"NO_VERUS_SUMMARY:"+key)
            if lane=="negative":
                ensure(receipt_lane["exit"]!=0 and re.search(r"verification results::\s*\d+ verified,\s*[1-9]\d* errors",log),"NO_NATIVE_REJECTION:"+key)
                ensure("assertion failed" in log.lower(),"NEGATIVE_NOT_PROOF_ASSERTION_FAILURE:"+key)
                report[key]="REJECTED_NATIVE_ASSERTION"
            else:
                ensure(receipt_lane["exit"]==0 and re.search(r"verification results::\s*\d+ verified,\s*0 errors",log),"NATIVE_SUCCESS_MISSING:"+key)
                report[key]="VERIFIED_CONDITIONAL_ON_SOURCE_AXIOMS"
    return {"status":"WARRANTED_BOUNDED_NATIVE_OBLIGATION_PROBE","lanes":report,
            "limits":["Native failure does not alone prove semantic non-derivability.",
                      "Separate bounded source-compatible finite countermodels remain the semantic evidence.",
                      "No demonstration of incorrect executable results or comparative superiority."]}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("source",type=Path);p.add_argument("tool",type=Path);p.add_argument("evidence",type=Path)
    a=p.parse_args()
    try: result=check(a.source,a.tool,a.evidence)
    except (ValueError,OSError,KeyError,json.JSONDecodeError,subprocess.CalledProcessError) as e:
        result={"status":"REJECTED_OR_UNKNOWN","reason":str(e)}
    (a.evidence/"adjudication.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    if result["status"]!="WARRANTED_BOUNDED_NATIVE_OBLIGATION_PROBE":raise SystemExit(1)
