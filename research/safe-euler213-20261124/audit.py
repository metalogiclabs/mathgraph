"""Pinned native SAFE Euler-order countermodel with causal repair/withdrawal arms."""
import ast
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import scipy
from scipy.spatial.transform import Rotation
import sympy

PIN = "f9ed45abc53b28afb7e287e605173275f7fe92c9"
TREE = "2d440ab76686815e075f27f7c0811a7c5ea05869"
LIB_SHA = "b5deeac8ab3c61e95745d0feabd7028e708121bf62be4ac4a70bf193cae5fe07"
BLOBS = {
    "safe-time/src/lib.rs": "3e50177fdd23b374ed4c3f8264bee1c956a71a3c",
    "safe-time/Cargo.toml": "24eec505cfcf9aeb0cb8bef839c15ad824e5eb02",
    "Cargo.lock": "d22530b7ad4da0f9ef48f1fb65119883745d396f",
}
EPS = 1e-12

def mul(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def transpose(a):
    return [list(r) for r in zip(*a)]
def error(a,b):
    return max(abs(a[i][j]-b[i][j]) for i in range(3) for j in range(3))
def hamilton(a,b):
    w,x,y,z=a; v,i,j,k=b
    return [w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v]
def qmatrix(q):
    x,y,z,w=q; columns=[]
    for axis in range(3):
        basis=[0.0]*4;basis[axis+1]=1.0
        columns.append(hamilton(hamilton([w,x,y,z],basis),[w,-x,-y,-z])[1:])
    return transpose(columns)
def references(p,r,y):
    sp,cp=math.sin(p),math.cos(p);sr,cr=math.sin(r),math.cos(r);sy,cy=math.sin(y),math.cos(y)
    rx=[[1.,0.,0.],[0.,cr,-sr],[0.,sr,cr]]
    ry=[[cp,0.,sp],[0.,1.,0.],[-sp,0.,cp]]
    rz=[[cy,-sy,0.],[sy,cy,0.],[0.,0.,1.]]
    return {"intrinsic213":mul(mul(ry,rx),rz),"extrinsic213":mul(mul(rz,rx),ry),
            "intrinsic123":mul(mul(rx,ry),rz)}
def angle_error(actual,expected):
    relative=mul(transpose(expected),actual)
    c=(sum(relative[i][i] for i in range(3))-1.)/2.
    return math.degrees(math.acos(max(-1.,min(1.,c))))

def verify(text,arm):
    rows=list(csv.DictReader(io.StringIO(text)))
    controls=mixed=outside=matches123=matches213=0
    max_scipy=max_norm=max_sign=0.
    minimum=math.inf;witness=None
    for row in rows:
        p,r,y=[math.radians(float(row[k])) for k in ("pitch_deg","roll_deg","yaw_deg")]
        q=[float(row[k]) for k in ("x","y","z","w")]
        actual=qmatrix(q); refs=references(p,r,y)
        scipy_refs={"intrinsic213":Rotation.from_euler("YXZ",[p,r,y]).as_matrix(),
                    "extrinsic213":Rotation.from_euler("yxz",[p,r,y]).as_matrix(),
                    "intrinsic123":Rotation.from_euler("XYZ",[r,p,y]).as_matrix()}
        max_scipy=max(max_scipy,error(actual,Rotation.from_quat(q).as_matrix()),
                      *(error(refs[k],v) for k,v in scipy_refs.items()))
        max_norm=max(max_norm,abs(sum(v*v for v in q)-1.))
        max_sign=max(max_sign,error(actual,qmatrix([-v for v in q])))
        errors={k:error(actual,v) for k,v in refs.items()}
        best=min(error(actual,m) for k in ("intrinsic213","extrinsic213") for m in (refs[k],transpose(refs[k])))
        matches213+=errors["intrinsic213"]<=EPS
        if row["kind"]=="control":
            controls+=1
            assert errors["intrinsic213"]<=EPS and errors["extrinsic213"]<=EPS,row
        elif row["kind"]=="mixed":
            mixed+=1;outside+=best>EPS;matches123+=errors["intrinsic123"]<=EPS
            minimum=min(minimum,best)
        elif row["kind"]=="witness":
            witness={"angles_deg":[float(row[k]) for k in ("pitch_deg","roll_deg","yaw_deg")],
                     "quaternion_xyzw":q,"matrix_errors":errors,"best_213_family_error":best,
                     "intrinsic213_angular_error_deg":angle_error(actual,refs["intrinsic213"]),
                     "actual_matrix":actual,"intrinsic213_matrix":refs["intrinsic213"]}
        else:
            raise AssertionError(row)
    assert len(rows)==236 and controls==19 and mixed==216 and witness is not None
    assert max_scipy<=EPS and max_norm<=EPS and max_sign<=EPS
    if arm in ("original","withdrawal"):
        assert outside==mixed==matches123==216 and witness["best_213_family_error"]>EPS
    else:
        assert arm=="intrinsic213-candidate" and outside==0 and matches213==236
    return {"arm":arm,"rows":len(rows),"controls_passed":controls,"mixed_cases":mixed,
            "mixed_outside_213_family":outside,"mixed_matching_123":matches123,
            "all_rows_matching_intrinsic213":matches213,"minimum_mixed_213_family_error":minimum,
            "scipy_crosscheck_max_error":max_scipy,"unit_norm_max_error":max_norm,
            "quaternion_sign_alias_error":max_sign,"tolerance":EPS,"witness":witness}

def symbolic_identity(data):
    body=data.decode().split("pub fn euler213_to_quaternion",1)[1].split("\n}",1)[0]
    names=("sr","cr","sp","cp","sy","cy")
    variables=dict(zip(names,sympy.symbols("sr cr sp cp sy cy")))
    def convert(node):
        if isinstance(node,ast.Name):
            return variables[node.id]
        if isinstance(node,ast.BinOp):
            a,b=convert(node.left),convert(node.right)
            if isinstance(node.op,ast.Add):return a+b
            if isinstance(node.op,ast.Sub):return a-b
            if isinstance(node.op,ast.Mult):return a*b
        raise AssertionError(ast.dump(node))
    native={k:convert(ast.parse(v,mode="eval").body) for k,v in re.findall(r"let ([wxyz]) = ([^;]+);",body)}
    assert len(native)==4
    sr,cr,sp,cp,sy,cy=[variables[k] for k in names]
    product=hamilton(hamilton([cr,sr,0,0],[cp,0,sp,0]),[cy,0,0,sy])
    delta=[sympy.expand(native[k]-v) for k,v in zip("wxyz",product)]
    assert delta==[0,0,0,0]
    return {"identity":"native = qx(roll) * qy(pitch) * qz(yaw)","coefficient_differences":[str(v) for v in delta],
            "boundary":"Symbolic expansion, not a kernel-checked theorem or owner intent."}

def main():
    root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    here=Path(__file__).resolve().parent
    def git(*args):
        return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
    assert git("rev-parse","HEAD")==PIN and git("rev-parse","HEAD^{tree}")==TREE
    subprocess.run(["git","diff","--exit-code"],cwd=root,check=True)
    for path,blob in BLOBS.items():
        assert git("hash-object",path)==blob,path
    lib=root/"safe-time/src/lib.rs";original=lib.read_bytes()
    assert hashlib.sha256(original).hexdigest()==LIB_SHA
    for name in ("LICENSE","Cargo.lock","safe-time/src/lib.rs","safe-time/Cargo.toml","safe-time/README.md"):
        target=out/"upstream"/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
    (out/"symbolic-identity.json").write_text(json.dumps(symbolic_identity(original),indent=2)+"\n")
    def run(args,name):
        r=subprocess.run(["cargo","+1.94.1",*args],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (out/name).write_text(r.stdout)
        return r
    run(["--version"],"cargo-version.txt")
    subprocess.run(["rustc","+1.94.1","--version"],stdout=(out/"rustc-version.txt").open("w"),check=True)
    author=run(["test","--locked","-p","safe-time","--lib"],"author-before-harness.log")
    assert author.returncode==0 and "8 passed; 0 failed" in author.stdout
    for name,target in [("rotation_probe.rs","safe-time/examples/mathgraph_rotation_probe.rs"),
                        ("rotation_contract.rs","safe-time/tests/mathgraph_rotation_contract.rs")]:
        destination=root/target;assert not destination.exists(),destination
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes((here/name).read_bytes())
    candidate=original
    for old,new in [
        (b"let w = cr * cp * cy - sr * sp * sy;",b"let w = cr * cp * cy + sr * sp * sy;"),
        (b"let z = cr * cp * sy + sr * sp * cy;",b"let z = cr * cp * sy - sr * sp * cy;")]:
        assert candidate.count(old)==1
        candidate=candidate.replace(old,new)
    reports=[]
    try:
        for arm,data in [("original",original),("intrinsic213-candidate",candidate),("withdrawal",original)]:
            lib.write_bytes(data)
            author=run(["test","--locked","-p","safe-time","--lib"],arm+"-author.log")
            assert author.returncode==0 and "8 passed; 0 failed" in author.stdout
            regression=run(["test","--locked","-p","safe-time","--test","mathgraph_rotation_contract"],arm+"-contract.log")
            expected_exit=0 if arm=="intrinsic213-candidate" else 101
            assert regression.returncode==expected_exit,(arm,regression.stdout)
            if expected_exit:assert "213_CONTRACT_MISMATCH" in regression.stdout
            native=subprocess.run(["cargo","+1.94.1","run","--locked","--quiet","-p","safe-time",
                                   "--example","mathgraph_rotation_probe"],cwd=root,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            (out/(arm+"-build.log")).write_text(native.stderr)
            assert native.returncode==0,native.stderr
            (out/(arm+"-native.csv")).write_text(native.stdout)
            report=verify(native.stdout,arm)
            report.update(author_tests_passed=8,native_contract_exit=regression.returncode,
                          lib_sha256=hashlib.sha256(data).hexdigest(),lib_git_blob=git("hash-object","safe-time/src/lib.rs"))
            (out/(arm+"-report.json")).write_text(json.dumps(report,indent=2)+"\n")
            if arm=="intrinsic213-candidate":
                patch=subprocess.check_output(["git","diff","--","safe-time/src/lib.rs"],cwd=root)
                (out/"diagnostic-intrinsic213.patch").write_bytes(patch)
            reports.append(report)
            print(json.dumps({k:report[k] for k in ("arm","author_tests_passed","native_contract_exit",
                                                   "controls_passed","mixed_cases","mixed_outside_213_family")}),flush=True)
    finally:
        lib.write_bytes(original)
    assert (out/"original-native.csv").read_bytes()==(out/"withdrawal-native.csv").read_bytes()
    subprocess.run(["git","diff","--exit-code"],cwd=root,check=True)
    assert git("rev-parse","HEAD")==PIN and lib.read_bytes()==original
    summary={"terminal_form":"FINITE_COUNTERMODEL","source_commit":PIN,"source_tree":TREE,"source_blobs":BLOBS,
             "source_restored_byte_identical":True,"withdrawal_output_byte_identical":True,
             "numpy":np.__version__,"scipy":scipy.__version__,"sympy":sympy.__version__,
             "warranted":"Pinned helper matches intrinsic123 and violates both standard213 conventions and inverses on 216 mixed cases.",
             "unknown":"Maintainer intended convention, downstream operational use, mission effects.",
             "candidate_patch":"Two-sign intrinsic213 diagnostic only; owner-approved repair UNKNOWN.",
             "boundary":"safe-time helper and native tests only; not full SAFE qualification.","arms":reports}
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("PINNED_NATIVE_ROTATION_AUDIT_COMPLETE",flush=True)

if __name__=="__main__":main()
