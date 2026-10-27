"""Source-only bounded ACSL old-state/frame/alias recognizer."""
import json,re,subprocess,itertools
from pathlib import Path
M=Path(__file__).with_name("FROZEN_MANIFEST.json")
def manifest():return json.loads(M.read_text())
def spec(c):
 x=re.search(r"/\*@([\s\S]*?)\*/",c)
 return re.sub(r"\s+","",x.group(1)) if x else ""
def classify(code):
 s=spec(code)
 if r"\at(" in s or "lemma" in s or "predicateunchanged" in s:
  return {"status":"UNKNOWN_UNSUPPORTED","reason":"TWO_STATE_LABEL_QUANTIFICATION"}
 if ("assigns*a;" in s and r"ensures\old(*b)==>*a==0;" in s
     and r"ensures!\old(*b)==>*a==\old(*a);" in s
     and r"ensures*b==\old(*b);" in s and r"\separated(a,b)" in s):
  family="CONDITIONAL_RESET_OLD_FRAME"
 elif ("assigns*a;" in s and r"ensures*a==\old(*a)+*b;" in s
       and r"ensures*b==\old(*b);" in s and r"\separated(a,b)" in s):
  family="INCREMENT_OLD_FRAME"
 elif ("assigns*a,*b;" in s and r"ensures*a==\old(*b)&&*b==\old(*a);" in s):
  family="TWO_POINTER_SWAP_DISTINCT_SCOPE"
 elif ("0<=n1<n&&0<=n2<n" in s
       and s.count(r"arr[n2]==\old(arr[n1])")==2 and "assigns" not in s):
  family="WEAK_DUPLICATE_ARRAY_POST"
 elif (r"assigns\nothing;" in s and r"ensures\result==*p+*q;" in s
       and r"\separated(p,q)" in s):
  family="POINTER_SUM_UNCHANGED"
 elif (r"assigns\nothing;" in s and r"ensures\result==*a+5;" in s
       and r"*a<=INT_MAX-5" in s):
  family="POINTER_PLUS_FIVE_UNCHANGED"
 else:
  return {"status":"UNKNOWN_UNSUPPORTED","reason":"UNRECOGNIZED_ACSL_OLD_FRAME_FORM"}
 return {"status":"DISCOVERED_BOUNDED_CONTRACT","family":family,
         "distinct_pointer_scope_only":family=="TWO_POINTER_SWAP_DISTINCT_SCOPE",
         "no_inferred_frame":family=="WEAK_DUPLICATE_ARRAY_POST",
         "method":"Conservative original-ACSL literal template, not complete language parser"}
def cases(family):
 if family=="CONDITIONAL_RESET_OLD_FRAME":
  yield from itertools.product((-3,0,5),(-2,0,1,4))
 elif family=="INCREMENT_OLD_FRAME":
  yield from itertools.product((-5,-1,0,3,5),(-3,0,2))
 elif family=="TWO_POINTER_SWAP_DISTINCT_SCOPE":
  yield from itertools.product((-3,-1,0,2,5),(-3,0,2,5))
 elif family=="WEAK_DUPLICATE_ARRAY_POST":
  for n in range(1,4):
   for row in itertools.product(manifest()["small_values"],repeat=n):
    for i in range(n):
     for j in range(n):yield (row,i,j)
 elif family=="POINTER_SUM_UNCHANGED":
  yield from itertools.product((-5,-2,0,2,5),(-5,0,3,5))
 elif family=="POINTER_PLUS_FIVE_UNCHANGED":
  for x in (-5,-2,-1,0,1,2,5):yield (x,)
 else:raise ValueError("NO_RECOGNIZED_FAMILY")
def probes(f):
 if f=="CONDITIONAL_RESET_OLD_FRAME":return [(-3,0),(5,1),(0,-2)]
 if f=="INCREMENT_OLD_FRAME":return [(-5,2),(0,0),(3,-3)]
 if f=="TWO_POINTER_SWAP_DISTINCT_SCOPE":return [(-3,5),(0,0),(2,-3)]
 if f=="WEAK_DUPLICATE_ARRAY_POST":return [((-2,0,2),0,2),((2,-2),0,0),((0,2,-2),2,1)]
 if f=="POINTER_SUM_UNCHANGED":return [(-5,3),(0,0),(5,-5)]
 if f=="POINTER_PLUS_FIVE_UNCHANGED":return [(-5,),(0,),(5,)]
 return []
def authorizes(family,pre,post,result):
 if family=="CONDITIONAL_RESET_OLD_FRAME":
  a,b=pre;ap,bp=post
  return ap==(0 if b else a) and bp==b
 if family=="INCREMENT_OLD_FRAME":
  a,b=pre;ap,bp=post
  return ap==a+b and bp==b
 if family=="TWO_POINTER_SWAP_DISTINCT_SCOPE":
  a,b=pre
  return tuple(post)==(b,a)
 if family=="WEAK_DUPLICATE_ARRAY_POST":
  row,i,j=pre
  return len(post)==len(row) and post[j]==row[i]
 if family=="POINTER_SUM_UNCHANGED":
  a,b=pre
  return tuple(post)==(a,b) and result==a+b
 if family=="POINTER_PLUS_FIVE_UNCHANGED":
  (a,)=pre
  return tuple(post)==(a,) and result==a+5
 raise ValueError("NO_AUTHORIZED_RULE")
def extract(root):
 root=Path(root);m=manifest();items=[]
 for row in m["cases"]:
  blob=subprocess.run(["git","-C",str(root),"hash-object",row["c"]],capture_output=True,text=True,check=True).stdout.strip()
  if blob!=row["blob"]:raise ValueError("SOURCE_PIN_MISMATCH:"+row["c"])
  x=classify((root/row["c"]).read_text());x.update(row)
  if x["status"]=="DISCOVERED_BOUNDED_CONTRACT":
   x["test_count"]=sum(1 for _ in cases(x["family"]))
   x["probes"]=[list(y) for y in probes(x["family"])]
  items.append(x)
 return {"protocol":m["protocol"],"source_only":True,"revision":m["revision"],"cases":items}
