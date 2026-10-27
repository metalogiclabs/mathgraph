"""Conservative source-only ACSL quantifier/implication normalizer.

Recognizes four syntactic templates; explicitly not a full ACSL parser.
All obligations, probes and allowed input sets depend ONLY on C source bytes.
"""
import json,re,subprocess
from itertools import product
from pathlib import Path
MANIFEST=Path(__file__).with_name("FROZEN_MANIFEST.json")
def manifest():return json.loads(MANIFEST.read_text())
def squash(value):return re.sub(r"\s+","",value)
def compiled_contract(code):
    m=re.search(r"/\*@([\s\S]*?)\*/",code)
    return m.group(1) if m else ""
def normalize(code):
    raw=compiled_contract(code)
    c=squash(raw)
    if r"\old" in c or r"\separated" in c:
        return {"status":"UNKNOWN_UNSUPPORTED","reason":"OLD_STATE_POINTER_ALIASING_OUTSIDE_SUBSET"}
    sig=re.search(r"\b(int|void)\s+([A-Za-z_]\w*)\s*\(\s*int\s*\*\s*([A-Za-z_]\w*)\s*,\s*int\s+([A-Za-z_]\w*)\s*\)",code)
    if not sig:return {"status":"UNKNOWN_UNSUPPORTED","reason":"FUNCTION_SIGNATURE_OUTSIDE_SUBSET"}
    ret,name,arr,n=sig.groups()
    if "requires"+n+">0;" not in c and "requires"+n+">=0;" not in c:
        return {"status":"UNKNOWN_UNSUPPORTED","reason":"NO_SUPPORTED_LENGTH_PRECONDITION"}
    obligations=[]
    if (ret=="int" and r"\forallintegerk;" in c and r"\existsintegerk;" in c and
        (r"\result>="+arr+"[k]" in c and r"\result=="+arr+"[k]" in c)):
        family="MAX_OF_ARRAY"
        obligations=[
          {"quantifier":"FORALL","antecedent":"0<=k<n","consequent":"result>=array[k]"},
          {"quantifier":"EXISTS","predicate":"0<=k<n && result==array[k]"}]
    elif (ret=="int" and "behaviorall_even:" in c and "behaviorall_not_even:" in c and
          arr+"[k]%2==0" in c and arr+"[k]%2!=0" in c and
          r"ensures\result==1;" in c and r"ensures\result==0;" in c):
        family="ALL_EVEN_01"
        obligations=[
          {"quantifier":"FORALL","antecedent":"0<=k<n","consequent":"array[k]%2==0","result":1},
          {"quantifier":"EXISTS","predicate":"0<=k<n && array[k]%2!=0","result":0}]
    elif (ret=="void" and r"ensures\forallintegerk;" in c and
          "k%2==0" in c and arr+"[k]==0" in c):
        family="ZERO_EVEN_POSITIONS"
        obligations=[{"quantifier":"FORALL","antecedent":"0<=k<n && k%2==0","consequent":"array_post[k]==0"}]
    elif (ret=="void" and r"requires\forallintegerk;" in c and
          "a[k]==k" in c and "2*k<=INT_MAX" in c and
          r"ensures\forallintegerk;" in c and "a[k]==2*k" in c):
        family="DOUBLE_INDEX_INITIALIZED"
        obligations=[{"quantifier":"FORALL","antecedent":"0<=k<n","precondition":"array_pre[k]==k","consequent":"array_post[k]==2*k"}]
    else:return {"status":"UNKNOWN_UNSUPPORTED","reason":"NO_SOUND_SUPPORTED_POSTCONDITION_NORMAL_FORM"}
    frame="assigns\\nothing;" in c
    return {"status":"DISCOVERED_BOUNDED_CONTRACT","family":family,
            "function":name,"array_param":arr,"length_param":n,
            "return_type":ret,"frame_unchanged":frame,"obligations":obligations,
            "source_limitations":["Quantifiers evaluated only on finite valid input domain",
                                  "Template recognizer; no general ACSL equivalence proof"]}
def inputs(spec):
    kind=spec["family"]
    config=manifest()
    if kind=="DOUBLE_INDEX_INITIALIZED":
        for n in range(1,config["double_max_n"]+1):yield tuple(range(n))
    else:
        vals=config["values"]
        for n in range(1,config["array_max_n"]+1):
            yield from product(vals,repeat=n)
def probes(spec):
    kind=spec["family"]
    if kind=="MAX_OF_ARRAY":return [(-2,),(-2,2,1),(2,2,-1)]
    if kind=="ALL_EVEN_01":return [(2,),(2,4,6),(2,3)]
    if kind=="ZERO_EVEN_POSITIONS":return [(3,),(3,4,5),(-2,1,2,1)]
    if kind=="DOUBLE_INDEX_INITIALIZED":return [(0,),(0,1),(0,1,2,3)]
    return []
def authorized(spec,pre,post,result):
    kind=spec["family"]
    if spec["frame_unchanged"] and pre!=post:return False
    if kind=="MAX_OF_ARRAY":return result==max(pre)
    if kind=="ALL_EVEN_01":return result==(1 if all(x%2==0 for x in pre) else 0)
    if kind=="ZERO_EVEN_POSITIONS":
        return result is None and len(pre)==len(post) and all(post[i]==0 for i in range(0,len(pre),2))
    if kind=="DOUBLE_INDEX_INITIALIZED":
        return result is None and len(pre)==len(post) and all(post[i]==2*i for i in range(len(pre)))
    raise ValueError("UNSUPPORTED_FAMILY")
def discover(root):
    cfg=manifest()
    report=[]
    for entry in cfg["cases"]:
        path=Path(root)/entry["source"]
        h=subprocess.run(["git","-C",str(root),"hash-object",entry["source"]],capture_output=True,text=True,check=True).stdout.strip()
        if h!=entry["blob"]:raise ValueError("C_SOURCE_CHANGED:"+entry["source"])
        spec=normalize(path.read_text())
        spec.update({"source":entry["source"],"target":entry["target"],"c_blob":entry["blob"]})
        if spec["status"]=="DISCOVERED_BOUNDED_CONTRACT":
            spec["probes"]=[list(a) for a in probes(spec)]
            spec["full_input_count"]=sum(1 for _ in inputs(spec))
        report.append(spec)
    return {"protocol":cfg["protocol"],"source_only":True,"upstream":cfg["rev"],"cases":report}
