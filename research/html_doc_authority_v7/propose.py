#!/usr/bin/env python3
"""Pre-native explicit documentation-to-HTML observer. No source imports."""
import ast,argparse,hashlib,json,pathlib,re
CLAIM=[("escape",re.compile(r"\bescapes?\s+(?:raw\s+)?html\b|\bescape\s+html\s+tags\b",re.I)),
       ("raw",re.compile(r"\bdoes\s+not\s+escape\s+html\b|\bnon[- ]escaped\s+instance\b",re.I))]
CALL=re.compile(r"(?<![\w.])(?P<module>[A-Za-z_]\w*)\.(?P<function>[A-Za-z_]\w*)\s*\((?P<args>[^()\n]{0,120})\)")
def kwargs(s):
 if not s.strip():return {}
 try:
  call=ast.parse("f("+s+")",mode="eval").body
  if call.args or any(k.arg is None for k in call.keywords):return None
  values={k.arg:ast.literal_eval(k.value) for k in call.keywords}
  return values if len(values)==len(call.keywords) and all(isinstance(v,(str,bool,int,type(None))) for v in values.values()) else None
 except (SyntaxError,ValueError,TypeError):return None
def discover(root):
 root=pathlib.Path(root)
 docs=[]
 for base in (root,root/"docs",root/"doc"):
  if not base.is_dir():continue
  files=list(base.iterdir()) if base==root else list(base.rglob("*"))
  for p in files:
   if p.is_file() and p.suffix.lower() in (".rst",".md") and p.stat().st_size<=150000 and not any(x in ("test","tests","examples","vendor") for x in p.relative_to(root).parts):
    docs.append(p)
 docs=sorted(set(docs),key=lambda x:str(x.relative_to(root)))[:60]
 files={};claims=[];unknown=[]
 for p in docs:
  raw=p.read_bytes();name=str(p.relative_to(root))
  files[name]=hashlib.sha256(raw).hexdigest()
  lines=raw.decode("utf-8",errors="replace").splitlines()
  for i,line in enumerate(lines):
   for mode,pat in CLAIM:
    if not pat.search(line):continue
    if mode=="escape" and re.search(r"does\\s+not\\s+escape|non[- ]escaped|unescaped",line,re.I):continue
    window="\n".join(lines[max(0,i-12):i+1])
    calls=list(CALL.finditer(window))
    favored=[c for c in calls if c.group("function")+"(" in line]
    c=favored[-1] if favored else calls[-1] if calls else None
    if c is None:
     unknown.append({"path":name,"line":i+1,"reason":"MISSING_QUALIFIED_CALL"});continue
    opts=kwargs(c.group("args"))
    if opts is None:
     unknown.append({"path":name,"line":i+1,"reason":"UNSUPPORTED_LITERAL_ARGS"});continue
    if opts.get("escape") is False and mode=="escape":
     unknown.append({"path":name,"line":i+1,"reason":"CONTRADICTORY_CONFIG"});continue
    anchor=line if c.group(0) in line else "\n".join(lines[max(0,i-12):i+1])
    call_line=next((text for text in anchor.splitlines() if c.group(0) in text),"")
    factory=bool(re.search(r"^\\s*[A-Za-z_]\\w*\\s*=\\s*"+re.escape(c.group("module")+"."+c.group("function"))+r"\\(",call_line))
    claims.append({"factory":factory,"path":name,"path_sha256":files[name],"line":i+1,"authority_sentence":line.strip(),
                   "authority_sha256":hashlib.sha256(line.strip().encode()).hexdigest(),
                   "module":c.group("module"),"function":c.group("function"),
                   "kwargs":opts,"mode":mode,"relation":"HTMLParser script tag "+("absent" if mode=="escape" else "present")})
 unique={}
 for c in claims:
  k=(c["module"],c["function"],json.dumps(c["kwargs"],sort_keys=True),c["mode"])
  unique.setdefault(k,c)
 return {"protocol":"HTML_DOC_AUTHORITY_V7","files":files,"claims":list(unique.values())[:16],
         "unknowns":unknown[:50],"status":"CANDIDATE_DOC_BOUND" if unique else "UNKNOWN_NO_EXPLICIT_CALL_AND_HTML_CONTRACT"}
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--source",type=pathlib.Path,required=True);ap.add_argument("--out",type=pathlib.Path,required=True);a=ap.parse_args()
 v=discover(a.source);a.out.parent.mkdir(exist_ok=True,parents=True);a.out.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
 print("PRE_NATIVE_DOC_CONTRACT",v["status"],[(x["module"],x["function"],x["mode"]) for x in v["claims"]])
