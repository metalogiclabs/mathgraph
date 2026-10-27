"""Independently authored contract comparator (no MathGraph oracle import)."""
import json,sys
from pathlib import Path
COUNTS={"recursive_search":5467,"binary_search":1764}
def compare(folder):
    folder=Path(folder)
    data=[json.loads(x) for x in (folder/"observations.jsonl").read_text().splitlines()]
    if len(data)!=7231:raise ValueError("INCOMPLETE_CORPUS")
    report={}
    for name,count in COUNTS.items():
        cases=[x for x in data if x["kind"]==name]
        if len(cases)!=count:raise ValueError("MISSING_CASE")
        violations=[]
        for x in cases:
            indices=[i for i,v in enumerate(x["array"]) if v==x["key"]]
            expected=4294967295 if name=="recursive_search" else -1
            source_ok=(x["c"] in indices if indices else x["c"]==expected)
            translated_ok=(x["rust"] in indices if indices else x["rust"]==expected)
            if not source_ok or not translated_ok or not x["c_unchanged"] or not x["rust_unchanged"]:
                violations.append(x)
        report[name]={"cases":count,"violations":len(violations),
                      "verdict":"BASELINE_TIE" if not violations else "BASELINE_FOUND_MISMATCH"}
    (folder/"baseline_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
    if any(x["violations"] for x in report.values()):raise SystemExit(1)
if __name__=="__main__":compare(sys.argv[1])
