#!/usr/bin/env python3
"""Authentic source-bound C vs untouched Qwen Rust, finite postcondition check."""
import ctypes,hashlib,json,subprocess,sys
from pathlib import Path
from extractor import packet,all_cases,probes,authorized,manifest
PIN="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
SOURCE_PACKET_SHA="c5bf8a2d62a50f355504578e74c3fe1e80c0d2048776ca937cb02fe8ac0fa583"
TARGET_BLOBS=[
"850ad4aae633bfb4786266d4ac97d9d417688df0",
"302694fffbfb050ab5cab6adafd6624261264bf7",
"5c2fd6e8a1b7bb1b9a21bc2e2121f53564e712e1",
"433019c395bc42ca800c5320ac284f63d4a36d73",
"2e5b9c8bab4bc60cdf4828353ea23b339dfd54f0"]
NAMES=["max","arraymax","areElementsEven","func","arrayDouble"]
def run(command,**opts):
    return subprocess.run(command,capture_output=True,text=True,check=True,**opts)
def hash_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git_hash(root,rel):return run(["git","-C",str(root),"hash-object",rel]).stdout.strip()
def native_c(root,doc,i,out):
    src=root/doc["source"]
    lib=out/("source_"+str(i)+".so")
    run(["cc","-std=c11","-O2","-fPIC","-shared",str(src),"-o",str(lib)])
    handler=getattr(ctypes.CDLL(str(lib)),NAMES[i])
    if i==0:
        handler.argtypes=(ctypes.c_int,ctypes.c_int)
    else:handler.argtypes=(ctypes.POINTER(ctypes.c_int),ctypes.c_int)
    handler.restype=None if i in (3,4) else ctypes.c_int
    return handler
def run_source(func,i,values):
    if i==0:
        return int(func(*values)),None
    a=(ctypes.c_int*len(values))(*values)
    result=func(a,len(values))
    return (int(result) if i not in (3,4) else None),tuple(a)
def rust_wrapper(root,metadata,out):
    implementations=[
       "max(values[0],values[1]) as i64",
       "arraymax(values.as_slice(),values.len() as i32) as i64",
       "areElementsEven(values.as_slice(),values.len() as i32) as i64",
       "{func(values.as_mut_slice(),values.len() as i32);0}",
       "{arrayDouble(values.as_mut_slice(),values.len() as i32);0}"]
    segments=[]
    for i,m in enumerate(metadata):
        target=(root/m["target"]).resolve()
        call=implementations[i]
        # Preserve original Rust exact bytes through include in a module.
        segments.append('mod item'+str(i)+' { include!(r#"'+str(target)+'"#); '
                        'pub fn evaluate(values: &mut Vec<i32>)->i64 {'+call+'} }')
    code="\n".join(segments)+"""
use std::io::{self,Read};
fn main(){
 let mut input=String::new();io::stdin().read_to_string(&mut input).unwrap();
 for line in input.lines(){
  let parts:Vec<&str>=line.split_whitespace().collect();
  let index:usize=parts[0].parse().unwrap();
  let id:usize=parts[1].parse().unwrap();
  let mut values:Vec<i32>=parts[2..].iter().map(|v|v.parse().unwrap()).collect();
  let returned=match id {
"""+ "\n".join("   "+str(i)+"=>item"+str(i)+"::evaluate(&mut values)," for i in range(len(metadata)))+"""
   _=>panic!("bad id")};
  let after=values.iter().map(|v|v.to_string()).collect::<Vec<String>>().join(",");
  println!("{} {} {}",index,returned,after);
 }
}
"""
    path=out/"rust_adapter.rs";path.write_text(code)
    exe=out/"rust_adapter"
    try:run(["rustc","--edition=2021","-O",str(path),"-o",str(exe)])
    except subprocess.CalledProcessError as err:
        (out/"rustc_error.log").write_text(err.stderr or "")
        raise ValueError("UNKNOWN_NOT_EXECUTABLE:rustc:"+str(err.stderr)[-900:])
    return exe,path

