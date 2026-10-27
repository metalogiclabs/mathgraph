#!/usr/bin/env python3
"""Source-pinned C pointer alias calls versus unmodified safe Rust direct calls."""
import ctypes,hashlib,json,re,subprocess,sys
from pathlib import Path
from analyzer import scan
REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
PACKET="1710221dfdfb31911b21ecd472ec5dffc83a93be3b69d723093bc4be5b4985b3"
TARGET={
"add_read":"40776acb8f6b8613ce2523e803b12b831d2efc25",
"add_output":"0af446a465027b7ae458e05833ddb21cee794cc8",
"max_mut_behaviors":"acba66aebd6813bb129e08fc215e44b4e01534a4",
"max_read":"6f9017d89b91631960a77be6d1c40f5378ff3e81",
"max_mut_old":"eb413aa48c528322b5b42e67837d963b72455ec1",
"max_read_cases":"9567028bd64b93f8b9afece9f33c4beff6ee1b75",
"max_nullable":"b4cf82e670797861c4736e43884d895aad4bf656",
"array_equal":"ef83a75a5a7bf87834e0cd525e14c51253a3e512",
"vector_sum":"b5a4a47c145e3a052742e3a2e09cd240f7f1c114"}
def sh(args,**kw):return subprocess.run(args,capture_output=True,text=True,check=False,**kw)
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sig(source,fn):
 m=re.search(r"\bfn\s+"+re.escape(fn)+r"\s*\(([^)]*)\)",source)
 if not m:raise ValueError("TARGET_SIGNATURE_NOT_FOUND")
 parts=[]
 for token in m.group(1).split(","):
  items=token.strip().split(":",1)
  if len(items)!=2:raise ValueError("TARGET_SIGNATURE_GRAMMAR")
  name,typ=map(str.strip,items)
  if typ not in ("&i32","&mut i32","&[i32]","&mut [i32]","Option<&i32>","Option<&mut i32>","i32","u32","usize"):
   raise ValueError("UNSUPPORTED_RUST_TYPE:"+typ)
  parts.append((name,typ))
 return parts
def wrapper(file,fn,params,shared=None,nullable=None):
 shared=set(shared or [])
 declarations=[]
 pointer_index={n:i for i,(n,t) in enumerate(params) if "&" in t}
 for i,(n,t) in enumerate(params):
  if n not in pointer_index:continue
  declarations.append("let mut v"+str(i)+"="+("[3i32,4i32];" if "[" in t else "3i32;"))
 args=[]
 for i,(n,t) in enumerate(params):
  if n not in pointer_index:
   if n not in ("n","len","length"):raise ValueError("SCALAR_PARAMETER_UNKNOWN:"+n)
   args.append("2_"+t);continue
  ref=pointer_index[next(iter(shared))] if n in shared else i
  if nullable is not None and n==nullable:
   if not t.startswith("Option<"):raise ValueError("NULL_NOT_REPRESENTED")
   args.append("None")
  elif t in ("&i32","&[i32]"):args.append("&v"+str(ref))
  elif t in ("&mut i32","&mut [i32]"):args.append("&mut v"+str(ref))
  elif t=="Option<&i32>":args.append("Some(&v"+str(ref)+")")
  else:args.append("Some(&mut v"+str(ref)+")")
 return ('mod target {include!(r#"'+str(file.resolve())+'"#);\n'
         'pub fn witness(){'+''.join(declarations)+'let _ = '+fn+'('+','.join(args)+');}}\n'
         'fn main(){target::witness();}\n')
def compile_probe(root,out,item,params,pair=None,nullable=None):
 label=item["id"]+"_"+("_".join(pair) if pair else "distinct")
 if nullable:label+="_null_"+nullable
 path=out/(label+".rs");path.write_text(wrapper(root/item["target"],item["fn"],params,pair,nullable))
 p=sh(["rustc","--edition=2021","--emit=metadata",str(path),"-o",str(out/(label+".rmeta"))])
 log=out/(label+".log");log.write_text(p.stdout+"\n"+p.stderr)
 errors=list(dict.fromkeys(re.findall(r"error\[(E\d+)\]",p.stderr)))
 state="ACCEPTED" if p.returncode==0 else ("BORROW_REJECTED" if
       any(code in ("E0499","E0502") for code in errors) else "UNKNOWN_COMPILER_FAILURE")
 return {"status":state,"exit":p.returncode,"errors":errors,"source_sha256":h(path),"log_sha256":h(log)}
