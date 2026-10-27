#!/usr/bin/env python3
"""Independent native nullable C/Rust API positive control, source unmodified."""
import ctypes,hashlib,json,subprocess,sys
from pathlib import Path
REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
C="data/tutorial_wp/ex-4-max-ptr-answer-4.c"
R="transpiled_rust/tutorial_wp/ex-4-max-ptr-answer-4.rs"
C_BLOB="275ebc2ee79f231bc35936fac96463444c2a3365"
R_BLOB="b4cf82e670797861c4736e43884d895aad4bf656"
def command(args,**kw):return subprocess.run(args,capture_output=True,text=True,check=False,**kw)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(root,out):
 root,out=Path(root).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 rev=command(["git","-C",str(root),"rev-parse","HEAD"])
 if rev.stdout.strip()!=REV:raise ValueError("UNPINNED_REVISION")
 for p,sha in ((C,C_BLOB),(R,R_BLOB)):
  if command(["git","-C",str(root),"hash-object",p]).stdout.strip()!=sha:
   raise ValueError("SOURCE_INPUT_DRIFT:"+p)
 generated=out/"nullable_c_glue.c"
 generated.write_text('#include "'+str(root/C)+'"\nint h = 0;\n')
 so=out/"nullable_c.so"
 cc=command(["cc","-O2","-std=c11","-fPIC","-shared",str(generated),"-o",str(so)])
 if cc.returncode:raise ValueError("NATIVE_C_COMPILATION_FAILED:"+cc.stderr[-700:])
 f=ctypes.CDLL(str(so)).max_ptr
 f.argtypes=[ctypes.POINTER(ctypes.c_int)]*2
 f.restype=ctypes.c_int
 native=[]
 for p,q in ((False,False),(True,False),(False,True),(True,True)):
  x=ctypes.c_int(3)
  native.append(int(f(ctypes.byref(x) if p else None,ctypes.byref(x) if q else None)))
 if native!=[-2147483648,3,3,3]:
  raise ValueError("C_NULLABLE_PRECONDITION_NOT_CLOSED:"+str(native))
 rust=out/"nullable_rust_glue.rs"
 rust.write_text(
  'mod original {include!(r#"'+str(root/R)+'"#);'
  'pub fn check(mode:usize)->i32{let x=3i32;match mode{'
  '0=>max_ptr(None,None),1=>max_ptr(Some(&x),None),'
  '2=>max_ptr(None,Some(&x)),3=>max_ptr(Some(&x),Some(&x)),'
  '_=>panic!("mode")}}}\n'
  'fn main(){for i in 0..4{println!("{}",original::check(i));}}\n')
 exe=out/"nullable_rust_glue"
 compiled=command(["rustc","--edition=2021","-O",str(rust),"-o",str(exe)])
 (out/"nullable_rust_compiler.log").write_text(compiled.stdout+"\n"+compiled.stderr)
 if compiled.returncode:raise ValueError("UNMODIFIED_RUST_API_NULL_CALL_FAILED:"+compiled.stderr[-800:])
 process=command([str(exe)],timeout=60)
 if process.returncode:raise ValueError("NATIVE_RUST_RUNTIME_FAILED:"+process.stderr[-700:])
 outputs=[int(x) for x in process.stdout.splitlines()]
 if outputs!=native:raise ValueError("SOURCE_TO_RUST_NULLABLE_RETURN_MISMATCH")
 if command(["git","-C",str(root),"status","--porcelain"]).stdout.strip():
  raise ValueError("UPSTREAM_CHANGED")
 result={"status":"BOUNDED_NULL_ALIAS_POSITIVE_MATCH","native_c_results":native,
         "unchanged_rust_results":outputs,"cases":4,"C_source_blob":C_BLOB,"Rust_target_blob":R_BLOB,
         "C_glue_sha256":digest(generated),"Rust_glue_sha256":digest(rust),
         "compiler_log_sha256":digest(out/"nullable_rust_compiler.log"),
         "scope":"Four finite null-or-shared pointer topologies, not universal nullable refinement"}
 (out/"NULLABLE_RUNTIME_REPORT.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print(json.dumps(result,sort_keys=True))
 return result
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: nullable_native.py UPSTREAM EVIDENCE")
 run(sys.argv[1],sys.argv[2])
