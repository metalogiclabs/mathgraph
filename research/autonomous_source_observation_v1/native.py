#!/usr/bin/env python3
"""Native execution of untouched C and Qwen Rust against source-generated probes.

No guessed specification for unsupported contract shape. Source contracts,
function names, length/key argument order and corpus from preregistered Python.
Rust ABI types are inspected solely to compile an input/output adapter.
"""
import ctypes,hashlib,json,subprocess,sys,re
from pathlib import Path
from discover import extract,cases,authorized,manifest,function_signature

REVISION="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
EXPECTED_PACKET_SHA="93d37bd442b74d1710ec93abd52f2671b3f3188ff9ea19714c40a57ceb9531f3"

def command(args,**kw):return subprocess.run(args,capture_output=True,text=True,check=True,**kw)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tracked_sha(root,path):
    return command(["git","-C",str(root),"hash-object",path]).stdout.strip()
def native_function(csource,source_path,output_dir,index):
    sig=function_signature(csource)
    libpath=output_dir/("original_"+str(index)+".so")
    command(["cc","-std=c11","-O2","-fPIC","-shared",str(source_path),"-o",str(libpath)])
    f=getattr(ctypes.CDLL(str(libpath)),sig["function"])
    f.argtypes=[ctypes.POINTER(ctypes.c_int) if p["pointer"] else
                ctypes.c_size_t if p["unsigned"] else ctypes.c_int
                for p in sig["parameters"]]
    f.restype=ctypes.c_size_t if sig["returns_unsigned"] else ctypes.c_int
    return sig,f
def rust_adapter(rust_source,rust_path,sig,index):
    name=sig["function"]
    match=re.search(r"\bfn\s+"+re.escape(name)+r"\s*\((.*?)\)\s*->\s*(\w+)\s*\{",rust_source,re.S)
    if not match:raise ValueError("RUST_ABI_UNSUPPORTED:"+rust_path.name)
    tokens=[t.strip() for t in match.group(1).split(",")]
    if len(tokens)!=3:raise ValueError("RUST_PARAMETER_ARITY")
    types=[t.split(":",1)[1].strip() for t in tokens if ":" in t]
    if len(types)!=3:raise ValueError("RUST_PARAMETER_GRAMMAR")
    positions=[]
    for ix,param in enumerate(sig["parameters"]):
        t=types[ix]
        if param["pointer"]:
            if t not in ("&[i32]","&mut [i32]"):raise ValueError("RUST_POINTER_ADAPTER_UNSUPPORTED:"+t)
            if t=="&mut [i32]":raise ValueError("C_MUTABLE_TO_RUST_MUTABLE_DISALLOWED")
            positions.append("row")
        else:
            if t not in ("i32","u32","usize"):raise ValueError("RUST_SCALAR_TYPE_UNSUPPORTED:"+t)
            if param["name"] in ("n","len","length"):
                positions.append("row.len() as "+t)
            else:
                positions.append("key as "+t)
    # Rust body is copied verbatim by include, no semantic repairs.
    return ('mod task_'+str(index)+' {\n'+
            ' include!(r#"'+str(rust_path.resolve())+'"#);\n'+
            ' pub fn evaluate(row:&[i32],key:i32)->i64 {\n'+
            '  '+name+'('+",".join(positions)+') as i64\n }\n}\n')

