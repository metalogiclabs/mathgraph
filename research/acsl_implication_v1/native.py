#!/usr/bin/env python3
"""Native source-authoritative C vs unmodified Qwen Rust on sealed ACSL clauses."""
import ctypes,hashlib,json,subprocess,sys
from pathlib import Path
from normalizer import discover,inputs,probes,authorized,manifest

PACKET_SHA="e70b963a6b84d06fcbe60bc95d5caa6e4d60389439d20c9d503ab18609fba01e"
REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
TARGET_BLOBS={
 "transpiled_rust/frama_c_problems/max.rs":"302694fffbfb050ab5cab6adafd6624261264bf7",
 "transpiled_rust/frama_c_problems/check_evens_in_array.rs":"5c2fd6e8a1b7bb1b9a21bc2e2121f53564e712e1",
 "transpiled_rust/frama_c_problems/replace_evens.rs":"433019c395bc42ca800c5320ac284f63d4a36d73",
 "transpiled_rust/frama_c_problems/array_double.rs":"2e5b9c8bab4bc60cdf4828353ea23b339dfd54f0",
 "transpiled_rust/frama_c_problems/reset_1st.rs":"b22649522e7f9ebac53a08f01ac2328ec9165ac9"}
def run(args,**kw):return subprocess.run(args,check=True,capture_output=True,text=True,**kw)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(root,p):return run(["git","-C",str(root),"hash-object",str(p)]).stdout.strip()
def rust_source(target,index,entry):
    name=entry["function"]; mutable=entry["return_type"]=="void"
    param="&mut row[..]" if mutable else "&row[..]"
    invoke=(name+"("+param+",n)" + ("; return 0i64;" if mutable else " as i64"))
    return ("mod task_"+str(index)+" {\n"+
            'include!(r#"'+str(target.resolve())+'"#);\n'+
            "pub fn eval(row:&mut Vec<i32>)->i64 {let n=row.len() as i32;\n"+
            (invoke if mutable else "return "+invoke+";")+"\n}\n}\n")
