"""Source-only pairwise alias and null call-admission discovery.

Purposefully limited ACSL grammar. No Rust inputs or imported target metadata,
except opaque target path for later exact-identity binding. Missing proof of
entire C call-domain semantics stays UNKNOWN.
"""
import json,re,subprocess
from pathlib import Path
PATH=Path(__file__).with_name("FROZEN_MANIFEST.json")
def manifest():return json.loads(PATH.read_text())
def squeeze(s):return re.sub(r"\s+","",s)
def functions(code):
    pattern=r"/\*@([\s\S]*?)\*/\s*(?:int|void|size_t|unsigned)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{"
    return [(m.group(1),m.group(2),m.group(3)) for m in re.finditer(pattern,code)]
def params(sig):
    args=[]
    for a in sig.split(","):
        a=a.strip()
        name=re.search(r"([A-Za-z_]\w*)\s*(?:\[[^]]*\])?\s*$",a)
        if not name:raise ValueError("UNSUPPORTED_PARAMETER:"+a)
        isptr=("*" in a or "[" in a)
        args.append({"name":name.group(1),"pointer":isptr,"c_decl":a})
    return args
def separating_pairs(acsl,names):
    # Only accept \separated containing a pair or a single multi-argument
    # assertion. Flatten path-range suffixes separately; do not invent pairs.
    out=set()
    for m in re.finditer(r"\\separated\s*\(",acsl):
        tail=acsl[m.end():]
        depth=1; i=0
        while i<len(tail) and depth:
            if tail[i]=="(":depth+=1
            elif tail[i]==")":depth-=1
            i+=1
        if depth:continue
        block=tail[:i-1]
        # Known ACSL range expressions have commas only between distinct
        # pointer expressions, not the integer range bounds.
        terms=re.split(r",\s*(?=[A-Za-z_]\w*\s*(?:[+,)]|$))",block)
        detected=[]
        for term in terms:
            z=re.match(r"\s*([A-Za-z_]\w*)",term)
            if z and z.group(1) in names:detected.append(z.group(1))
        for k,a in enumerate(detected):
            for b in detected[k+1:]:
                out.add(tuple(sorted((a,b))))
    return out
def extract_contract(code,fn):
    matches=[x for x in functions(code) if x[1]==fn]
    if len(matches)!=1:return {"status":"UNKNOWN_SOURCE","reason":"MISSING_OR_AMBIGUOUS_FUNCTION"}
    acsl,name,sig=matches[0]; allparams=params(sig)
    ptrs=[p for p in allparams if p["pointer"]]
    if len(ptrs)<2:return {"status":"UNKNOWN_SOURCE","reason":"NOT_MULTIPLE_POINTERS"}
    original=squeeze(acsl)
    if "requires" not in original or not any(z in original for z in ("valid(","valid_read(","NULL","separated(")):
        return {"status":"UNKNOWN_SOURCE","reason":"UNSUPPORTED_POINTER_ADMISSION"}
    pnames={p["name"] for p in ptrs}
    pairs=separating_pairs(acsl,pnames)
    obligations=[]
    for k,p in enumerate(ptrs):
        for q in ptrs[k+1:]:
            pair=tuple(sorted((p["name"],q["name"])))
            admit=pair not in pairs
            # Might have relational restrictions not expressible by raw
            # \separated alone. We do NOT promote arbitrary C preconditions.
            nullable={name for name in pair if
                      re.search(r"\b"+re.escape(name)+r"\s*==\s*NULL\s*\|\|\s*\\valid_read\s*\(\s*"+re.escape(name)+r"\s*\)",acsl)}
            unknown_pre=bool(re.search(r"\b(?:requires|assumes)\b[^;]*(?:\\disjoint|\\at|\\fresh|\\valid_function)",acsl))
            obligations.append({"pair":list(pair),"source_alias_admission":"PERMITTED_ABSENT_SEPARATION" if admit else "FORBIDDEN_EXPLICIT_SEPARATION",
                                "source_nullable":sorted(nullable),"other_preconditions_outside_scope":unknown_pre})
    return {"status":"SOURCE_ONLY_PAIRWISE_WARRANT","fn":fn,"pointers":[p["name"] for p in ptrs],
            "arguments":allparams,"explicit_separated_pairs":[list(x) for x in sorted(pairs)],
            "obligations":obligations,
            "qualification":"Necessary pairwise syntactic condition; no universal ACSL satisfiability proof"}
def scan(root):
    m=manifest();result=[]
    for x in m["sources"]:
        path=Path(root)/x["c"]
        h=subprocess.run(["git","-C",str(root),"hash-object",x["c"]],check=True,capture_output=True,text=True).stdout.strip()
        if h!=x["blob"]:raise ValueError("SOURCE_C_DRIFT:"+x["id"])
        observed=extract_contract(path.read_text(),x["fn"])
        observed.update(x);result.append(observed)
    return {"protocol":m["protocol"],"source_only":True,"source_rev":m["revision"],
            "tasks":result}
