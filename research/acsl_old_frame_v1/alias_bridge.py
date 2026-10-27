#!/usr/bin/env python3
"""Bounded safe adapter for C swap's alias-admissible call set.

Constructed adapter is NOT part of authentic generated Rust. It explicitly
models same-location versus distinct-location input topology; no unsafe code.
"""
import ctypes,hashlib,json,subprocess,sys
from pathlib import Path
C="data/frama_c_problems/swap.c"
RUST="transpiled_rust/frama_c_problems/swap.rs"
REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
C_SHA="318943f87c2faffa9a4aa3e6cd0bd5be9dcc2286"
R_SHA="4590f8472cb8fa99e37a4925fa05955b1c418b36"
VALUES=(-5,-2,0,3,7)
def sh(cmd,**opts):return subprocess.run(cmd,capture_output=True,text=True,check=False,**opts)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def wrapper(rust):
 return ('mod source {include!(r#"'+str(rust.resolve())+'"#);\n'
         'pub enum Topology<'+chr(39)+'a> {Same(&'+chr(39)+'a mut i32),'
         'Distinct(&'+chr(39)+'a mut i32,&'+chr(39)+'a mut i32)}\n'
         'pub fn adapted(input:Topology<'+chr(39)+'_>){match input{'
         'Topology::Same(_)=>{},Topology::Distinct(a,b)=>swap(a,b)}}\n'
         'pub fn case(same:bool,x:i32,y:i32)->(i32,i32){\n'
         'let mut a=x;let mut b=y;\n'
         'if same {adapted(Topology::Same(&mut a));(a,a)} else {'
         'adapted(Topology::Distinct(&mut a,&mut b));(a,b)}\n}}\n'
         'use std::io::{self,Read};\n'
         'fn main(){let mut s=String::new();io::stdin().read_to_string(&mut s).unwrap();\n'
         'for line in s.lines(){let v:Vec<i32>=line.split_whitespace().map(|x|x.parse().unwrap()).collect();\n'
         'let (a,b)=source::case(v[0]==1,v[1],v[2]);println!("{} {}",a,b);}}\n')
def replay(root,out):
 root,out=Path(root).resolve(),Path(out).resolve()
 out.mkdir(parents=True,exist_ok=True)
 revision=sh(["git","-C",str(root),"rev-parse","HEAD"])
 if revision.stdout.strip()!=REV:raise ValueError("REVISION_DRIFT")
 for name,blob in ((C,C_SHA),(RUST,R_SHA)):
  exact=sh(["git","-C",str(root),"hash-object",name])
  if exact.stdout.strip()!=blob:raise ValueError("SOURCE_PIN_DRIFT:"+name)
 if sh(["git","-C",str(root),"status","--porcelain"]).stdout.strip():
  raise ValueError("UPSTREAM_DIRTY")
 so=out/"swap_original.so"
 cc=sh(["cc","-std=c11","-O2","-fPIC","-shared",str(root/C),"-o",str(so)])
 if cc.returncode:raise ValueError("C_COMPILE_FAIL:"+cc.stderr[-900:])
 f=ctypes.CDLL(str(so)).swap
 p=ctypes.POINTER(ctypes.c_int);f.argtypes=(p,p);f.restype=None
 rust=out/"explicit_alias_adapter.rs";rust.write_text(wrapper(root/RUST))
 exe=out/"explicit_alias_adapter"
 built=sh(["rustc","--edition=2021","-O",str(rust),"-o",str(exe)])
 (out/"adapter_compiler.log").write_text(built.stdout+"\n"+built.stderr)
 if built.returncode:raise ValueError("SAFE_ADAPTER_NOT_COMPILABLE:"+built.stderr[-1500:])
 cases=[(1,x,x) for x in VALUES]+[(0,x,y) for x in VALUES for y in VALUES]
 lines="\n".join(" ".join(map(str,row)) for row in cases)+"\n"
 executed=sh([str(exe)],input=lines,timeout=60)
 if executed.returncode:raise ValueError("ADAPTER_RUNTIME_FAILED:"+executed.stderr[-1200:])
 outputs=executed.stdout.splitlines()
 if len(outputs)!=len(cases):raise ValueError("ADAPTER_OUTPUT_COUNT")
 records=[]
 for index,((same,a,b),line) in enumerate(zip(cases,outputs)):
  obs=list(map(int,line.split()))
  if len(obs)!=2:raise ValueError("ADAPTER_OUTPUT_SHAPE")
  left=ctypes.c_int(a);right=ctypes.c_int(b)
  if same:
   f(ctypes.byref(left),ctypes.byref(left))
   source=[left.value,left.value]
  else:
   f(ctypes.byref(left),ctypes.byref(right))
   source=[left.value,right.value]
  expected=[a,a] if same else [b,a]
  records.append({"id":index,"topology":"SAME" if same else "DISTINCT",
                  "before":[a,b],"native_c":source,"constructed_safe_rust":obs,
                  "expected_from_original_contract":expected,
                  "c_matches_contract":source==expected,"bridge_matches_contract":obs==expected})
 with (out/"bridge_observations.jsonl").open("w") as f:
  for row in records:f.write(json.dumps(row,sort_keys=True)+"\n")
 bad=[x for x in records if not x["c_matches_contract"] or not x["bridge_matches_contract"]]
 report={"status":"BOUNDED_SAFE_ALIAS_AWARE_ADAPTER_MATCH" if not bad else "COUNTEREXAMPLE",
         "category":"CONSTRUCTED_ADAPTER_NOT_ORIGINAL_TRANSLATION",
         "revision":REV,"c_blob":C_SHA,"rust_blob":R_SHA,"adapter_sha256":sha(rust),
         "observations_sha256":sha(out/"bridge_observations.jsonl"),
         "cases":len(records),"same_location_cases":len(VALUES),
         "distinct_location_cases":len(VALUES)**2,"failed":len(bad),
         "first_failed":bad[:1],
         "why_adapter_needed":"Source permits overlapping C pointer arguments; original safe Rust two-&mut signature cannot directly accept them.",
         "limits":["Topology must be explicitly identified by caller.",
                   "Only same or distinct scalar locations tested; not a full C pointer model.",
                   "Constructed adapter is not part of the published generated Rust source.",
                   "Conventional source-aware review can design the same adapter."]}
 (out/"BRIDGE_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
 print(json.dumps(report,sort_keys=True))
 if bad:raise SystemExit(1)
 return report
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: alias_bridge.py UPSTREAM EVIDENCE")
 replay(sys.argv[1],sys.argv[2])