def c_witness(root,out,item,pair):
 raw=(root/item["c"]).read_text()
 fn=item["fn"];m=re.search(r"\b(int|void)\s+"+re.escape(fn)+r"\s*\(([^)]*)\)\s*\{",raw)
 if not m:return {"status":"UNKNOWN_C_SIGNATURE"}
 names=[];types=[]
 for token in m.group(2).split(","):
  token=token.strip()
  mo=re.search(r"([A-Za-z_]\w*)\s*$",token)
  if not mo:return {"status":"UNKNOWN_C_ARG"}
  names.append(mo.group(1));types.append(token)
 extra="int h = 0;\n" if "extern int h" in raw else ""
 glue=out/(item["id"]+"_"+"_".join(pair)+".c")
 glue.write_text('#include "'+str((root/item["c"]).resolve())+'"\n'+extra)
 binary=out/(item["id"]+"_"+"_".join(pair)+".so")
 built=sh(["cc","-std=c11","-O2","-fPIC","-shared",str(glue),"-o",str(binary)])
 if built.returncode:return {"status":"UNKNOWN_C_COMPILE","detail":built.stderr[-700:]}
 try:
  lib=ctypes.CDLL(str(binary));f=getattr(lib,fn)
 except Exception as e:return {"status":"UNKNOWN_C_LOAD","detail":str(e)}
 f.argtypes=[ctypes.POINTER(ctypes.c_int) if "*" in t else
             ctypes.c_size_t if "size_t" in t else ctypes.c_int for t in types]
 f.restype=ctypes.c_int if m.group(1)=="int" else None
 vals={}
 for name,typ in zip(names,types):
  if "*" not in typ:continue
  lookup=pair[0] if name in pair else name
  if lookup not in vals:vals[lookup]=(ctypes.c_int*2)(3,4) if item["id"] in ("array_equal","vector_sum") else ctypes.c_int(3)
 args=[]
 for n,t in zip(names,types):
  if "*" in t:args.append(vals[pair[0] if n in pair else n])
  elif n in ("n","len","length"):args.append(2)
  else:return {"status":"UNKNOWN_C_SCALAR"}
 try:result=f(*args)
 except Exception as e:return {"status":"UNKNOWN_C_RUNTIME","detail":str(e)}
 return {"status":"C_SAME_POINTER_EXECUTED","result":result,
         "post":{n:list(v) if isinstance(v,ctypes.Array) else v.value for n,v in vals.items()}}
def audit(root,out):
 root,out=Path(root).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 rev=sh(["git","-C",str(root),"rev-parse","HEAD"])
 if rev.returncode or rev.stdout.strip()!=REV:raise ValueError("UPSTREAM_PIN_CHANGED")
 packet=scan(root);data=(json.dumps(packet,indent=2,sort_keys=True)+"\n").encode()
 if hashlib.sha256(data).hexdigest()!=PACKET:raise ValueError("SOURCE_ONLY_PACKET_SHA_DRIFT")
 (out/"FROZEN_PACKET.json").write_bytes(data)
 total={"source_alias_allowed":0,"source_alias_forbidden":0,
        "native_C_allowed_confirmed":0,"direct_rust_borrow_refusals":0,
        "direct_rust_alias_accepted":0,"rust_nullable_accepted":0,
        "unknown":0}
 findings=[]
 for item in packet["tasks"]:
  t=sh(["git","-C",str(root),"hash-object",item["target"]])
  if t.returncode or t.stdout.strip()!=TARGET[item["id"]]:raise ValueError("TARGET_BLOB_DRIFT:"+item["id"])
  args=sig((root/item["target"]).read_text(),item["fn"])
  if [x[0] for x in args]!=[x["name"] for x in item["arguments"]]:
   total["unknown"]+=1;findings.append({"id":item["id"],"status":"UNKNOWN_SIGNATURE_MISMATCH","args":args});continue
  distinct=compile_probe(root,out,item,args)
  if distinct["status"]!="ACCEPTED":
   total["unknown"]+=1;findings.append({"id":item["id"],"status":"UNKNOWN_POSITIVE_CONTROL","distinct":distinct});continue
  ps=[]
  for rule in item["obligations"]:
   pair=rule["pair"]
   if rule["source_alias_admission"]=="FORBIDDEN_EXPLICIT_SEPARATION":
    total["source_alias_forbidden"]+=1
    ps.append({"pair":pair,"status":"SOURCE_FORBIDS_ALIAS","no_mismatch_claim":True});continue
   total["source_alias_allowed"]+=1
   rust=compile_probe(root,out,item,args,pair=pair)
   c=c_witness(root,out,item,pair)
   if c["status"]=="C_SAME_POINTER_EXECUTED":
    total["native_C_allowed_confirmed"]+=1
    if rust["status"]=="BORROW_REJECTED":
     status="DIRECT_RUST_API_ADMISSIBILITY_MISMATCH";total["direct_rust_borrow_refusals"]+=1
    elif rust["status"]=="ACCEPTED":
     status="DIRECT_RUST_CALL_ADMITTED";total["direct_rust_alias_accepted"]+=1
    else:status="UNKNOWN_COMPILER";total["unknown"]+=1
   else:status="UNKNOWN_C_TEST";total["unknown"]+=1
   ps.append({"pair":pair,"status":status,"c":c,"rust":rust})
  nullable=[]
  for name in sorted({v for z in item["obligations"] for v in z["source_nullable"]}):
   try:probe=compile_probe(root,out,item,args,nullable=name)
   except ValueError:probe={"status":"NULL_NOT_REPRESENTED"}
   if probe["status"]=="ACCEPTED":total["rust_nullable_accepted"]+=1
   nullable.append({"pointer":name,"rust":probe})
  findings.append({"id":item["id"],"source":item["c"],"rust":item["target"],
                   "source_blob":item["blob"],"target_blob":TARGET[item["id"]],
                   "rust_signature":args,"distinct":distinct,"pairs":ps,"nullable":nullable})
 if sh(["git","-C",str(root),"status","--porcelain"]).stdout.strip():raise ValueError("UPSTREAM_CHANGED")
 report={"status":"BOUNDED_NATIVE_API_ADMISSION_AUDIT","source_only_packet_sha256":PACKET,
         "source_revision":REV,"counts":total,"findings":findings,
         "scope":"Direct safe Rust signature admission, NOT a runtime output error or universal refinement proof",
         "baseline_comparative_advantage":"UNTESTED"}
 (out/"NATIVE_REPORT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"status":report["status"],"counts":total,
       "per_case":[{"id":x["id"],"admission":[y["status"] for y in x.get("pairs",[])]} for x in findings]},sort_keys=True))
 return report
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: native.py UPSTREAM EVIDENCE")
 audit(sys.argv[1],sys.argv[2])
