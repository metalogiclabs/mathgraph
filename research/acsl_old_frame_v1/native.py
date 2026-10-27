#!/usr/bin/env python3
"""Run unchanged authentic C and generated Rust against sealed source-only packet."""
import ctypes,hashlib,json,subprocess,sys
from pathlib import Path
from normalizer import extract,cases,probes,authorizes,manifest

REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
FROZEN_PACKET="cb7e59d238a0bfaf9b033048deec4914ae2b9417e451ee215cc9ee2ea8dc0d79"
TARGET_BLOBS={
 "reset":"b22649522e7f9ebac53a08f01ac2328ec9165ac9",
 "increment":"822e4580ecd398c163e6f85ba79feaa4e3474f83",
 "swap":"4590f8472cb8fa99e37a4925fa05955b1c418b36",
 "array_swap":"d688af3f3d3900cc3582c37a0b0f4b60f77e926e",
 "sum":"1f65adb2da4cbf2d3c45216737f548ebf56eea07",
 "plus_five":"210074be2f34602e4cac03c714375944b12bdff1",
 "relational_unknown":"8b137891791fe96927ad78e64b0aad7bded08bdc"}
FN=("reset_1st_if_2nd_is_true","incr_a_by_b","swap","array_swap","add","plus_5")
def run(args,**kw):return subprocess.run(args,check=True,capture_output=True,text=True,**kw)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(root,rel):return run(["git","-C",str(root),"hash-object",rel]).stdout.strip()
def generate_adapter(paths):
    calls=[
      'let mut a=row[0]; let b=row[1]; reset_1st_if_2nd_is_true(&mut a,&b); (None,vec![a,b])',
      'let mut a=row[0]; let b=row[1]; let r=incr_a_by_b(&mut a,&b); (Some(r as i64),vec![a,b])',
      'let mut a=row[0]; let mut b=row[1]; swap(&mut a,&mut b); (None,vec![a,b])',
      'let mut v=row.to_vec(); let n=v.len() as i32; array_swap(&mut v,n,i,j); (None,v)',
      'let a=row[0]; let b=row[1]; let r=add(&a,&b); (Some(r as i64),vec![a,b])',
      'let a=row[0]; let r=plus_5(&a); (Some(r as i64),vec![a])']
    mods=[]
    for k,path in enumerate(paths):
        mods.append('mod c'+str(k)+' {\ninclude!(r#"'+str(path.resolve())+'"#);\n'
                    'pub fn evaluate(row:&[i32],i:i32,j:i32)->(Option<i64>,Vec<i32>){\n'+calls[k]+'\n}\n}\n')
    body="\n".join('  '+str(i)+' => c'+str(i)+'::evaluate(&row,p,q),' for i in range(6))
    return "".join(mods)+(
      'use std::io::{self,Read};\n'
      'fn main(){let mut s=String::new();io::stdin().read_to_string(&mut s).unwrap();\n'
      'for line in s.lines(){let mut it=line.split_whitespace();\n'
      'let case:usize=it.next().unwrap().parse().unwrap();\n'
      'let id:usize=it.next().unwrap().parse().unwrap();\n'
      'let p:i32=it.next().unwrap().parse().unwrap();\n'
      'let q:i32=it.next().unwrap().parse().unwrap();\n'
      'let n:usize=it.next().unwrap().parse().unwrap();\n'
      'let row:Vec<i32>=(0..n).map(|_|it.next().unwrap().parse().unwrap()).collect();\n'
      'let (result,post)=match case {\n'+body+'\n _=>panic!("bad case")};\n'
      'let ret=match result{Some(v)=>v.to_string(),None=>String::from("N")};\n'
      'println!("{} {} {}",id,ret,post.iter().map(|x|x.to_string()).collect::<Vec<_>>().join(","));\n'
      '}}\n')
def c_call(lib,index,pre):
    pointer=ctypes.POINTER(ctypes.c_int)
    if index==3:
        row,i,j=pre
        arr=(ctypes.c_int*len(row))(*row)
        fn=lib.array_swap;fn.argtypes=[pointer,ctypes.c_int,ctypes.c_int,ctypes.c_int];fn.restype=None
        fn(arr,len(row),i,j)
        return None,list(arr)
    vals=[ctypes.c_int(x) for x in pre]
    argtypes=[pointer for _ in vals]
    fn=getattr(lib,FN[index]);fn.argtypes=argtypes
    fn.restype=None if index in (0,2) else ctypes.c_int
    result=fn(*[ctypes.byref(x) for x in vals])
    return (None if result is None else int(result)),[x.value for x in vals]
