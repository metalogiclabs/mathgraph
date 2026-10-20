#!/usr/bin/env python3
"""Separate equal-information conventional author-doc rulebook baseline.

Reads the same documentation files as candidate, scans adjacent fully-qualified
call syntax and explicit author statements. It has no implementation/test output.
"""
import argparse,ast,hashlib,json,pathlib,re
MODCALL=re.compile(r"(?P<module>\b[a-zA-Z_]\w*)\.(?P<function>[a-zA-Z_]\w*)\((?P<args>[^()\n]{0,120})\)")
def parse_opts(text):
 try:
  node=ast.parse("f("+text+")",mode="eval").body
  if len(node.args)>1 or any(not isinstance(v,(ast.Name,ast.Constant)) for v in node.args) or any(k.arg is None for k in node.keywords):return None
  return {k.arg:ast.literal_eval(k.value) for k in node.keywords}
 except (SyntaxError,TypeError,ValueError):return None

def assess(root):
 root=pathlib.Path(root);docs=[]
 for d in (root,root/"docs",root/"doc"):
  if not d.is_dir():continue
  for p in (list(d.iterdir()) if d==root else list(d.rglob("*"))):
   if p.is_file() and p.suffix.lower() in (".rst",".md") and p.stat().st_size<=150000 and not any(x in ("tests","test","examples","vendor") for x in p.relative_to(root).parts):docs.append(p)
 rows=[];files={}
 for p in sorted(set(docs),key=str)[:60]:
  raw=p.read_bytes();rel=str(p.relative_to(root));files[rel]=hashlib.sha256(raw).hexdigest()
  lines=raw.decode("utf-8",errors="replace").splitlines()
  for number,line in enumerate(lines):
   sentence=line.lower()
   mode=None
   if "does not escape html" in sentence or "non-escaped instance" in sentence:mode="raw"
   elif re.search(r"\bescapes?\s+(?:raw\s+)?html\b",sentence):mode="escape"
   if not mode:continue
   context="\n".join(lines[max(0,number-12):number+1])
   matches=list(MODCALL.finditer(context))
   matching=[v for v in matches if v.group("function")+"(" in line]
   call=matching[-1] if matching else matches[-1] if matches else None
   if call is None:continue
   options=parse_opts(call.group("args"))
   if options is None or any(not isinstance(v,(str,bool,int,type(None))) for v in options.values()):continue
   if mode=="escape" and options.get("escape") is False:continue
   raw_line=next((x for x in context.splitlines() if call.group(0) in x),"")
   factory=bool(re.search(r"^\s*\w+\s*=\s*"+re.escape(call.group("module")+"."+call.group("function"))+r"\(",raw_line))
   rows.append({"factory":factory,"path":rel,"path_sha256":files[rel],"line":number+1,
                "authority_sentence":line.strip(),"authority_sha256":hashlib.sha256(line.strip().encode()).hexdigest(),
                "module":call.group("module"),"function":call.group("function"),"kwargs":options,
                "mode":mode,"relation":"HTMLParser script tag "+("absent" if mode=="escape" else "present")})
 seen={}
 for item in rows:
  key=(item["module"],item["function"],item["mode"],json.dumps(item["kwargs"],sort_keys=True))
  seen.setdefault(key,item)
 return {"protocol":"HTML_DOC_AUTHORITY_V7_EXPERT_RULE_BASELINE","files":files,"claims":list(seen.values())[:16],
         "status":"CANDIDATE_DOC_BOUND" if seen else "UNKNOWN_NO_EXPLICIT_CALL_AND_HTML_CONTRACT",
         "baseline":"independently coded conventional documentation inspection recipe, not a blind human reviewer"}
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--source",type=pathlib.Path,required=True);ap.add_argument("--out",type=pathlib.Path,required=True);a=ap.parse_args()
 v=assess(a.source);a.out.parent.mkdir(exist_ok=True,parents=True);a.out.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n");print("EXPERT_RULE_PRE_NATIVE",v["status"],[(x["module"],x["function"],x["mode"]) for x in v["claims"]])