def execute(upstream,output):
    upstream,output=Path(upstream).resolve(),Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    if command(["git","-C",str(upstream),"rev-parse","HEAD"]).stdout.strip()!=REVISION:
        raise ValueError("REPOSITORY_REVISION_CHANGED")
    packet=extract(upstream)
    packet_bytes=(json.dumps(packet,sort_keys=True,indent=2)+"\n").encode()
    if hashlib.sha256(packet_bytes).hexdigest()!=EXPECTED_PACKET_SHA:
        raise ValueError("SOURCE_ONLY_PACKET_CHANGED")
    (output/"frozen_source_packet.json").write_bytes(packet_bytes)
    entries=packet["discovery"]; docs=manifest()["cases"]
    if len(entries)!=5:raise ValueError("SOURCE_HOLDOUT_SET_CHANGED")
    adapters=[]; c_functions=[];target_info=[]
    for i,(entry,m) in enumerate(zip(entries,docs)):
        cpath=upstream/m["c"];rpath=upstream/m["target"]
        if tracked_sha(upstream,m["c"])!=m["c_blob"]:raise ValueError("PINNED_SOURCE_CHANGED")
        sig,func=native_function(cpath.read_text(),cpath,output,i)
        c_functions.append((sig,func))
        if not rpath.is_file():raise ValueError("HELDOUT_TARGET_MISSING:"+m["target"])
        code=rpath.read_text()
        adapters.append(rust_adapter(code,rpath,sig,i))
        target_info.append({"source":m["c"],"target":m["target"],
                            "source_blob":m["c_blob"],"target_blob":tracked_sha(upstream,m["target"]),
                            "source_sha256":digest(cpath),"target_sha256":digest(rpath)})
    if command(["git","-C",str(upstream),"status","--porcelain"]).stdout.strip():
        raise ValueError("UPSTREAM_TREE_NOT_CLEAN")
    wrapper=output/"rust_io_adapter.rs"
    wrapper.write_text("\n".join(adapters)+
        'use std::io::{self,Read};\n'
        'fn main(){\n'
        ' let mut s=String::new();io::stdin().read_to_string(&mut s).unwrap();\n'
        ' for line in s.lines(){\n'
        '  let mut i=line.split_whitespace();\n'
        '  let tid:usize=i.next().unwrap().parse().unwrap();\n'
        '  let idx:usize=i.next().unwrap().parse().unwrap();\n'
        '  let n:usize=i.next().unwrap().parse().unwrap();\n'
        '  let key:i32=i.next().unwrap().parse().unwrap();\n'
        '  let row:Vec<i32>=(0..n).map(|_|i.next().unwrap().parse().unwrap()).collect();\n'
        '  let before=row.clone();\n'
        '  let result=match tid {\n'
        +"\n".join("   "+str(j)+"=>task_"+str(j)+"::evaluate(&row,key)," for j in range(len(entries)))+
        '\n   _=>panic!("unknown task")};\n'
        '  println!("{} {} {}",idx,result,if row==before {1} else {0});\n'
        ' }\n}\n')
    exe=output/"rust_io_adapter"
    try:
        build=command(["rustc","--edition=2021","-O",str(wrapper),"-o",str(exe)])
    except subprocess.CalledProcessError as e:
        (output/"rust_compile.log").write_text(e.stderr or "")
        result={"status":"UNKNOWN_NOT_EXECUTABLE","compile_failure":(e.stderr or "")[-3000:]}
        (output/"NATIVE_REPORT.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print(json.dumps(result,sort_keys=True));return result

    observations=[]
    queue=[]
    case_totals=[]
    for i,entry in enumerate(entries):
        if entry["status"]=="DISCOVERED_BOUNDED_CONTRACT":
            # Domain strictly from source-generated packet, not target code.
            allrows=list(cases(entry,full=True))
            probe_set={(tuple(x["array"]),x["key"]) for x in entry["probes"]}
        else:
            # Unsupported source: record differential-only evidence but
            # DO NOT authorize claim equivalence by invented contract.
            vals=tuple(manifest()["domain"]["values"])
            ks=tuple(manifest()["domain"]["keys"])
            from itertools import product
            allrows=[(row,key) for n in range(5) for row in product(vals,repeat=n) for key in ks]
            probe_set=set()
        case_totals.append(len(allrows))
        for row,key in allrows:
            queue.append((i,row,key,(row,key) in probe_set))
    payload="\n".join(" ".join(str(z) for z in (i,n,len(row),key,*row))
                      for n,(i,row,key,probe) in enumerate(queue))+"\n"
    try:
        completed=command([str(exe)],input=payload,timeout=120)
    except subprocess.CalledProcessError as e:
        (output/"rust_runtime.log").write_text((e.stdout or "")+"\n"+(e.stderr or ""))
        report={"status":"UNKNOWN_NOT_EXECUTABLE","runtime_failure":(e.stderr or "")[-2000:]}
        (output/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
        print(json.dumps(report,sort_keys=True));return report
    lines=completed.stdout.splitlines()
    if len(lines)!=len(queue):raise ValueError("RUST_OUTPUT_COUNT_INCOMPLETE")
    outcomes=[]
    for i,entry in enumerate(entries):
        outcomes.append({"source":entry["c"],"status":entry["status"],"family":entry.get("family"),
                         "full_count":case_totals[i],"tested_count":0,"probe_count":0,
                         "source_violations":0,"target_violations":0,"probe_violations":0,
                         "differential_disagreements":0,"first_counterexample":None})
    for j,((idx,row,key,probe),line) in enumerate(zip(queue,lines)):
        parts=line.split()
        if len(parts)!=3 or int(parts[0])!=j:raise ValueError("UNTRUSTED_RUST_RECORD_FORMAT")
        got=int(parts[1]);unchanged=(parts[2]=="1")
        sig,func=c_functions[idx]
        array=(ctypes.c_int*max(len(row),1))(*row)
        before=list(array)[:len(row)]
        args=[array if p["pointer"] else
              len(row) if p["name"] in ("n","len","length") else key
              for p in sig["parameters"]]
        c_value=int(func(*args))
        c_unchanged=list(array)[:len(row)]==before
        entry=entries[idx]; result=outcomes[idx]
        supported=entry["status"]=="DISCOVERED_BOUNDED_CONTRACT"
        c_bad=(not authorized(entry,row,key,c_value) or not c_unchanged) if supported else False
        t_bad=(not authorized(entry,row,key,got) or not unchanged) if supported else False
        if c_bad:result["source_violations"]+=1
        if t_bad:result["target_violations"]+=1
        if probe:
            result["probe_count"]+=1
            if t_bad:result["probe_violations"]+=1
        if c_value!=got:result["differential_disagreements"]+=1
        result["tested_count"]+=1
        item={"case":idx,"row":list(row),"key":key,"source":c_value,"target":got,
              "source_unchanged":c_unchanged,"target_unchanged":unchanged,
              "probe":probe,"source_contract_supported":supported}
        if (c_bad or t_bad) and result["first_counterexample"] is None:
            result["first_counterexample"]=item
        observations.append(item)
    with (output/"observations.jsonl").open("w") as f:
        for item in observations:f.write(json.dumps(item,sort_keys=True)+"\n")
    for result in outcomes:
        if result["status"]!="DISCOVERED_BOUNDED_CONTRACT":
            result["verdict"]="UNKNOWN_UNSUPPORTED_CONTRACT"
        elif result["source_violations"]:
            result["verdict"]="REJECTED_SOURCE_BASELINE"
        elif result["target_violations"]:
            result["verdict"]="FINITE_COUNTEREXAMPLE"
        else:result["verdict"]="WARRANTED_BOUNDED_MATCH"
    report={"protocol":"AUTONOMOUS_SOURCE_OBSERVATION_V1",
            "status":"FINISHED_BOUNDED_HOLDOUT",
            "source_only_packet_sha256":EXPECTED_PACKET_SHA,
            "upstream_revision":REVISION,"source_and_target":target_info,
            "rustc":command(["rustc","--version"]).stdout.strip(),
            "cc":command(["cc","--version"]).stdout.splitlines()[0],
            "rust_wrapper_sha256":digest(wrapper),
            "rust_binary_sha256":digest(exe),
            "observations_sha256":digest(output/"observations.jsonl"),
            "total_executions":len(queue),
            "source_discovered_probe_count":sum(x["probe_count"] for x in outcomes),
            "cases":outcomes,
            "limitations":["Syntactic ACSL classifier, not a complete ACSL parser.",
                           "Hand-selected nonrandom source holdouts, targets not read until after source-only gate.",
                           "Finite native runtime evidence does not prove general C-to-Rust equivalence.",
                           "Unsupported source contracts remain UNKNOWN regardless of differential passes.",
                           "Conventional comparator is equally informed; no benefit claimed without comparison."]}
    (output/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"total_executions":report["total_executions"],
       "probes":report["source_discovered_probe_count"],
       "per_case":[{"name":x["source"],"verdict":x["verdict"],"tested":x["tested_count"],
                    "violations":x["target_violations"],"probe_violations":x["probe_violations"]}
                   for x in outcomes]},sort_keys=True))
    return report
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: native.py UPSTREAM OUTPUT")
    output=execute(Path(sys.argv[1]),Path(sys.argv[2]))
    if output["status"]!="FINISHED_BOUNDED_HOLDOUT":raise SystemExit(2)
    if any(x["verdict"] in ("FINITE_COUNTEREXAMPLE","REJECTED_SOURCE_BASELINE")
           for x in output["cases"]):raise SystemExit(1)
