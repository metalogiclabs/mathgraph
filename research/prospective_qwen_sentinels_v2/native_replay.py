#!/usr/bin/env python3
"""Prospectively predeclared, native C and unmodified generated Rust replay."""
import ctypes,hashlib,json,subprocess,sys
from pathlib import Path
from source_oracle import vectors,authorized,census,UINT_MAX

UPSTREAM="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
SOURCES={
 "sorted_minus_one":(
  "data/tutorial_wp/ex-3-binary-search-answer.c","b4f00cac89395f618671bcd73f5b2828e4df3858",
  "transpiled_rust/tutorial_wp/ex-3-binary-search-answer.rs","ca7bb488b2de916812715c790ed3b7cdf8c84e3d"),
 "unsorted_uintmax":(
  "data/tutorial_wp/ex-3-search-answer.c","72d7eafa47c1e4914101ee1a088ffd15688e6369",
  "transpiled_rust/tutorial_wp/ex-3-search-answer.rs","ba64d22cf4f6b6861e0c8af5bb203c47b4fd5fdf")
}

def shell(cmd,**kwargs):
    return subprocess.run(cmd,capture_output=True,text=True,check=True,**kwargs)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exact_blob(root,path,expected):
    actual=shell(["git","-C",str(root),"hash-object",path]).stdout.strip()
    if actual!=expected:raise ValueError("PINNED_INPUT_DRIFT:"+path)

