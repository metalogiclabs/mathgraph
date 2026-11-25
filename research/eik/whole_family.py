"""Whole-family replacement: joint rounding slabs, no old ta_r fallback.
Independent exact-c is the synthesis oracle. Search failure is UNKNOWN.
All partitions are contiguous mathematical cells, independent of scoring samples.
"""
import argparse, hashlib, json, pathlib, re
import numpy as np
from synth import oracle, exact_eval
from joint import fit
BASE="3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4"
H=0x3f800000
START=0x3ffe0000
MID=0x40800000
END=0x41120000
ANCHOR=H-6144
P=argparse.ArgumentParser()
P.add_argument("reference");P.add_argument("baseline");P.add_argument("out");P.add_argument("variant")
a=P.parse_args()
out=pathlib.Path(a.out);out.mkdir(exist_ok=True,parents=True)
src=pathlib.Path(a.baseline).read_text();assert hashlib.sha256(src.encode()).hexdigest()==BASE
f=oracle(a.reference,"sigmoid");g=oracle(a.reference,"tanh")
journal={"variant":a.variant,"base":BASE,"groups":[],"attempts":[],"status":"UNKNOWN"}
def save():
    (out/"synthesis.json").write_text(json.dumps(journal,indent=2))
def one(s,x,y):
    assert s.count(x)==1,(x[:100],s.count(x))
    return s.replace(x,y)
def drop(s,pattern):
    s,n=re.subn(pattern,"",s,flags=re.S);assert n==1,(pattern,n);return s
