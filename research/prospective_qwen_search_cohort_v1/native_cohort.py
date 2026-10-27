"""Replay unchanged source C and Qwen Rust on frozen 7,231-case cohort."""
import ctypes,json,subprocess,hashlib,sys
from pathlib import Path
from oracle import cases,allowed,COUNTS,require_counts
PIN="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
FILES={
 "recursive_search":("data/tutorial_wp/ex-3-search-answer.c","72d7eafa47c1e4914101ee1a088ffd15688e6369","transpiled_rust/tutorial_wp/ex-3-search-answer.rs","ba64d22cf4f6b6861e0c8af5bb203c47b4fd5fdf"),
 "binary_search":("data/tutorial_wp/ex-3-binary-search-answer.c","b4f00cac89395f618671bcd73f5b2828e4df3858","transpiled_rust/tutorial_wp/ex-3-binary-search-answer.rs","ca7bb488b2de916812715c790ed3b7cdf8c84e3d")}
def exec_(args,**kw):return subprocess.run(args,check=True,capture_output=True,text=True,**kw)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(root,out):
    root,out=Path(root).resolve(),Path(out).resolve()
    if exec_(["git","-C",str(root),"rev-parse","HEAD"]).stdout.strip()!=PIN:raise ValueError("UPSTREAM_REVISION")
    for name,(cp,ch,rp,rh) in FILES.items():
        for p,expected in ((cp,ch),(rp,rh)):
            if exec_(["git","-C",str(root),"hash-object",p]).stdout.strip()!=expected:
                raise ValueError("BYTE_DRIFT:"+p)
    if exec_(["git","-C",str(root),"status","--porcelain"]).stdout.strip():raise ValueError("UPSTREAM_DIRTY")
    require_counts();out.mkdir(parents=True,exist_ok=True)
    library=out/"source.so"
    exec_(["cc","-O2","-fPIC","-shared","-std=c11",str(root/FILES["recursive_search"][0]),
           str(root/FILES["binary_search"][0]),"-o",str(library)])
    lib=ctypes.CDLL(str(library))
    f0=lib.search;f0.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_uint,ctypes.c_int];f0.restype=ctypes.c_uint
    f1=lib.bsearch;f1.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int];f1.restype=ctypes.c_int
    wrapper=out/"rust_harness.rs"
    wrapper.write_text('include!(r#"'+str(root/FILES["recursive_search"][2])+'"#);\n'
        +'include!(r#"'+str(root/FILES["binary_search"][2])+'"#);\n'
        +'use std::io::{self,Read};\n'
        +'fn main() { let mut s=String::new(); io::stdin().read_to_string(&mut s).unwrap();\n'
        +'for line in s.lines() { let mut it=line.split_whitespace();\n'
        +'let which:i32=it.next().unwrap().parse().unwrap();\n'
        +'let n:usize=it.next().unwrap().parse().unwrap();\n'
        +'let key:i32=it.next().unwrap().parse().unwrap();\n'
        +'let a:Vec<i32>=(0..n).map(|_|it.next().unwrap().parse().unwrap()).collect();\n'
        +'let before=a.clone(); let v:i64=if which==0 {search(&a,n as u32,key) as i64}\n'
        +'else {bsearch(&a,n as i32,key) as i64};\n'
        +'println!("{} {}",v,if a==before {1} else {0});\n'
        +'} }\n')
    exe=out/"rust_harness"
    exec_(["rustc","--edition=2021","-O",str(wrapper),"-o",str(exe)])
    vectors=[(name,row,key) for name in ("recursive_search","binary_search") for row,key in cases(name)]
    if len(vectors)!=7231:raise ValueError("CENSUS")
    input_="\n".join(" ".join(map(str,(0 if name=="recursive_search" else 1,len(row),key,*row))) for name,row,key in vectors)+"\n"
    lines=exec_([str(exe)],input=input_,timeout=90).stdout.splitlines()
    if len(lines)!=len(vectors):raise ValueError("RUST_OUTPUT_COUNT")
    violations={name:{"c":[],"rust":[]} for name in FILES}
    with (out/"observations.jsonl").open("w") as f:
        for index,((name,row,key),line) in enumerate(zip(vectors,lines)):
            arr=(ctypes.c_int*max(1,len(row)))(*row);before=list(arr)[:len(row)]
            c=int((f0 if name=="recursive_search" else f1)(arr,len(row),key))
            parts=line.split()
            if len(parts)!=2:raise ValueError("MALFORMED_RUST")
            rust=int(parts[0]);keep=(parts[1]=="1")
            unchanged=(list(arr)[:len(row)]==before)
            item={"index":index,"kind":name,"array":list(row),"key":key,"c":c,"rust":rust,
                  "c_unchanged":unchanged,"rust_unchanged":keep}
            f.write(json.dumps(item,sort_keys=True)+"\n")
            if not allowed(name,row,key,c) or not unchanged:violations[name]["c"].append(item)
            if not allowed(name,row,key,rust) or not keep:violations[name]["rust"].append(item)
    score={}
    for name in FILES:
        bad=violations[name]
        score[name]={"cases":COUNTS[name],"c_violations":len(bad["c"]),
                     "rust_violations":len(bad["rust"]),
                     "first_c":bad["c"][:1],"first_rust":bad["rust"][:1],
                     "verdict":"REJECTED_SOURCE_BASELINE" if bad["c"] else
                       "FINITE_COUNTEREXAMPLE" if bad["rust"] else "WARRANTED_BOUNDED_MATCH"}
    report={"upstream":PIN,"cases":7231,"source_blobs":FILES,"score":score,
            "compiler":exec_(["rustc","--version"]).stdout.strip(),"wrapper_sha256":sha(wrapper),
            "rust_binary_sha256":sha(exe)}
    (out/"native_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"cases":7231,"score":score},sort_keys=True))
    if any(x["verdict"]!="WARRANTED_BOUNDED_MATCH" for x in score.values()):raise SystemExit(1)
if __name__=="__main__":audit(sys.argv[1],sys.argv[2])