def replay(root,out):
    root,out=Path(root).resolve(),Path(out).resolve()
    if shell(["git","-C",str(root),"rev-parse","HEAD"]).stdout.strip()!=UPSTREAM:
        raise ValueError("UPSTREAM_REVISION_DRIFT")
    if shell(["git","-C",str(root),"status","--porcelain"]).stdout.strip():
        raise ValueError("UPSTREAM_DIRTY")
    out.mkdir(parents=True,exist_ok=True)
    libs={}
    for kind,(cpath,cblob,rpath,rblob) in SOURCES.items():
        exact_blob(root,cpath,cblob);exact_blob(root,rpath,rblob)
        so=out/(kind+".so")
        shell(["cc","-std=c11","-O2","-fPIC","-shared",str(root/cpath),"-o",str(so)])
        lib=ctypes.CDLL(str(so))
        func=getattr(lib,"bsearch" if kind=="sorted_minus_one" else "search")
        func.argtypes=(ctypes.POINTER(ctypes.c_int),
                       ctypes.c_int if kind=="sorted_minus_one" else ctypes.c_uint,
                       ctypes.c_int)
        func.restype=ctypes.c_int if kind=="sorted_minus_one" else ctypes.c_uint
        libs[kind]=func
    first=root/SOURCES["sorted_minus_one"][2]
    second=root/SOURCES["unsorted_uintmax"][2]
    wrapper=out/"rust_harness.rs"
    wrapper.write_text(
      'include!(r#"'+str(first)+'"#);\n'
      'include!(r#"'+str(second)+'"#);\n'
      'use std::io::{self,Read};\n'
      'fn main() {\n'
      ' let mut s=String::new(); io::stdin().read_to_string(&mut s).unwrap();\n'
      ' for line in s.lines() {\n'
      '  let mut it=line.split_whitespace();\n'
      '  let mode=it.next().unwrap();\n'
      '  let n:usize=it.next().unwrap().parse().unwrap();\n'
      '  let key:i32=it.next().unwrap().parse().unwrap();\n'
      '  let arr:Vec<i32>=(0..n).map(|_|it.next().unwrap().parse().unwrap()).collect();\n'
      '  let old=arr.clone();\n'
      '  let got:i64=if mode=="A" { bsearch(&arr,n as i32,key) as i64 } else { search(&arr,n as u32,key) as i64 };\n'
      '  println!("{} {}",got,if arr==old {1} else {0});\n'
      ' }\n'
      '}\n')
    exe=out/"rust_harness"
    try:
        shell(["rustc","--edition","2021","-O",str(wrapper),"-o",str(exe)])
    except subprocess.CalledProcessError as e:
        (out/"rustc.stderr.log").write_text(e.stderr or "")
        report={"verdict":"UNKNOWN_NOT_EXECUTABLE","reason":"UNMODIFIED_TARGET_COMPILATION_FAILED",
                "rustc_error_sha256":sha(out/"rustc.stderr.log")}
        (out/"native_report.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report))
        return report
    allcases=[]
    for kind in ("sorted_minus_one","unsorted_uintmax"):
        for row,key in vectors(kind):
            allcases.append((kind,row,key))
    expected=census()
    if len(allcases)!=sum(expected.values()):raise ValueError("CORPUS_CENSUS_DRIFT")
    encoded="\n".join(" ".join(str(x) for x in
                (("A" if kind=="sorted_minus_one" else "B"),len(row),key,*row))
                for kind,row,key in allcases)+"\n"
    native=shell([str(exe)],input=encoded,timeout=120).stdout.splitlines()
    if len(native)!=len(allcases):raise ValueError("RUST_OUTPUT_CENSUS_MISMATCH")
    observations=[]
    failures={k:[] for k in expected}
    source_errors={k:[] for k in expected}
    for index,((kind,row,key),line) in enumerate(zip(allcases,native)):
        original=(ctypes.c_int*max(1,len(row)))(*row)
        snapshot=list(original)[:len(row)]
        source=int(libs[kind](original,len(row),key))
        source_same=list(original)[:len(row)]==snapshot
        parts=line.split()
        if len(parts)!=2:raise ValueError("RUST_OUTPUT_FORMAT:"+str(index))
        target=int(parts[0]);target_same=parts[1]=="1"
        rec={"index":index,"kind":kind,"row":list(row),"key":key,
             "c":source,"rust":target,"c_unchanged":source_same,
             "rust_unchanged":target_same}
        observations.append(rec)
        if not authorized(kind,row,key,source) or not source_same:source_errors[kind].append(rec)
        if not authorized(kind,row,key,target) or not target_same:failures[kind].append(rec)
    with (out/"observations.jsonl").open("w") as f:
        for record in observations:f.write(json.dumps(record,sort_keys=True)+"\n")
    per_case={}
    for kind in expected:
        per_case[kind]={"count":expected[kind],
          "source_violations":len(source_errors[kind]),
          "target_violations":len(failures[kind]),
          "first_source_counterexample":source_errors[kind][:1],
          "first_target_counterexample":failures[kind][:1],
          "verdict":("REJECTED_SOURCE_BASELINE" if source_errors[kind] else
                     "FINITE_COUNTEREXAMPLE" if failures[kind] else
                     "WARRANTED_BOUNDED_MATCH")}
    report={"protocol":"PREREGISTERED_QWEN_SENTINELS_V2",
            "source_commit":UPSTREAM,"source_blob_ids":{k:v[1] for k,v in SOURCES.items()},
            "target_blob_ids":{k:v[3] for k,v in SOURCES.items()},
            "source_sha256":{k:sha(root/v[0]) for k,v in SOURCES.items()},
            "target_sha256":{k:sha(root/v[2]) for k,v in SOURCES.items()},
            "native_c_compiler":shell(["cc","--version"]).stdout.splitlines()[0],
            "native_rust_compiler":shell(["rustc","--version"]).stdout.strip(),
            "harness_sha256":sha(wrapper),"executable_sha256":sha(exe),
            "observations_sha256":sha(out/"observations.jsonl"),"total_cases":len(observations),
            "cases":per_case}
    (out/"native_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
    return report

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: native_replay.py UPSTREAM_DIR EVIDENCE_DIR")
    verdict=replay(sys.argv[1],sys.argv[2])
    if verdict["verdict"]=="UNKNOWN_NOT_EXECUTABLE":
        raise SystemExit(2)
    if any(v["verdict"]!="WARRANTED_BOUNDED_MATCH" for v in verdict["cases"].values()):
        raise SystemExit(1)
