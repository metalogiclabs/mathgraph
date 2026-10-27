#!/usr/bin/env python3
"""Native, source-pinned Verus proof-obligation producer. Never edits upstream."""
import argparse,hashlib,json,subprocess
from pathlib import Path
PIN="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
TOOL="a3fe3b37b2ef1b68a6ef3b22490b4e628f442da423cb56fce6afc554e19c5c04"
CASES={
"gcd":("data/tutorial_wp/ex-2-gcd.c","acd6ca718d61d14d709599d7961436ec136c13a94261d40f38911a190bc20d2d",
"RQ3_result/Full_Fixed/ex-2-gcd.rs","2536507f61a2fe83a1356c969093be18cd7aee4511c5155cf70753daa4506cab",
"""proof fn mg_gcd_positive() {
    is_gcd_inductive();
    assert(is_gcd(2, 0, 2));
}""",
"""proof fn mg_gcd_exclusion() {
    is_gcd_inductive();
    assert(!is_gcd(2, 0, 1));
}"""),
"fibo":("data/tutorial_wp/ex-N-fibo.c","258c311b2e665fab0ffa67c78981ccaa5689b3cad613a560298f6ce7fb5c50ec",
"RQ3_result/Full_Fixed/ex-N-fibo.rs","e207d24b404f8964bc42bf8a67245ac78dd94c6ace9cd64e04e63a47b3456849",
"""proof fn mg_fibo_positive() {
    is_fibo_inductive();
    assert(is_fibo(0, 1));
}""",
"""proof fn mg_fibo_exclusion() {
    is_fibo_inductive();
    fib_monotonic();
    assert(!is_fibo(-1, 0));
}""")}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def added(original,proof):
    marker="} // verus!"
    if original.count(marker)!=1:raise ValueError("MACRO_BOUNDARY_NOT_UNIQUE")
    return original.replace(marker,"\n"+proof+"\n"+marker)
def run(root,verus,out):
    root,verus,out=Path(root).resolve(),Path(verus).resolve(),Path(out).resolve()
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if rev!=PIN or sha(verus)!=TOOL:raise ValueError("PINNED_SOURCE_OR_TOOL_DRIFT")
    out.mkdir(parents=True,exist_ok=True)
    receipt={"upstream":rev,"tool_sha256":sha(verus),"lanes":{}}
    for name,(cp,cs,rp,rs,pos,neg) in CASES.items():
        if sha(root/cp)!=cs or sha(root/rp)!=rs:raise ValueError("SOURCE_BYTES_CHANGED:"+name)
        original=(root/rp).read_text()
        for lane,content in (("original",original),("positive",added(original,pos)),("negative",added(original,neg))):
            directory=out/name
            directory.mkdir(parents=True,exist_ok=True)
            program=directory/(lane+".rs")
            program.write_text(content)
            proc=subprocess.run([str(verus),str(program)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                text=True,check=False,timeout=90)
            log=directory/(lane+".log")
            log.write_text(proc.stdout)
            receipt["lanes"][name+"/"+lane]={"exit":proc.returncode,"program_sha256":sha(program),"log_sha256":sha(log)}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v["exit"] for k,v in receipt["lanes"].items()},sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("source",type=Path);p.add_argument("tool",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();run(a.source,a.tool,a.output)
