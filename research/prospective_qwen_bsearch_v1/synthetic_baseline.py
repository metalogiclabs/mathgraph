#!/usr/bin/env python3
"""Separate source-aware conventional evaluator of POST-UNBLIND synthetic controls."""
from pathlib import Path
import json,sys
def audit(evidence):
    root=Path(evidence)/"synthetic_diagnostic"
    items=[json.loads(line) for line in (root/"observations.jsonl").read_text().splitlines()]
    if len(items)!=1764:raise ValueError("DIAGNOSTIC_COUNT_CHANGED")
    failures=[]
    for x in items:
        choices=[i for i,v in enumerate(x["array"]) if v==x["key"]]
        okay=(x["synthetic_result"] in choices) if choices else (x["synthetic_result"]==len(x["array"]))
        if not okay or not x["unchanged"]:failures.append(x)
    result={"verdict":"BASELINE_DETECTS_SYNTHETIC_SENTINEL_DEFECT" if failures else "FAILED_CONTROL",
            "cases":len(items),"failures":len(failures),"first":failures[:1],
            "no_real_migration_defect_claim":True}
    (root/"synthetic_baseline.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    if not failures:raise SystemExit(1)
if __name__=="__main__":audit(sys.argv[1])
