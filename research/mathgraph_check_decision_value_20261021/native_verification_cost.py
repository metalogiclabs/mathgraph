#!/usr/bin/env python3
"""Real-source native test cost comparison for pinned goldmark-meta PR 8.

This benchmark measures verification *execution time*, not sound semantic
transport or customer savings. It rejects any claim that unexecuted native
tests prove behavior. All source history SHA pins are checked.
"""
import json, os, pathlib, statistics, subprocess, tempfile, time

BASE="f5d5bebad44ac55105584283ee742a9e6f3524c0"
HEAD="ad93e759a4ba37c8b548367506f50dfd5bc0ce1a"
URL="https://github.com/yuin/goldmark-meta.git"
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(os.environ.get("MATHGRAPH_NATIVE_OUT","mathgraph-native-cost.json"))

def run(cmd,cwd=None,timeout=240):
    t=time.perf_counter()
    p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     text=True,timeout=timeout)
    return {"seconds":round(time.perf_counter()-t,6),"code":p.returncode,
            "log_tail":p.stdout[-1600:]}

def checked(label,result):
    if result["code"]!=0:
        raise RuntimeError(label+" FAILED: "+result["log_tail"])
    return result["seconds"]

def main():
    with tempfile.TemporaryDirectory(prefix="mathgraph-goldmark-") as temp:
        source=pathlib.Path(temp)/"source"
        checked("git clone",run(["git","clone","--quiet",URL,str(source)],timeout=160))
        checked("git checkout head",run(["git","checkout","--quiet","--detach",HEAD],source))
        actual=run(["git","rev-parse","HEAD"],source)
        if actual["log_tail"].strip()!=HEAD: raise RuntimeError("HEAD_IDENTITY_MISMATCH")
        # Native original package suite, plus a separately prepared consequence
        # test covering the source author's advertised feature and body fidelity.
        probe=ROOT/"research/mathgraph_check_decision_value_20261021/frontmatter_consequence_test.go.txt"
        (source/"mathgraph_consequence_test.go").write_bytes(probe.read_bytes())
        # Warm shared compilation/dependency cache outside the measurement.
        checked("warm Go",run(["go","test","-count=1","./..."],source,timeout=240))
        commands={
          "full":["go","test","-count=1","./..."],
          "targeted":["go","test","-count=1","-run",
                      "^TestMathGraphProspective","./..."],
        }
        measured=[]
        for i in range(6):
            order=("full","targeted") if i%2==0 else ("targeted","full")
            record={"round":i}
            for name in order:
                record[name+"_seconds"]=checked(name,run(commands[name],source,timeout=240))
            measured.append(record)
        (source/"mathgraph_consequence_test.go").unlink()
        checked("git checkout base",run(["git","checkout","--quiet","--detach",BASE],source))
        actual=run(["git","rev-parse","HEAD"],source)
        if actual["log_tail"].strip()!=BASE: raise RuntimeError("BASE_IDENTITY_MISMATCH")
        checked("base original Go suite",run(["go","test","-count=1","./..."],source,timeout=240))
        (source/"mathgraph_consequence_test.go").write_bytes(probe.read_bytes())
        base=run(["go","test","-count=1","-run",
                  "^TestMathGraphProspectiveFrontmatterConsequence$","./..."],
                 source,timeout=240)
        if base["code"]==0: raise RuntimeError("BASE_UNEXPECTED_PASS")
        # The new feature was expected to fail before the submitted patch.
        # This is not an independent bug discovery or proof of safe reuse.
        full=[r["full_seconds"] for r in measured]
        targeted=[r["targeted_seconds"] for r in measured]
        report={
          "schema":"mathgraph.native-verification-cost.v1",
          "repository":"yuin/goldmark-meta","base":BASE,"head":HEAD,
          "measurements":measured,
          "median_full_seconds":statistics.median(full),
          "median_targeted_seconds":statistics.median(targeted),
          "median_execution_difference_seconds":round(statistics.median(full)-statistics.median(targeted),6),
          "observed_execution_reduction_percent":round(100*(1-statistics.median(targeted)/statistics.median(full)),2),
          "baseline":"same source, warmed Go cache, six alternating rounds, -count=1",
          "comparison_boundary":"native test execution only; not measured evidence admission, semantic impact discovery, or selection overhead",
          "base_new_feature_test":"RED_EXPECTED",
          "limitations":["targeted selection authored by researcher using known feature and known test names",
                         "original source tests excluded in targeted arm",
                         "a failure in an excluded test would be missed",
                         "no proof of equivalence of full and targeted assurance",
                         "not real incremental semantic evidence transport",
                         "not an independent customer-value result"],
        }
        OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        print(json.dumps({k:v for k,v in report.items() if "seconds" in k or "percent" in k}))
if __name__=="__main__":main()
