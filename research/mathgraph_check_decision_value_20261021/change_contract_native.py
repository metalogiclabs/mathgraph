"""Change-carrying bounded assurance with adversarial negative control.

Genuine source: yuin/goldmark-meta PR #8. Three revisions created in isolated
temporary worktree: base, submitted head, head with deliberately broken parser.
The agent-authored transport obligation is NOT proof of general equivalence.
"""
import json, os, pathlib, subprocess, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(os.environ.get("MATHGRAPH_CONTRACT_OUT","change-contract.json"))
BASE="f5d5bebad44ac55105584283ee742a9e6f3524c0"
HEAD="ad93e759a4ba37c8b548367506f50dfd5bc0ce1a"
def run(cmd,cwd,timeout=300):
 t=time.perf_counter()
 p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 return round(time.perf_counter()-t,6),p.returncode,p.stdout[-1500:]
def must(label,record):
 if record[1]:raise RuntimeError(label+": "+record[2])
def test(path,pattern):
 return run(["go","test","-count=1","-run",pattern,"./..."],path)
def main():
 with tempfile.TemporaryDirectory(prefix="mg-contract-") as td:
  path=pathlib.Path(td)/"source"
  must("clone",run(["git","clone","-q","https://github.com/yuin/goldmark-meta.git",str(path)],td))
  must("fetch head",run(["git","fetch","-q","https://github.com/noerw/goldmark-meta.git",HEAD],path))
  probe=ROOT/"research/mathgraph_check_decision_value_20261021/frontmatter_consequence_test.go.txt"
  output={}
  for label,revision in [("base",BASE),("head",HEAD)]:
   must("checkout",run(["git","checkout","-q","--detach",revision],path))
   (path/"mathgraph_consequence_test.go").write_bytes(probe.read_bytes())
   output[label]={"property":test(path,"^TestMathGraphProspective"),"full":run(["go","test","-count=1","./..."],path)}
   (path/"mathgraph_consequence_test.go").unlink()
  must("checkout bad",run(["git","checkout","-q","--detach",HEAD],path))
  source=path/"meta.go"
  before=source.read_text()
  needle="if isEndSeparator(line) && !util.IsBlank(line) {"
  if before.count(needle)!=1:raise RuntimeError("BAD_MUTATION_TARGET_MISMATCH")
  source.write_text(before.replace(needle,"if false && isEndSeparator(line) && !util.IsBlank(line) {",1))
  (path/"mathgraph_consequence_test.go").write_bytes(probe.read_bytes())
  output["bad"]={"property":test(path,"^TestMathGraphProspective"),"full":run(["go","test","-count=1","./..."],path)}
  if output["base"]["property"][1]==0:raise RuntimeError("BASE_SHOULD_NOT_SUPPORT_NEW_TERMINATOR")
  if output["head"]["property"][1]!=0 or output["head"]["full"][1]!=0:raise RuntimeError("HEAD_NOT_GREEN")
  if output["bad"]["property"][1]==0:raise RuntimeError("BAD_CHANGE_FALSE_ADMITTED")
  contract={
   "schema":"mathgraph.change-contract-native.v1",
   "base":BASE,"head":HEAD,"negative":"head with isEndSeparator disabled",
   "property":"both --- and ... terminate frontmatter; metadata and body survive",
   "states":{k:{"property_pass":v["property"][1]==0,"full_pass":v["full"][1]==0,
                 "property_seconds":v["property"][0],"full_seconds":v["full"][0]}
              for k,v in output.items()},
   "decision":"HEAD_BOUNDED_ACCEPT_BAD_REJECT",
   "limits":["This is an authored behavioral property test, not a verified universal correspondence",
     "No evidence transport for unrelated properties","No automated impact coverage",
     "Real source with controlled adversarial mutation, not independent external adoption",
     "Comparison lacks expert selective-CI baseline and long-run cost"],
  }
  OUT.write_text(json.dumps(contract,sort_keys=True,indent=2)+"\n")
  print(json.dumps(contract,sort_keys=True))
if __name__=="__main__":main()