def search(lo,hi,options,fold):
    # Oracle is the entire contiguous region, not a scorer pool.
    y=np.fromiter((f(w+0x800000) for w in range(lo,hi)),dtype=np.int64,count=hi-lo)
    z=np.fromiter((g(w) for w in range(lo,hi)),dtype=np.int64,count=hi-lo)
    assert np.all((y>=0x3f000000)&(y<=H)) and np.all((z>=0x3f000000)&(z<=H))
    for k,d,s in options:
        n=1<<k;assert lo%n==hi%n==0
        t=(np.arange(n,dtype=np.int64)-n//2)<<(32-k);rows=[]
        attempt={"lo":lo,"hi":hi,"k":k,"d":d,"s":s,"fold":fold,"status":"UNKNOWN","rows_passed":0}
        journal["attempts"].append(attempt);save()
        for ix in range(0,len(y),n):
            yy=y[ix:ix+n];zz=z[ix:ix+n];b=int(yy[n//2])
            ys=yy-b;zt=zz-(2*b-H)
            low4=np.maximum(4*ys,2*zt+1);high4=np.minimum(4*(ys+1),2*(zt+1)+1)
            r=fit(low4,high4,t,k,d,s)
            if r["status"]!="exact":
                attempt.update(failed_cell=lo+ix,reason=r);break
            c=r["coeff"];v=exact_eval(c,t)
            assert np.array_equal(b+(v>>s),yy)
            assert np.array_equal(2*b-H+((v-(1<<(s-2)))>>(s-1)),zz)
            if fold:
                off=(b-ANCHOR)*(1<<s)
                q=v+off
                if int(q.min())<1<<(s-2) or int(q.max())>=2**32 or not 0<=off+c[0]<2**32:
                    attempt.update(failed_cell=lo+ix,reason="folded-coordinate-out-of-range");break
                assert np.array_equal(ANCHOR+(q>>s),yy)
                assert np.array_equal(2*ANCHOR-H+((q-(1<<(s-2)))>>(s-1)),zz)
                c=[off+c[0],*c[1:]]
            rows.append({"base":b,"coeff":c,"margin_lsb":r["margin_lsb"]})
            attempt["rows_passed"]=len(rows)
            if len(rows)%64==0: print(hex(lo),k,d,s,"rows",len(rows),flush=True);save()
        if len(rows)==len(y)//n:
            attempt["status"]="EXACT_FULL_GROUP"
            record={"lo":lo,"hi":hi,"k":k,"d":d,"s":s,"fold":fold,"rows":rows}
            journal["groups"].append(record);save();return record
        print("UNKNOWN",attempt,flush=True);save()
    return None
early_cubic=[(16,3,17),(15,3,17),(15,3,18),(14,3,19)]
tail_cubic=[(17,3,18),(16,3,18),(15,3,18),(14,3,19)]
if a.variant=="uniform-cubic":
    groups=[search(START,END,early_cubic,False)]
elif a.variant=="split-cubic":
    groups=[search(START,MID,early_cubic,False)]
    if groups[0] is not None:groups.append(search(MID,END,tail_cubic,True))
elif a.variant=="split-quadratic":
    groups=[search(START,MID,[(14,2,18),(13,2,19),(12,2,20)],False)]
    if groups[0] is not None:groups.append(search(MID,END,[(16,2,18),(15,2,18),(14,2,19),(13,2,19)],True))
else:raise ValueError(a.variant)
if any(r is None for r in groups):
    journal["status"]="UNKNOWN_NO_COMPLETE_REPRESENTATION";save();raise SystemExit(0)
assert groups[0]["lo"]==START and groups[-1]["hi"]==END
assert all(x["hi"]==y["lo"] for x,y in zip(groups,groups[1:]))
# Remove obsolete table and both old reconstruction paths; no original fallback in this family.
src=drop(src,r"static const struct rx_r ta_r\[138\] = \{.*?\};\n")
src=drop(src,r"cellx_: \{\n.*?\n    \}\n(?=lt_:)")
src=drop(src,r"scella_: \{\n.*?\n    \}\n(?=slt_:)")
# Unreachable historical alternative kernels are not part of the exported control.
# Remove for source-size budget; the control binary must remain the unchanged archive.
start=src.index("static const struct { int32_t c0, c1, c2, c3; } small_exp_rows[]")
end=src.index("uint32_t eik_sigmoid(uint32_t w)\n{",start)
src=src[:start]+src[end:]
tables=[];sb=[];tb=[]
for i,r in enumerate(groups):
    k,d,s,lo,fold=[r[x] for x in ("k","d","s","lo","fold")]
    name="jr"+str(i)
    fields=("uint32_t c0;" if fold else "uint32_t base; int32_t c0;")+" int32_t "+",".join("c"+str(j) for j in range(1,d+1))+";"
    vals=[]
    for row in r["rows"]:
        c=row["coeff"]
        vals.append("{"+(",".join([str(c[0])+"u"]+list(map(str,c[1:]))) if fold else ",".join([str(row["base"])+"u"]+list(map(str,c))))+"}")
    tables.append("struct "+name+" { "+fields+" };\nstatic const struct "+name+" "+name+"_rows["+str(len(vals))+"]={\n"+",\n".join(vals)+"\n};")
    p="int32_t t=(int32_t)((w<<"+str(32-k)+")^0x80000000u); int32_t p=r->c"+str(d)+";"
    p+="".join(" p=r->c"+str(j)+"+mulhs_r(p,t);" for j in range(d-1,0,-1))
    p+=(" uint32_t q=r->c0+(uint32_t)mulhs_r(p,t);" if fold else " int32_t q=r->c0+mulhs_r(p,t);")
    sigbase=str(ANCHOR)+"u" if fold else "r->base"
    tanbase=str(2*ANCHOR-H)+"u" if fold else "(2u*r->base-0x3f800000u)"
    tables.append("static inline uint32_t "+name+"_sig(uint32_t w) { const struct "+name+" *r=&"+name+"_rows[(w>>"+str(k)+")-"+str((lo+0x800000)>>k)+"u]; "+p+" return "+sigbase+"+(uint32_t)(q>>"+str(s)+"); }")
    tables.append("static inline uint32_t "+name+"_tan(uint32_t w,uint32_t t0) { const struct "+name+" *r=&"+name+"_rows[(t0>>"+str(k+1)+")-"+str(lo>>k)+"u]; "+p+" return ("+tanbase+"+(uint32_t)((q-"+str(1<<(s-2))+("" if fold else "")+")>>"+str(s-1)+"))|(w&0x80000000u); }")
    sb.append(name+"_sig(w)");tb.append(name+"_tan(w,t)")
# The existing hi_/phi_ domain checks remain; dispatch is replaced, not augmented globally.
marker="static inline uint32_t eik_tanh_r(uint32_t w)\n{"
src=one(src,marker,"\n".join(tables)+"\n"+marker)
sret=sb[0] if len(sb)==1 else "(w<0x41000000u?"+sb[0]+":"+sb[1]+")"
tret=tb[0] if len(tb)==1 else "(t<0x81000000u?"+tb[0]+":"+tb[1]+")"
src,n=re.subn(r"if \(t <= 0x82206000u\) \{\n.*?\n    \}\n(?=    if \(\(int32_t\)w < 0\))","if (t <= 0x82206000u) return "+tret+";\n",src,flags=re.S);assert n==1
src,n=re.subn(r"phi_:\n    if \(w > 0x418AB000u\)\n        goto phuge_;\n    \{\n.*?\n    \}\n(?=phuge_:)","phi_:\n    if (w > 0x418AB000u) goto phuge_;\n    return "+sret+";\n",src,flags=re.S);assert n==1
assert not re.search(r"\bta_r\b|goto cellx_|goto scella_",src)
if len(src.encode())>262144:
    journal["status"]="REJECTED_SOURCE_SIZE";journal["bytes"]=len(src.encode());save();raise SystemExit(0)
(out/"candidate.c").write_text(src)
journal["status"]="CANDIDATE_FULL_REGION";journal["source_sha256"]=hashlib.sha256(src.encode()).hexdigest();journal["source_bytes"]=len(src.encode())
journal["table_bytes"]=sum(len(r["rows"])*4*(r["d"]+1+(not r["fold"])) for r in groups)
save()
print(journal["status"],journal["source_sha256"],journal["table_bytes"],flush=True)
