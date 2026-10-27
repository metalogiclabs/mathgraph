#!/usr/bin/env python3
"""Authentic C-permitted pointer alias vs safe Rust &mut admissibility.

The claim is strictly API-call admission, NOT a wrong Rust runtime value.
Original C/Rust bytes remain unmodified. Rust negative compilation MUST fail
with E0499, while positive compilation/execution and C same-pointer call pass.
"""
import ctypes,hashlib,json,re,subprocess,sys
from pathlib import Path
REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
C="data/frama_c_problems/swap.c"
R="transpiled_rust/frama_c_problems/swap.rs"
C_BLOB="318943f87c2faffa9a4aa3e6cd0bd5be9dcc2286"
R_BLOB="4590f8472cb8fa99e37a4925fa05955b1c418b36"
def cmd(argv,**opts):return subprocess.run(argv,capture_output=True,text=True,check=False,**opts)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def build_wrapper(path,alias):
    body=('let mut a:i32=7;swap(&mut a,&mut a);' if alias else
          'let mut a:i32=3;let mut b:i32=7;swap(&mut a,&mut b);assert!(a==7 && b==3);')
    return ('mod migration {include!(r#"'+str(path.resolve())+'"#);'+
            'pub fn check(){'+body+'}}\nfn main(){migration::check();}\n')
def witness(root,out):
    root,out=Path(root).resolve(),Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    rev=cmd(["git","-C",str(root),"rev-parse","HEAD"])
    if rev.returncode or rev.stdout.strip()!=REV:raise ValueError("SOURCE_REVISION_DRIFT")
    for path,digest in ((C,C_BLOB),(R,R_BLOB)):
        r=cmd(["git","-C",str(root),"hash-object",path])
        if r.returncode or r.stdout.strip()!=digest:raise ValueError("INPUT_BLOB_DRIFT:"+path)
    cs=(root/C).read_text()
    rust=(root/R).read_text()
    clause=re.search(r"/\*@([\s\S]*?)\*/",cs)
    if not clause:raise ValueError("C_SOURCE_PRECONDITION_MISSING")
    pre=re.sub(r"\s+","",clause.group(1))
    if r"requires\valid(a)&&\valid(b);" not in pre or r"\separated" in pre:
        raise ValueError("C_ALIAS_PRECONDITION_NOT_GROUNDED")
    if r"ensures*a==\old(*b)&&*b==\old(*a);" not in pre:
        raise ValueError("SWAP_POSTCONDITION_MISSING")
    if not re.search(r"fn\s+swap\s*\(\s*a\s*:\s*&mut\s+i32\s*,\s*b\s*:\s*&mut\s+i32\s*\)",rust):
        raise ValueError("RUST_SAFE_MUTABLE_REFERENCE_SIGNATURE_CHANGED")
    if cmd(["git","-C",str(root),"status","--porcelain"]).stdout.strip():
        raise ValueError("UPSTREAM_CHANGED")
    so=out/"source_swap.so"
    compiled=cmd(["cc","-std=c11","-O2","-shared","-fPIC",str(root/C),"-o",str(so)])
    if compiled.returncode:raise ValueError("SOURCE_C_COMPILE_FAILED:"+compiled.stderr[-1000:])
    fn=ctypes.CDLL(str(so)).swap
    fn.argtypes=(ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int))
    fn.restype=None
    same=ctypes.c_int(7)
    fn(ctypes.byref(same),ctypes.byref(same))
    if same.value!=7:raise ValueError("SOURCE_ALIAS_RUNTIME_NOT_CLOSED")
    x,y=ctypes.c_int(3),ctypes.c_int(7)
    fn(ctypes.byref(x),ctypes.byref(y))
    if (x.value,y.value)!=(7,3):raise ValueError("SOURCE_DISTINCT_RUNTIME_NOT_CLOSED")
    scripts={}
    compilers={}
    for label,should_compile in (("distinct",True),("same_pointer",False)):
        target=out/(label+".rs");target.write_text(build_wrapper(root/R,not should_compile))
        binary=out/(label+".bin")
        proc=cmd(["rustc","--edition=2021",str(target),"-o",str(binary)])
        log=out/(label+".compiler.log");log.write_text(proc.stdout+"\n"+proc.stderr)
        scripts[label]={"source_sha256":sha(target),"compiler_log_sha256":sha(log),"exit":proc.returncode}
        if should_compile:
            if proc.returncode!=0:raise ValueError("DISTINCT_RUST_CONTROL_COMPILATION_FAILED:"+proc.stderr[-900:])
            executable=cmd([str(binary)])
            if executable.returncode!=0:raise ValueError("DISTINCT_RUST_RUNTIME_FAILED:"+executable.stderr[-900:])
            scripts[label]["runtime_exit"]=executable.returncode
        else:
            if proc.returncode==0 or ("E0499" not in proc.stderr and
                                      "cannot borrow" not in proc.stderr):
                raise ValueError("RUST_ALIAS_CALL_NOT_REJECTED_BY_BORROW_CHECKER")
            scripts[label]["expected_native_error"]="E0499"
    report={"status":"SOURCE_ALLOWED_ALIASING_NOT_DIRECTLY_CALLABLE_WITH_SAFE_RUST_MUTABLE_REFERENCES",
            "source_revision":REV,"c_blob":C_BLOB,"rust_blob":R_BLOB,
            "c_source_sha256":sha(root/C),"rust_source_sha256":sha(root/R),
            "c_same_pointer_value":same.value,"c_distinct_values":[x.value,y.value],
            "rust_compilation":scripts,"compiler_version":cmd(["rustc","--version"]).stdout.strip(),
            "claim_scope":"Direct, safe Rust API call using the translated signature; not full adapter impossibility",
            "no_executable_semantic_bug_claim":True,
            "limitation":"C pointer aliasing admitted by original \\\\valid preconditions; rustc excludes direct overlapping &mut arguments. Other safe API designs might preserve functionality."}
    (out/"ALIAS_REPORT.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
    return report
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: alias_witness.py upstream evidence")
    witness(sys.argv[1],sys.argv[2])
