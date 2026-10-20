#!/usr/bin/env python3
"""Independent protected HTML tag oracle; candidate and equally informed rulebook.

The executed source and doc auth are frozen. Failure to establish source-declared
identity or native test authority yields UNKNOWN. No general sanitization claim.
"""
import argparse,hashlib,html,html.parser,importlib,json,pathlib,sys,xml.etree.ElementTree as ET
PROBE="<script>alert(1)</script>"
class Observer(html.parser.HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.script=False
 def handle_starttag(self,tag,attrs):
  if tag.lower()=="script":self.script=True
 def handle_startendtag(self,tag,attrs):
  if tag.lower()=="script":self.script=True
def parsed_script(text):
 p=Observer();p.feed(text);p.close();return p.script
def native(junit):
 x=ET.parse(junit).getroot();nodes=[x] if x.tag=="testsuite" else list(x.iter("testsuite"))
 sums={name:sum(int(n.attrib.get(name,0)) for n in nodes) for name in ("tests","errors","failures","skipped")}
 sums["admitted"]=sums["tests"]>sums["skipped"] and sums["errors"]==sums["failures"]==0
 return sums
def evaluate(prop,source,nt):
 rows=[]
 for item in prop["claims"]:
  row={"claim":item,"status":"UNKNOWN","observation":{}}
  filename=source/item["path"]
  if hashlib.sha256(filename.read_bytes()).hexdigest()!=item["path_sha256"]:
   row["status"]="UNKNOWN_CHANGED_AUTHOR_SOURCE";rows.append(row);continue
  lines=filename.read_text(encoding="utf8",errors="replace").splitlines()
  line=item["line"]
  if line<1 or line>len(lines) or hashlib.sha256(lines[line-1].strip().encode()).hexdigest()!=item["authority_sha256"]:
   row["status"]="UNKNOWN_MISSING_EXACT_AUTHOR_SENTENCE";rows.append(row);continue
  if not nt["admitted"]:
   row["status"]="UNKNOWN_NATIVE_SUITE";rows.append(row);continue
  try:
   module=importlib.import_module(item["module"])
   if not pathlib.Path(module.__file__).resolve().is_relative_to(source.resolve()):
    row["status"]="UNKNOWN_IMPORTED_WRONG_SOURCE";rows.append(row);continue
   fn=getattr(module,item["function"])
   if item["factory"]:
    rendered=fn(**item["kwargs"])
    if not callable(rendered):raise TypeError("documented factory returned noncallable")
    result=rendered(PROBE)
   else:
    result=fn(PROBE,**item["kwargs"])
   if not isinstance(result,str):
    row["status"]="UNKNOWN_NON_HTML_STRING";rows.append(row);continue
   script=parsed_script(result)
   escaped="&lt;script" in result.lower() and "alert(1)" in result
   row["observation"]={"output_repr":repr(result)[:600],"script_tag":script,"literal_tag_escaped":escaped}
   if item["mode"]=="escape":
    correct=(not script and escaped)
   else:
    correct=script
   # Two independent standard library controls on the same attack/probe.
   negative=parsed_script(PROBE) and not parsed_script(html.escape(PROBE))
   row["observation"]["independent_reference_controls"]=bool(negative)
   row["status"]=("WARRANTED_BOUNDED_DOC_HTML_SCRIPT_OBSERVATION" if correct and negative else
                   "REJECTED_BOUNDED_AUTHOR_DOC_RELATION" if not correct and negative else
                   "UNKNOWN_REFERENCE_CONTROLS")
  except Exception as e:
   row["status"]="UNKNOWN_UNSUPPORTED_NATIVE_CALL";row["observation"]["error"]=type(e).__name__+":"+str(e)[:240]
  rows.append(row)
 return rows
def judge(root,source,cand,expert,junit,metadata):
 assert cand["protocol"]=="HTML_DOC_AUTHORITY_V7" and expert["protocol"]=="HTML_DOC_AUTHORITY_V7_EXPERT_RULE_BASELINE"
 assert cand["files"]==expert["files"],"BASELINE_INFORMATION_MISMATCH"
 results={}
 status=native(junit)
 for arm,prop in (("candidate",cand),("expert_rule",expert)):
  rows=evaluate(prop,source,status)
  results[arm]={"status":prop["status"],"rows":rows,"warrants":sum(x["status"].startswith("WARRANTED_BOUNDED") for x in rows),
                "rejections":sum(x["status"].startswith("REJECTED_BOUNDED") for x in rows),
                "unknowns":sum(x["status"].startswith("UNKNOWN") for x in rows)}
 a,b=results["candidate"],results["expert_rule"]
 if not (cand["claims"] or expert["claims"]):verdict="INCONCLUSIVE_NO_PROPOSALS"
 elif not status["admitted"]:verdict="INCONCLUSIVE_NATIVE_AUTHORITY"
 elif a["warrants"]==b["warrants"] and a["rejections"]==b["rejections"]:verdict="AUTHORED_RULE_TIE"
 else:verdict="AUTHORED_RULE_DIFFERENCE_NOT_HUMAN_SUPERIORITY"
 return {"status":"EXECUTED_NATIVE_BOUNDED" if status["admitted"] else "UNKNOWN_NATIVE_AUTHORITY",
  "metadata":metadata,"native":status,"arms":results,
  "comparison":{"verdict":verdict,"candidate_warrants":a["warrants"],"expert_rule_warrants":b["warrants"],
                "baseline":"separate equal-information expert-authored code, NOT a competent live reviewer"},
  "bounds":"source-declared HTML escaping on one script-token sample and raw parser; NOT sanitization, author intentions outside docs, or autonomous observation grammar"}
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 for name in ("source","candidate","expert","junit","metadata","out"):
  ap.add_argument("--"+name,type=pathlib.Path,required=True)
 a=ap.parse_args();source=a.source.resolve()
 cand=json.loads(a.candidate.read_text());expert=json.loads(a.expert.read_text());metadata=json.loads(a.metadata.read_text())
 res=judge(None,source,cand,expert,a.junit,metadata)
 res["checksums"]={name:hashlib.sha256(getattr(a,name).read_bytes()).hexdigest() for name in ("candidate","expert","junit")}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
 print("DOC_HTML_NATIVE_VERDICT",json.dumps({"native":res["native"],"comparison":res["comparison"],
   "candidate":[x["status"] for x in res["arms"]["candidate"]["rows"]],
   "expert":[x["status"] for x in res["arms"]["expert_rule"]["rows"]]},sort_keys=True))
