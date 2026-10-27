"""Deterministic, conservative ACSL observation discovery from original C only.

No inspection or import of translated Rust. Syntactic family recognizer, not
a general ACSL theorem prover or natural-language requirement extractor.
"""
import hashlib,json,re
from pathlib import Path
from itertools import combinations_with_replacement,product

DATA=Path(__file__).with_name("FROZEN_MANIFEST.json")
def manifest():return json.loads(DATA.read_text())
def gitblob(path):
    import subprocess
    return subprocess.run(["git","hash-object",str(path)],check=True,capture_output=True,text=True).stdout.strip()
def function_signature(source):
    m=re.search(r"\b(int|size_t|unsigned)\s+([A-Za-z_][\w]*)\s*\(([^)]*)\)\s*\{",source)
    if not m:raise ValueError("FUNCTION_SIGNATURE_UNSUPPORTED")
    tokens=[]
    for arg in m.group(3).split(","):
        arg=arg.strip()
        val=re.search(r"([A-Za-z_]\w*)\s*$",arg)
        if not val:raise ValueError("PARAMETER_UNSUPPORTED")
        tokens.append({"name":val.group(1),"pointer":"*" in arg,"unsigned":"size_t" in arg or "unsigned" in arg})
    if len(tokens)!=3 or sum(t["pointer"] for t in tokens)!=1:
        raise ValueError("ONLY_THREE_ARGUMENT_POINTER_FUNCTIONS")
    return {"function":m.group(2),"returns_unsigned":m.group(1)!="int","parameters":tokens}
def behavior_bodies(contract):
    blocks={}
    for match in re.finditer(r"\bbehavior\s+([A-Za-z_]\w*)\s*:",contract):
        nxt=re.search(r"\bbehavior\s+[A-Za-z_]\w*\s*:|\b(?:complete|disjoint)\s+behaviors\s*;",contract[match.end():])
        end=match.end()+nxt.start() if nxt else len(contract)
        blocks[match.group(1)]=contract[match.end():end]
    return blocks
def scalar_result(body):
    m=re.search(r"ensures\s+\\result\s*==\s*(-?\d+|len|n|length)\b",body)
    return m.group(1) if m else None

def classify(c_text):
    contracts=re.findall(r"/\*@([\s\S]*?)\*/",c_text)
    whole="\n".join(contracts)
    sig=function_signature(c_text)
    clauses=behavior_bodies(whole)
    if not clauses: return dict(sig,status="UNKNOWN_UNSUPPORTED_CONTRACT",reason="NO_NAMED_BEHAVIORS")
    exists=[];absent=[]
    for label,body in clauses.items():
        m=re.search(r"\bassumes\s+([\s\S]*?);",body)
        if not m:continue
        assume=m.group(1)
        if r"\exists" in assume: exists.append(body)
        elif r"\forall" in assume and "!=" in assume: absent.append(body)
    if len(exists)!=1 or len(absent)!=1:
        return dict(sig,status="UNKNOWN_UNSUPPORTED_CONTRACT",reason="AMBIGUOUS_EXISTENCE_BEHAVIOR")
    missing=scalar_result(absent[0])
    present=scalar_result(exists[0])
    if missing is None:return dict(sig,status="UNKNOWN_UNSUPPORTED_CONTRACT",reason="NO_ABSENT_RESULT_EQUATION")
    if present=="1" and missing=="0":family="BOOLEAN_PRESENCE"
    elif missing=="-1" and (r"\result" in exists[0]):family="INDEX_OR_NEGATIVE_ONE"
    elif missing in ("len","n","length") and (r"\result" in exists[0]):family="INDEX_OR_LENGTH"
    else:return dict(sig,status="UNKNOWN_UNSUPPORTED_CONTRACT",reason="UNSUPPORTED_RESULT_KIND")
    signed_or_sorted=(r"requires Sorted:" in whole or
                      bool(re.search(r"requires\s+\\forall\s+integer[\s\S]{0,155}?<=.*?(?:\bbase\[|\barr\[)",whole)))
    # If source specifies sortedness via another syntax, don't silently drop it.
    if r"\forall" in whole and "requires" in whole and " <= " in whole:
        signed_or_sorted=signed_or_sorted or ("Sorted:" in whole)
    n_positive=bool(re.search(r"\brequires\s+(?:n|len|length)\s*>\s*0\s*;",whole))
    params=sig["parameters"]
    npos=next((i for i,p in enumerate(params) if not p["pointer"] and p["name"] in ("n","len","length")),None)
    if npos is None:return dict(sig,status="UNKNOWN_UNSUPPORTED_CONTRACT",reason="NO_LENGTH_PARAMETER")
    keypos=next((i for i,p in enumerate(params) if not p["pointer"] and i!=npos),None)
    return dict(sig,status="DISCOVERED_BOUNDED_CONTRACT",family=family,
                absent_value=missing,present_value=present,sorted_required=signed_or_sorted,
                empty_allowed=not n_positive,
                parameter_positions={"array":next(i for i,p in enumerate(params) if p["pointer"]),"length":npos,"key":keypos},
                diagnostics="Named ACSL behavior inference, finite model only")

def cases(spec,full=False):
    vals=tuple(manifest()["domain"]["values"]);keys=tuple(manifest()["domain"]["keys"])
    if full:
        maxlen=manifest()["domain"]["sorted_max_length"] if spec["sorted_required"] else manifest()["domain"]["unsorted_max_length"]
        for n in range(0 if spec["empty_allowed"] else 1,maxlen+1):
            rows=combinations_with_replacement(vals,n) if spec["sorted_required"] else product(vals,repeat=n)
            for row in rows:
                for key in keys:yield row,key
    else:
        # Deterministic minimal source-synthesized observations: missing,
        # matching and (when authorized) empty. No target feedback.
        row=(vals[0],vals[-1])
        yield row,keys[-1]
        yield row,vals[-1]
        if spec["empty_allowed"]:yield (),keys[-1]
        else:yield (vals[0],vals[0],vals[-1]),vals[0]
def authorized(spec,row,key,output):
    if type(output)!=int:return False
    positions={i for i,val in enumerate(row) if val==key}
    if spec["family"]=="BOOLEAN_PRESENCE":
        return output==(1 if positions else 0)
    if positions:return output in positions
    if spec["family"]=="INDEX_OR_NEGATIVE_ONE":return output==-1
    if spec["family"]=="INDEX_OR_LENGTH":return output==len(row)
    return False
def extract(root):
    frozen=manifest();selected=[]
    for item in frozen["cases"]:
        file=Path(root)/item["c"]
        if gitblob(file)!=item["c_blob"]:raise ValueError("SOURCE_HASH_DRIFT:"+item["c"])
        spec=classify(file.read_text())
        spec.update({"c":item["c"],"c_blob":item["c_blob"],"target":item["target"]})
        if spec["status"]=="DISCOVERED_BOUNDED_CONTRACT":
            spec["probes"]=[{"array":list(a),"key":k} for a,k in cases(spec)]
            spec["full_count"]=sum(1 for _ in cases(spec,full=True))
        selected.append(spec)
    return {"protocol":"SOURCE_ONLY_AUTONOMOUS_OBSERVATION_V1","source_only":True,
            "upstream":frozen["revision"],"discovery":selected}