def execute(upstream,out):
    upstream,out=Path(upstream).resolve(),Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if run(["git","-C",str(upstream),"rev-parse","HEAD"]).stdout.strip()!=REV:
        raise ValueError("UPSTREAM_REVISION_DRIFT")
    if run(["git","-C",str(upstream),"status","--porcelain"]).stdout.strip():
        raise ValueError("UPSTREAM_DIRTY")
    packet=discover(upstream)
    frozen=(json.dumps(packet,sort_keys=True,indent=2)+"\n").encode()
    if hashlib.sha256(frozen).hexdigest()!=PACKET_SHA:raise ValueError("SOURCE_ONLY_PACKET_DRIFT")
    (out/"SOURCE_ONLY_PACKET.json").write_bytes(frozen)
    models=packet["cases"]
    compiled=[];wrappers=[];targets={}
    for i,entry in enumerate(models):
        target=entry["target"]
        if blob(upstream,target)!=TARGET_BLOBS[target]:raise ValueError("TARGET_SHA_DRIFT:"+target)
        targets[target]={"blob":TARGET_BLOBS[target],"sha256":digest(upstream/target)}
        if entry["status"]!="DISCOVERED_BOUNDED_CONTRACT":
            compiled.append(None);continue
        src=upstream/entry["source"];libpath=out/("source_"+str(i)+".so")
        try:
            run(["cc","-std=c11","-O2","-fPIC","-shared",str(src),"-o",str(libpath)])
        except subprocess.CalledProcessError as e:
            status={"status":"REJECTED_SOURCE_BASELINE","source":entry["source"],"compiler_error":e.stderr[-3000:]}
            (out/"NATIVE_REPORT.json").write_text(json.dumps(status,indent=2));return status
        lib=ctypes.CDLL(str(libpath))
        fn=getattr(lib,entry["function"])
        fn.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_int]
        fn.restype=ctypes.c_int if entry["return_type"]=="int" else None
        compiled.append(fn)
        wrappers.append(rust_source(upstream/target,i,entry))
    rust=out/"rust_harness.rs"
    rust.write_text("\n".join(wrappers)+
      'use std::io::{self,Read};\nfn main(){let mut text=String::new();\n'
      'io::stdin().read_to_string(&mut text).unwrap();\n'
      'for line in text.lines(){let mut it=line.split_whitespace();\n'
      'let id:usize=it.next().unwrap().parse().unwrap();\n'
      'let num:usize=it.next().unwrap().parse().unwrap();\n'
      'let n:usize=it.next().unwrap().parse().unwrap();\n'
      'let mut row:Vec<i32>=(0..n).map(|_|it.next().unwrap().parse().unwrap()).collect();\n'
      'let result=match id {\n'+
      "\n".join(" "+str(i)+"=>task_"+str(i)+"::eval(&mut row)," for i,e in enumerate(models) if e["status"]=="DISCOVERED_BOUNDED_CONTRACT")+
      '\n_=>panic!("unknown case")};\n'
      'print!("{} {}",num,result);\n'
      'for value in row{print!(" {}",value);}\nprintln!();\n}\n}\n')
    exe=out/"rust_harness"
    try:run(["rustc","--edition=2021","-O",str(rust),"-o",str(exe)])
    except subprocess.CalledProcessError as e:
        (out/"rustc.log").write_text(e.stderr or "")
        status={"status":"UNKNOWN_NOT_EXECUTABLE","rustc_log_sha256":digest(out/"rustc.log")}
        (out/"NATIVE_REPORT.json").write_text(json.dumps(status,indent=2));return status
    queued=[];outcomes=[]
    for i,entry in enumerate(models):
        if entry["status"]!="DISCOVERED_BOUNDED_CONTRACT":
            outcomes.append({"source":entry["source"],"family":None,
                   "status":"UNKNOWN_UNSUPPORTED","reason":entry["reason"],
                   "full_test_count":0,"probe_count":0,"source_bad":0,"rust_bad":0})
            continue
        total=list(inputs(entry))
        extras=probes(entry)
        probe_set=set(extras)
        queued_set=set(total)
        rows=total+[tuple(row) for row in extras if tuple(row) not in queued_set]
        outcomes.append({"source":entry["source"],"family":entry["family"],
            "status":"WARRANTED_BOUNDED_MATCH","full_test_count":len(total),
            "probe_count":len(extras),"source_bad":0,"rust_bad":0,
            "source_target_differences":0,"probe_bad":0,"first_issue":None})
        for row in rows:queued.append((i,tuple(row),tuple(row) in probe_set))
    data="\n".join(" ".join(str(x) for x in (i,j,len(row),*row)) for j,(i,row,_) in enumerate(queued))+"\n"
    try:stdout=run([str(exe)],input=data,timeout=150).stdout
    except subprocess.CalledProcessError as e:
        (out/"runtime.log").write_text((e.stdout or "")+"\n"+(e.stderr or ""))
        status={"status":"UNKNOWN_NOT_EXECUTABLE","runtime_log_sha256":digest(out/"runtime.log")}
        (out/"NATIVE_REPORT.json").write_text(json.dumps(status,indent=2));return status
    lines=stdout.splitlines()
    if len(lines)!=len(queued):raise ValueError("INCOMPLETE_RUNTIME_CASE_CENSUS")
    observations=[]
    for j,((i,row,is_probe),line) in enumerate(zip(queued,lines)):
        fields=[int(x) for x in line.split()]
        if len(fields)!=2+len(row) or fields[0]!=j:raise ValueError("INVALID_RUST_RECORD:"+str(j))
        entry=models[i];result=outcomes[i]
        typed=(ctypes.c_int*max(1,len(row)))(*row)
        v=compiled[i](typed,len(row))
        c_post=tuple(typed)[:len(row)]
        r_post=tuple(fields[2:])
        c_result=(int(v) if entry["return_type"]=="int" else None)
        r_result=(int(fields[1]) if entry["return_type"]=="int" else None)
        c_good=authorized(entry,row,c_post,c_result)
        r_good=authorized(entry,row,r_post,r_result)
        issue={"case":i,"index":j,"input":list(row),"c_result":c_result,
               "rust_result":r_result,"c_post":list(c_post),"rust_post":list(r_post),
               "probe":is_probe,"source_ok":c_good,"target_ok":r_good}
        observations.append(issue)
        if not c_good:result["source_bad"]+=1
        if not r_good:
            result["rust_bad"]+=1
            if is_probe:result["probe_bad"]+=1
        if c_result!=r_result or c_post!=r_post:result["source_target_differences"]+=1
        if (not c_good or not r_good) and result["first_issue"] is None:
            result["first_issue"]=issue
    with (out/"observations.jsonl").open("w") as f:
        for obj in observations:f.write(json.dumps(obj,sort_keys=True)+"\n")
    for o in outcomes:
        if o["status"]=="UNKNOWN_UNSUPPORTED":continue
        o["status"]=("REJECTED_SOURCE_BASELINE" if o["source_bad"] else
                     "FINITE_COUNTEREXAMPLE" if o["rust_bad"] else
                     "WARRANTED_BOUNDED_MATCH")
    report={"status":"COMPLETE_BOUNDED_NATIVE_REPLAY","packet_sha256":PACKET_SHA,
            "upstream":REV,"target_hashes":targets,
            "total_tests":len(observations),
            "full_source_only_tests":sum(o["full_test_count"] for o in outcomes),
            "probes":sum(o["probe_count"] for o in outcomes),
            "observations_sha256":digest(out/"observations.jsonl"),
            "rustc_version":run(["rustc","--version"]).stdout.strip(),
            "cc_version":run(["cc","--version"]).stdout.splitlines()[0],
            "cases":outcomes,
            "limits":["Finite source-authorized domain only","Four bounded syntax templates only",
                      "No contract assertion for unsupported old-state case",
                      "Unmodified Rust target functions; wrappers only adapt input/output types",
                      "No superiority or formal universal refinement established"]}
    (out/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"tests":report["total_tests"],
          "cases":[{k:x.get(k) for k in ("source","status","source_bad","rust_bad","probe_bad")}
                   for x in outcomes]},sort_keys=True))
    return report
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("native.py UPSTREAM_DIR EVIDENCE_DIR")
    report=execute(sys.argv[1],sys.argv[2])
    if report["status"]!="COMPLETE_BOUNDED_NATIVE_REPLAY":raise SystemExit(2)
    if any(c["status"] in ("REJECTED_SOURCE_BASELINE","FINITE_COUNTEREXAMPLE") for c in report["cases"]):
        raise SystemExit(1)