def replay(root,out):
    root,out=Path(root).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    if run(["git","-C",str(root),"rev-parse","HEAD"]).stdout.strip()!=PIN:
        raise ValueError("UPSTREAM_REVISION_DRIFT")
    doc=packet(root)
    packet_bytes=(json.dumps(doc,sort_keys=True,indent=2)+"\n").encode()
    if hashlib.sha256(packet_bytes).hexdigest()!=SOURCE_PACKET_SHA:
        raise ValueError("PREUNBLIND_SOURCE_ONLY_PACKET_DRIFT")
    (out/"SOURCE_ONLY.json").write_bytes(packet_bytes)
    data=doc["cases"]
    if len(data)!=5 or any(i["status"]!="SOURCE_CONTRACT_RECOGNIZED" for i in data):
        raise ValueError("SOURCE_CONTRACT_NOT_RECOGNIZED")
    for i,item in enumerate(data):
        if git_hash(root,item["target"])!=TARGET_BLOBS[i]:
            raise ValueError("PUBLISHED_RUST_CHANGED:"+item["target"])
    if run(["git","-C",str(root),"status","--porcelain"]).stdout.strip():
        raise ValueError("PUBLIC_UPSTREAM_DIRTY")
    c_functions=[native_c(root,item,i,out) for i,item in enumerate(data)]
    try:executable,wrapper=rust_wrapper(root,data,out)
    except ValueError as err:
        report={"status":"UNKNOWN_NOT_EXECUTABLE","reason":str(err)}
        (out/"NATIVE_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report));return report
    enumerated=[]
    for i,item in enumerate(data):
        family=item["family"]; probelist={tuple(x) for x in item["probe_inputs"]}
        for vals in all_cases(family):
            enumerated.append((i,tuple(vals),tuple(vals) in probelist))
    if len(enumerated)!=2394 or sum(p for _,_,p in enumerated)!=15:
        raise ValueError("FROZEN_CORPUS_INCOMPLETE")
    payload="\n".join(" ".join(map(str,(j,i,*vals))) for j,(i,vals,probe) in enumerate(enumerated))+"\n"
    try:rust_lines=run([str(executable)],input=payload,timeout=120).stdout.splitlines()
    except subprocess.CalledProcessError as err:
        (out/"runtime_error.log").write_text((err.stderr or "")+"\n"+(err.stdout or ""))
        report={"status":"UNKNOWN_NOT_EXECUTABLE","reason":"RUST_RUNTIME_FAILED"}
        (out/"NATIVE_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report));return report
    if len(rust_lines)!=len(enumerated):raise ValueError("RUST_OUTPUT_COUNT_CHANGED")
    results=[{"source":d["source"],"family":d["family"],
               "source_violations":0,"target_violations":0,"probe_target_violations":0,
               "differential_changes":0,"cases":0,"first_counterexample":None} for d in data]
    rows=[]
    for j,((i,values,probe),line) in enumerate(zip(enumerated,rust_lines)):
        parts=line.split(maxsplit=2)
        if len(parts)!=3 or int(parts[0])!=j:raise ValueError("RUST_OUTPUT_WRONG_ORDER")
        rest=tuple(int(s) for s in parts[2].split(",")) if parts[2] else tuple()
        value=int(parts[1]) if i not in (3,4) else None
        src_result,src_after=run_source(c_functions[i],i,values)
        family=data[i]["family"]
        src_ok=authorized(family,values,src_after,src_result)
        rust_ok=authorized(family,values,rest if i!=0 else None,value)
        row={"index":j,"case":i,"before":list(values),"source_return":src_result,"target_return":value,
            "source_after":list(src_after) if src_after is not None else None,
            "target_after":list(rest) if i!=0 else None,"probe":probe,"source_authorized":src_ok,
            "target_authorized":rust_ok}
        rows.append(row)
        record=results[i];record["cases"]+=1
        if not src_ok:record["source_violations"]+=1
        if not rust_ok:record["target_violations"]+=1
        if not rust_ok and probe:record["probe_target_violations"]+=1
        if src_result!=value or (src_after is not None and src_after!=rest):
            record["differential_changes"]+=1
        if (not src_ok or not rust_ok) and record["first_counterexample"] is None:
            record["first_counterexample"]=row
    log=out/"OBSERVATIONS.jsonl"
    with log.open("w") as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True)+"\n")
    for item in results:
        item["verdict"]=("REJECTED_SOURCE_BASELINE" if item["source_violations"] else
                         "FINITE_COUNTEREXAMPLE" if item["target_violations"] else "WARRANTED_BOUNDED_MATCH")
    report={"status":"FINISHED_BOUNDED_HOLDOUT","source_only_packet_sha256":SOURCE_PACKET_SHA,
            "upstream_revision":PIN,"source_blobs":[x["blob"] for x in data],
            "target_blobs":TARGET_BLOBS,"case_reports":results,"total_cases":len(rows),
            "total_probes":sum(x["probe_target_violations"] for x in results)+15-sum(x["probe_target_violations"] for x in results),
            "native_observations_sha256":hash_file(log),
            "rust_adapter_sha256":hash_file(wrapper),
            "compiler_versions":{"cc":run(["cc","--version"]).stdout.splitlines()[0],
                                 "rustc":run(["rustc","--version"]).stdout.strip()},
            "limitations":["Five nonrandom hand-chosen, exact-pattern supported source contracts",
                           "Source-only generated finite probes, not universal equivalence proof",
                           "Partial ACSL postcondition does not authorize guessing a missing frame",
                           "Conventional reviewer has equal C/Rust/source information; no superiority assumed"]}
    (out/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"total_cases":report["total_cases"],
          "per_case":[{"name":x["source"],"verdict":x["verdict"],"target_violations":x["target_violations"],
                       "probes_with_target_violations":x["probe_target_violations"]} for x in results]},sort_keys=True))
    return report
if __name__=="__main__":
    result=replay(sys.argv[1],sys.argv[2])
    if result["status"]!="FINISHED_BOUNDED_HOLDOUT":raise SystemExit(2)
    if any(x["verdict"]!="WARRANTED_BOUNDED_MATCH" for x in result["case_reports"]):
        raise SystemExit(1)