def native(upstream,out):
    upstream,out=Path(upstream).resolve(),Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    m=manifest()
    if run(["git","-C",str(upstream),"rev-parse","HEAD"]).stdout.strip()!=REV:
        raise ValueError("PINNED_UPSTREAM_REVISION_DRIFT")
    packet=extract(upstream)
    serialized=(json.dumps(packet,sort_keys=True,indent=2)+"\n").encode()
    if hashlib.sha256(serialized).hexdigest()!=FROZEN_PACKET:
        raise ValueError("SOURCE_ONLY_PACKET_MISMATCH")
    (out/"SOURCE_ONLY_PACKET.json").write_bytes(serialized)
    original=[];targets=[];identities=[]
    for row in m["cases"]:
        if blob(upstream,row["c"])!=row["blob"]:
            raise ValueError("C_SOURCE_DRIFT:"+row["id"])
        if blob(upstream,row["target"])!=TARGET_BLOBS[row["id"]]:
            raise ValueError("RUST_SOURCE_DRIFT:"+row["id"])
        identities.append({"id":row["id"],"source":row["c"],"target":row["target"],
                           "c_blob":row["blob"],"rust_blob":TARGET_BLOBS[row["id"]],
                           "c_sha256":digest(upstream/row["c"]),
                           "rust_sha256":digest(upstream/row["target"])})
        if row["id"]=="relational_unknown":continue
        so=out/(row["id"]+".so")
        run(["cc","-std=c11","-O2","-fPIC","-shared",str(upstream/row["c"]),"-o",str(so)])
        original.append(ctypes.CDLL(str(so)))
        targets.append(upstream/row["target"])
    if run(["git","-C",str(upstream),"status","--porcelain"]).stdout.strip():
        raise ValueError("UPSTREAM_DIRTY")
    wrapper=out/"rust_adapter.rs";wrapper.write_text(generate_adapter(targets))
    exe=out/"rust_adapter"
    try:
        run(["rustc","--edition=2021","-O",str(wrapper),"-o",str(exe)])
    except subprocess.CalledProcessError as e:
        (out/"RUST_COMPILATION_ERROR.log").write_text(e.stderr or "")
        r={"status":"UNKNOWN_NOT_EXECUTABLE","reason":"RUST_COMPILATION_FAILED",
           "stderr_digest":digest(out/"RUST_COMPILATION_ERROR.log")}
        (out/"NATIVE_REPORT.json").write_text(json.dumps(r,indent=2)+"\n")
        print(json.dumps(r));return r
    inputs=[];probesets={}
    reports=[]
    for idx,entry in enumerate(packet["cases"]):
        status=entry["status"]
        if status=="UNKNOWN_UNSUPPORTED":
            reports.append({"id":entry["id"],"verdict":"UNKNOWN_UNSUPPORTED",
                            "reason":entry["reason"],"native_count":0})
            continue
        full=list(cases(entry["family"]))
        pset={str(z) for z in probes(entry["family"])}
        probesets[idx]=pset
        for pre in full:inputs.append((idx,pre,str(pre) in pset))
        reports.append({"id":entry["id"],"family":entry["family"],"source_violations":0,
                        "target_violations":0,"differential_disagreements":0,
                        "probe_count":0,"probe_target_violations":0,"native_count":0,
                        "first_source_failure":None,"first_target_failure":None,
                        "aliasing_scope":"UNTESTED_OVERLAPPING_POINTERS" if idx==2 else "NO_POINTER_ALIASING_IN_TESTS",
                        "weaker_spec_than_C_algorithm":idx==3})
    if len(inputs)!=356:raise ValueError("FROZEN_TEST_CENSUS_DRIFT")
    encoded=[]
    for idx,(which,pre,isprobe) in enumerate(inputs):
        if which==3:row,i,j=pre
        else:row,i,j=pre,0,0
        encoded.append(" ".join(str(x) for x in (which,idx,i,j,len(row),*row)))
    try:
        process=run([str(exe)],input="\n".join(encoded)+"\n",timeout=120)
    except subprocess.CalledProcessError as e:
        (out/"RUST_RUNTIME_ERROR.log").write_text((e.stdout or "")+"\n"+(e.stderr or ""))
        r={"status":"UNKNOWN_NOT_EXECUTABLE","reason":"RUST_RUNTIME_FAILED",
           "stderr_digest":digest(out/"RUST_RUNTIME_ERROR.log")}
        (out/"NATIVE_REPORT.json").write_text(json.dumps(r,indent=2)+"\n")
        print(json.dumps(r));return r
    output=process.stdout.splitlines()
    if len(output)!=len(inputs):raise ValueError("RUST_OUTPUT_COUNT_DRIFT")
    records=[]
    for ix,((which,pre,isprobe),line) in enumerate(zip(inputs,output)):
        parts=line.split(maxsplit=2)
        if len(parts)!=3 or int(parts[0])!=ix:
            raise ValueError("UNTRUSTWORTHY_NATIVE_OUTPUT:"+str(ix))
        rust_ret=None if parts[1]=="N" else int(parts[1])
        rust_post=[int(x) for x in parts[2].split(",")]
        c_ret,c_post=c_call(original[which],which,pre)
        fam=packet["cases"][which]["family"]
        src_ok=authorizes(fam,pre,c_post,c_ret)
        rust_ok=authorizes(fam,pre,rust_post,rust_ret)
        obs={"index":ix,"case":which,"pre":pre,"probe":isprobe,
             "c_post":c_post,"rust_post":rust_post,"c_result":c_ret,"rust_result":rust_ret,
             "source_contract_ok":src_ok,"target_contract_ok":rust_ok}
        records.append(obs)
        entry=reports[which]
        entry["native_count"]+=1
        if isprobe:entry["probe_count"]+=1
        if not src_ok:
            entry["source_violations"]+=1
            if entry["first_source_failure"] is None:entry["first_source_failure"]=obs
        if not rust_ok:
            entry["target_violations"]+=1
            if isprobe:entry["probe_target_violations"]+=1
            if entry["first_target_failure"] is None:entry["first_target_failure"]=obs
        if c_post!=rust_post or c_ret!=rust_ret:
            entry["differential_disagreements"]+=1
    with (out/"observations.jsonl").open("w") as f:
        for row in records:f.write(json.dumps(row,sort_keys=True)+"\n")
    for entry in reports:
        if entry["verdict"]=="UNKNOWN_UNSUPPORTED" if "verdict" in entry else False:continue
        entry["verdict"]=("REJECTED_SOURCE_BASELINE" if entry["source_violations"] else
                          "FINITE_COUNTEREXAMPLE" if entry["target_violations"] else
                          "WARRANTED_BOUNDED_MATCH")
    report={"status":"COMPLETED_BOUNDED_NATIVE_EVIDENCE","protocol":m["protocol"],
            "revision":REV,"source_packet_sha256":FROZEN_PACKET,
            "original_and_translated":identities,
            "case_count":len(inputs),"source_generated_probe_count":sum(x.get("probe_count",0) for x in reports),
            "observations_sha256":digest(out/"observations.jsonl"),
            "rust_adapter_sha256":digest(wrapper),"rust_executable_sha256":digest(exe),
            "compiler_versions":{"cc":run(["cc","--version"]).stdout.splitlines()[0],
                                 "rustc":run(["rustc","--version"]).stdout.strip()},
            "cases":reports,
            "limits":["Source-only narrow template parsing, not full ACSL semantics.",
                      "Pointer aliasing of swap not executable via separate safe Rust borrows, hence untested.",
                      "Unconstrained postconditions must not be silently strengthened.",
                      "Finite domain results only; strong conventional comparator equal input evidence."]}
    (out/"NATIVE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"count":report["case_count"],
       "cases":[{"name":x["id"],"verdict":x["verdict"],"c_bad":x.get("source_violations"),"rust_bad":x.get("target_violations"),"differential":x.get("differential_disagreements")} for x in reports]},sort_keys=True))
    return report
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: native.py UPSTREAM EVIDENCE")
    report=native(sys.argv[1],sys.argv[2])
    if report["status"]!="COMPLETED_BOUNDED_NATIVE_EVIDENCE":raise SystemExit(2)
    if any(x["verdict"] in ("FINITE_COUNTEREXAMPLE","REJECTED_SOURCE_BASELINE") for x in report["cases"]):raise SystemExit(1)
