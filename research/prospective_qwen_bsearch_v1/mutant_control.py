#!/usr/bin/env python3
"""POST-UNBLIND diagnostic mutation; never classify as a genuine migration bug."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from oracle import cases,admissible,EXPECTED_COUNT

UPSTREAM="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
TARGET="transpiled_rust/tutorial_wp/ex-4-binary-search-answer.rs"
BLOB="2286ec1d646fd1c5ae90a5aafe95ff48d2420188"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def invoke(cmd,**kw):return subprocess.run(cmd,check=True,capture_output=True,text=True,**kw)

def run(root,evidence):
    root,evidence=Path(root).resolve(),Path(evidence).resolve()
    if invoke(["git","-C",str(root),"hash-object",TARGET]).stdout.strip()!=BLOB:
        raise ValueError("TARGET_BYTES_DRIFT")
    authentic=(root/TARGET).read_text()
    boundary="\n    len\n}"
    if authentic.count(boundary)!=1:
        raise ValueError("SENTINEL_MUTATION_SITE_NOT_UNIQUE")
    altered=authentic.replace(boundary,"\n    0\n}")
    out=evidence/"synthetic_diagnostic"
    out.mkdir(parents=True,exist_ok=True)
    synthetic=out/"synthetic_wrong_sentinel.rs"
    synthetic.write_text(altered)
    wrapper=(evidence/"rust_runtime_harness.rs").read_text()
    if wrapper.count(str((root/TARGET).resolve()))!=1:
        raise ValueError("ORIGINAL_HARNESS_PATH_MISSING")
    harness=out/"synthetic_harness.rs"
    harness.write_text(wrapper.replace(str((root/TARGET).resolve()),str(synthetic)))
    exe=out/"synthetic_harness"
    invoke(["rustc","--edition","2021","-O",str(harness),"-o",str(exe)])
    examples=list(cases())
    if len(examples)!=EXPECTED_COUNT:
        raise AssertionError("FROZEN_CASES_CHANGED")
    input_data="\n".join(" ".join(map(str,(len(row),key,*row))) for row,key in examples)+"\n"
    output=invoke([str(exe)],input=input_data,timeout=90).stdout.splitlines()
    if len(output)!=EXPECTED_COUNT:
        raise ValueError("SYNTHETIC_RUNTIME_RESULT_COUNT")
    errors=[];record=[]
    for i,((row,key),line) in enumerate(zip(examples,output)):
        v=line.split()
        if len(v)!=2:raise ValueError("BAD_LINE")
        value=int(v[0]);unchanged=v[1]=="1"
        item={"index":i,"array":list(row),"key":key,"synthetic_result":value,"unchanged":unchanged}
        record.append(item)
        if not admissible(row,key,value) or not unchanged:errors.append(item)
    with (out/"observations.jsonl").open("w") as stream:
        for item in record:stream.write(json.dumps(item,sort_keys=True)+"\n")
    report={"status":"EXPECTED_SYNTHETIC_VIOLATION_DETECTED" if errors else "FAILED_TO_DETECT_SYNTHETIC_BUG",
            "source_is_unchanged":True,"synthetic_only":True,
            "control":"replace final not-found len return with 0 in disposable Rust copy",
            "case_count":len(record),"violation_count":len(errors),
            "first_violation":errors[0] if errors else None,
            "authentic_target_sha256":sha(root/TARGET),
            "synthetic_target_sha256":sha(synthetic)}
    (out/"diagnostic.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
    if not errors:raise SystemExit(1)
    return report
if __name__=="__main__":run(sys.argv[1],sys.argv[2])
