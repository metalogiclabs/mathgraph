#!/usr/bin/env python3
"""Native replay of preregistered Qwen Rust and original C, no target edits."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from oracle import cases,admissible,EXPECTED_COUNT

UPSTREAM="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
C_REL="data/tutorial_wp/ex-4-binary-search-answer.c"
R_REL="transpiled_rust/tutorial_wp/ex-4-binary-search-answer.rs"
C_BLOB="c31d685b159f072d75212aa48ba98e1e19a0f207"
R_BLOB="2286ec1d646fd1c5ae90a5aafe95ff48d2420188"

def cmd(args,**kwargs):
    return subprocess.run(args,check=True,capture_output=True,text=True,**kwargs)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check_git(root,rel,blob):
    observed=cmd(["git","-C",str(root),"hash-object",rel]).stdout.strip()
    if observed!=blob:raise ValueError("SOURCE_BYTE_DRIFT:"+rel)

def replay(root,out):
    root,out=Path(root).resolve(),Path(out).resolve()
    if cmd(["git","-C",str(root),"rev-parse","HEAD"]).stdout.strip()!=UPSTREAM:
        raise ValueError("UPSTREAM_REVISION_MISMATCH")
    check_git(root,C_REL,C_BLOB);check_git(root,R_REL,R_BLOB)
    if cmd(["git","-C",str(root),"status","--porcelain"]).stdout.strip():
        raise ValueError("UPSTREAM_NOT_CLEAN")
    out.mkdir(parents=True,exist_ok=True)
    c_lib=out/"original_bsearch.so"
    cc=cmd(["cc","-std=c11","-O2","-fPIC","-shared",str(root/C_REL),"-o",str(c_lib)])
    lib=ctypes.CDLL(str(c_lib))
    f=lib.bsearch
    f.argtypes=(ctypes.POINTER(ctypes.c_int),ctypes.c_size_t,ctypes.c_int)
    f.restype=ctypes.c_size_t
    target=root/R_REL
    wrapper=out/"rust_runtime_harness.rs"
    wrapper.write_text(
        'include!(r#"'+str(target)+'"#);\n'
        'use std::io::{self, Read};\n'
        'fn main() {\n'
        ' let mut s = String::new(); io::stdin().read_to_string(&mut s).unwrap();\n'
        ' for line in s.lines() {\n'
        '   let mut it = line.split_whitespace();\n'
        '   let n: usize = it.next().unwrap().parse().unwrap();\n'
        '   let k: i32 = it.next().unwrap().parse().unwrap();\n'
        '   let array: Vec<i32> = (0..n).map(|_| it.next().unwrap().parse().unwrap()).collect();\n'
        '   let before = array.clone();\n'
        '   let r = bsearch(&array,n,k);\n'
        '   println!("{} {}",r,if array==before {1} else {0});\n'
        ' }\n'
        '}\n'
    )
    exe=out/"rust_runtime_harness"
    rust=cmd(["rustc","--edition","2021","-O",str(wrapper),"-o",str(exe)])
    vectors=list(cases())
    if len(vectors)!=EXPECTED_COUNT:raise ValueError("FROZEN_CASE_CENSUS")
    encoded="\n".join(" ".join(str(x) for x in (len(row),key,*row)) for row,key in vectors)+"\n"
    run=cmd([str(exe)],input=encoded,timeout=90)
    output=run.stdout.splitlines()
    if len(output)!=EXPECTED_COUNT:raise ValueError("RUST_OUTPUT_COUNT:"+str(len(output)))
    observations=[]; bad_source=[];bad_target=[]
    for index,((row,key),line) in enumerate(zip(vectors,output)):
        original=(ctypes.c_int*max(1,len(row)))(*row)
        snapshot=list(original)[:len(row)]
        c_value=int(f(original,len(row),key))
        c_unchanged=list(original)[:len(row)]==snapshot
        parts=line.split()
        if len(parts)!=2:raise ValueError("MALFORMED_RUST_RESPONSE:"+str(index))
        rust_value=int(parts[0]);rust_unchanged=parts[1]=="1"
        valid_source=admissible(row,key,c_value) and c_unchanged
        valid_target=admissible(row,key,rust_value) and rust_unchanged
        data={"index":index,"array":list(row),"key":key,"c":c_value,"rust":rust_value,
              "c_unchanged":c_unchanged,"rust_unchanged":rust_unchanged}
        observations.append(data)
        if not valid_source:bad_source.append(data)
        if not valid_target:bad_target.append(data)
    with (out/"observations.jsonl").open("w") as stream:
        for record in observations:stream.write(json.dumps(record,sort_keys=True)+"\n")
    report={"protocol":"PREREGISTERED_QWEN_BSEARCH_SENTINEL_V1",
      "upstream":UPSTREAM,"source_blob_sha":C_BLOB,"target_blob_sha":R_BLOB,
      "source_sha256":sha(root/C_REL),"target_sha256":sha(root/R_REL),
      "case_count":len(observations),"source_violation_count":len(bad_source),
      "target_violation_count":len(bad_target),
      "first_source_counterexamples":bad_source[:3],"first_target_counterexamples":bad_target[:3],
      "rustc_version":cmd(["rustc","--version"]).stdout.strip(),
      "cc_version":cmd(["cc","--version"]).stdout.splitlines()[0],
      "harness_sha256":sha(wrapper),"rust_binary_sha256":sha(exe),
      "verdict":"REJECTED_SOURCE_BASELINE" if bad_source else
                "FINITE_COUNTEREXAMPLE" if bad_target else "WARRANTED_BOUNDED_MATCH"}
    (out/"native_report.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
    if bad_source or bad_target:raise SystemExit(1)
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: python native_replay.py UPSTREAM_ROOT EVIDENCE_DIR")
    replay(sys.argv[1],sys.argv[2])
