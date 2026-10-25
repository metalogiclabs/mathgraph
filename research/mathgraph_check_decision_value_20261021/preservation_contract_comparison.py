"""Pinned source-changing, behavior-preserving contract and cost comparison.

Scoped transformation: De Morgan rewrite within isEndSeparator in goldmark-meta
PR #8. Independent checker enumerates every possible byte and checks exact
context-diff restrictions. Runtime verifier runs native Go tests on both revisions.
This is bounded to a specific predicate, not a general proof of parser equivalence.
"""
import json, pathlib, subprocess, tempfile, time, statistics, os
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(os.environ.get("MATHGRAPH_PRESERVE_OUT","preservation.json"))
HEAD="ad93e759a4ba37c8b548367506f50dfd5bc0ce1a"
URL="https://github.com/noerw/goldmark-meta.git"
OLD="line[i] != '-' && line[i] != '.'"
NEW="!(line[i] == '-' || line[i] == '.')"
def execute(args, cwd, timeout=240):
    start=time.perf_counter()
    p=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    return round(time.perf_counter()-start,6),p.returncode,p.stdout[-1500:]
def require(rec,label):
    if rec[1]: raise RuntimeError(label+": "+rec[2])
def check(before,after):
    start=time.perf_counter()
    if before.count(OLD)!=1 or after!=before.replace(OLD,NEW,1):
        raise RuntimeError("CONTEXT_MISMATCH")
    for b in range(256):
        left=(b!=45 and b!=46)
        right=not(b==45 or b==46)
        if left!=right:raise RuntimeError("EXHAUSTIVE_BYTE_MISMATCH")
    return round(time.perf_counter()-start,6)
def main():
    with tempfile.TemporaryDirectory(prefix="mg-preservation-") as td:
        path=pathlib.Path(td)/"source"
        require(execute(["git","clone","-q",URL,str(path)],td),"clone")
        require(execute(["git","checkout","-q","--detach",HEAD],path),"checkout")
        _,_,identity=execute(["git","rev-parse","HEAD"],path)
        if identity.strip()!=HEAD: raise RuntimeError("SOURCE_IDENTITY_MISMATCH")
        probe=ROOT/"research/mathgraph_check_decision_value_20261021/frontmatter_consequence_test.go.txt"
        (path/"mathgraph_consequence_test.go").write_bytes(probe.read_bytes())
        original=(path/"meta.go").read_text()
        if original.count(OLD)!=1: raise RuntimeError("PINNED_SOURCE_PREDICATE_MISSING")
        require(execute(["go","test","-count=1","./..."],path),"historical native tests")
        modified=original.replace(OLD,NEW,1)
        (path/"meta.go").write_text(modified)
        if not execute(["git","diff","--exit-code","--","meta.go"],path)[1]:
            raise RuntimeError("SOURCE_DID_NOT_CHANGE")
        proof_times=[check(original,modified) for _ in range(7)]
        # Both original contract obligation and all existing native tests are
        # executed on modified source, with alternating full and selective runs.
        require(execute(["go","test","-count=1","./..."],path),"modified warmup")
        samples=[]
        for i in range(7):
            cmds={"full":["go","test","-count=1","./..."],
                  "selective":["go","test","-count=1","-run","^TestMathGraphProspective","./..."]}
            record={}
            for k in (("full","selective") if i%2==0 else ("selective","full")):
                result=execute(cmds[k],path)
                require(result,k)
                record[k]=result[0]
            samples.append(record)
        mf=statistics.median(x["full"] for x in samples)
        ms=statistics.median(x["selective"] for x in samples)
        mp=statistics.median(proof_times)
        result={"schema":"mathgraph.verified-source-changing-preservation.v1",
                "repository":"noerw/goldmark-meta","original_revision":HEAD,
                "source_changed":True,"change":"De Morgan rewrite of end-separator byte predicate",
                "verification":"exact context equality and independent exhaustive 256-byte truth-table comparison",
                "property":"isEndSeparator guard predicate has same result for all byte inputs",
                "native_original_pass":True,"native_modified_pass":True,
                "rounds":samples,"median_full_seconds":mf,"median_selective_seconds":ms,
                "median_contract_checker_seconds":mp,
                "contract_vs_full_execution_ratio":round(mf/max(mp,0.000001),2),
                "contract_vs_selective_execution_ratio":round(ms/max(mp,0.000001),2),
                "best_conventional_baseline":"manual syntactic De Morgan proof, zero native execution for this bounded guard",
                "beats_best_conventional_baseline":False,
                "semantic_transport":"WARRANTED_ONLY_FOR_DECLARED_GUARD_PREDICATE",
                "limitations":["No general parser semantics or environmental verification transport",
                 "One known local syntactic identity; equal-information reviewer can verify directly",
                 "Python checker timing excludes invocation/startup and source acquisition",
                 "Full CI cost excludes environment setup; scoped contract not permission to skip unrelated checks",
                 "Test results do not establish commercial advantage"]}
        OUT.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
