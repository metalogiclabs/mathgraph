"""Real-source conservative evidence reuse test, source-unchanged boundary.

Uses compose-go native Go suite, a *local* documentation-only revision,
and a source-file change. Competes with simple source-hash caching.
Not a novel semantic-reuse algorithm.
"""
import hashlib,json,os,pathlib,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(os.environ.get("EVIDENCE_CONTINUITY_OUT","compose-continuity.json"))
REPO="https://github.com/compose-spec/compose-go.git"
def cmd(args,cwd,timeout=600):
 t=time.perf_counter()
 p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if p.returncode: raise RuntimeError(str(args)+" failed: "+p.stdout[-2500:])
 return time.perf_counter()-t,p.stdout.strip()
def source_digest(path):
 # This is an intentionally conservative Go-file hash baseline. The test
 # does NOT claim full dependency/environment closure or semantic fidelity.
 h=hashlib.sha256()
 for p in sorted(path.rglob("*.go")):
  rel=p.relative_to(path)
  if ".git" in rel.parts or "vendor" in rel.parts: continue
  h.update(str(rel).encode());h.update(b"\\0");h.update(p.read_bytes())
 return h.hexdigest()
def main():
 with tempfile.TemporaryDirectory(prefix="mg-compose-") as tmp:
  path=pathlib.Path(tmp)/"compose"
  clone_s,_=cmd(["git","clone","--quiet",REPO,str(path)],tmp)
  _,pin=cmd(["git","rev-parse","HEAD"],path)
  _,go_version=cmd(["go","version"],path)
  # Warm dependency cache, then run full native suite twice for baseline.
  warm,_=cmd(["go","test","-count=1","./..."],path,timeout=600)
  full,_=cmd(["go","test","-count=1","./..."],path,timeout=600)
  t=time.perf_counter();base_hash=source_digest(path);hash_cost=time.perf_counter()-t
  (path/"MATHGRAPH_CONTINUITY_PROBE.md").write_text("Documentation-only change; no Go source changed.\\n")
  t=time.perf_counter();docs_hash=source_digest(path);docs_cost=time.perf_counter()-t
  if base_hash!=docs_hash:raise AssertionError("documentation-only unexpectedly invalidated source")
  # A Go file modification must fail closed; do not infer behavioral effect.
  target=next(p for p in sorted(path.rglob("*.go")) if ".git" not in p.parts)
  target.write_bytes(target.read_bytes()+b"\\n// evidence continuity conservative invalidation probe\\n")
  t=time.perf_counter();changed_hash=source_digest(path);change_cost=time.perf_counter()-t
  if changed_hash==base_hash:raise AssertionError("Go change not detected")
  OUT.write_text(json.dumps({
   "schema":"mathgraph.source-unchanged-cost.v1","repo":"compose-spec/compose-go",
   "commit":pin,"go_version":go_version,"full_suite_seconds":round(full,5),
   "warmup_seconds":round(warm,5),"source_hash_seconds":round(hash_cost,5),
   "docs_recheck_seconds":round(docs_cost,5),"source_change_recheck_seconds":round(change_cost,5),
   "docs_only_preserve":True,"go_changed_invalidate":True,
   "naive_full_rerun_vs_docs_hash_ratio":round(full/docs_cost,2),
   "comparison_to_conventional_source_hash_cache":"TIE by construction",
   "limitations":["manual source-only change control on real source",
                  "Go hash excludes dependency versions, tools, test environment, CI config",
                  "not verified whole-environment closure; cannot grant merge authority",
                  "semantic impact unknown for changed Go file",
                  "no improvement over conventional source hash cache",
                  "time excludes checkout/dependency warmup, included separately",
                  "document-only preservation is conditional on environment and dependency identity"],
  },indent=2,sort_keys=True)+"\\n")
  print(OUT.read_text())
if __name__=="__main__":main()
