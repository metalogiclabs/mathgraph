#!/usr/bin/env python3
"""Equal-runner scoped verifier vs existing broad targeted regression benchmark."""
import json, os, statistics, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name("benchmark.json")
BROAD=[
 "conformance/protocol_v1/test_consumer.py",
 "conformance/resolve_v1/test_consumer.py",
 "tests/test_mathgraph_resolve_publication_v1.py",
 "tests/test_mathgraph_warrant_resolution_core.py",
 "tests/test_mathgraph_living_warrants_v1.py",
]
CHECKER=["research/property_preservation_v2/checker.py"]
def execute(which):
    argv=([sys.executable,"research/property_preservation_v2/checker.py"]
        if which=="checker" else [sys.executable,"-m","pytest","-q",*BROAD])
    t=time.perf_counter()
    p=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,text=True)
    return {"kind":which,"elapsed_seconds":round(time.perf_counter()-t,6),
            "ok":p.returncode==0,"exit":p.returncode,
            "tail":p.stdout.strip().splitlines()[-9:]}
def main():
    trials=[]
    # Both paths receive the identical current checkout, same Python and CI runner,
    # and already-provisioned pinned external fixtures. Alternate order.
    for i in range(5):
        for label in (("checker","broad") if i%2==0 else ("broad","checker")):
            result=execute(label)
            trials.append(result)
            if not result["ok"]:
                OUT.write_text(json.dumps({"status":"FAIL_CLOSED","trials":trials},indent=2)+"\n")
                raise RuntimeError(label+" failed:\n"+"\n".join(result["tail"]))
    times={label:[x["elapsed_seconds"] for x in trials if x["kind"]==label]
           for label in ("checker","broad")}
    summaries={k:{"median_seconds":round(statistics.median(v),6),
                 "mean_seconds":round(statistics.mean(v),6),
                 "min_seconds":min(v),"max_seconds":max(v)}
               for k,v in times.items()}
    scoped_ratio=summaries["broad"]["median_seconds"]/summaries["checker"]["median_seconds"]
    result={"status":"PASS_PROPERTY_SCOPED_COST_MEASUREMENT",
      "repeat_pairs":5,"runs":trials,"summaries":summaries,
      "relative_median_broad_over_checker":round(scoped_ratio,3),
      "scope_caveat":"checker qualifies finite predicate only, broad suite checks more properties",
      "comparison":"INVALID_FOR_GLOBAL_RELEASE_SUBSTITUTION",
      "fixture_time_and_ci_startup":"NOT_CHARGED_EQUAL_SETUP",
      "postdecision_broad_audit":"SAME_5_BROAD_RUNS_INCLUDED_IN_EXPERIMENT_COST",
      "full_run_cost_note":"research qualification ran BOTH methods, no actual end-to-end cost reduction"}
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":result["status"],"median_seconds":summaries,
      "speed_ratio":result["relative_median_broad_over_checker"],
      "comparison":result["comparison"]},sort_keys=True))
if __name__=="__main__":main()
