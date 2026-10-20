#!/usr/bin/env python3
"""Held-out runner. Source only accessed after selection lock is committed."""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys,urllib.request
from collections import Counter
ROOT=pathlib.Path.cwd()
D=ROOT/"research/heldout_lean_boundary_v1"
EV=D/"evidence"
EV.mkdir(parents=True,exist_ok=True)
def run(cmd,cwd=ROOT,timeout=900,env=None):
    z=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     timeout=timeout,env=env)
    return z.returncode,z.stdout
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,text):(EV/name).write_text(text)
def fail(reason):
    save("VERDICT.json",json.dumps({"status":"UNKNOWN","reason":reason},indent=2)+"\n")
    raise SystemExit("UNKNOWN_"+reason)
lock=json.loads((D/"selection.lock.json").read_text())
assert lock["schema"]=="heldout.selection.metadata.v1"
assert lock["selected"]["repository"]==lock["pool"][0],"NO_OUTCOME_BASED_SUBSTITUTION"
assert lock["selection_rule"]=="FIRST_ELIGIBLE_NO_FALLTHROUGH"
repo=lock["selected"]["repository"]; pinned=lock["selected"]["selected_sha"]
method_commit=lock["method_commit"]
# Enforce F0 file identity under both commits, before source opening.
for name in ("PROTOCOL.md","selection.py","candidate.py","baseline.py","synthetic_tests.py","assay.py"):
    rc,prior=run(["git","show",method_commit+":"+str((D/name).relative_to(ROOT))])
    if rc!=0 or hashlib.sha256(prior.encode()).hexdigest()!=sha(D/name):
        fail("METHOD_CHANGED_AFTER_SELECTION_"+name)
rc,out=run(["python3",str(D/"synthetic_tests.py")])
save("synthetic_controls.txt",out)
if rc:fail("SYNTHETIC_CONTROLS")
save("source_metadata_lock.json",json.dumps(lock,indent=2,sort_keys=True)+"\n")
source=EV/"source_checkout"
rc,out=run(["git","clone","--quiet","--no-checkout","--filter=blob:none",
            "https://github.com/"+repo+".git",str(source)],timeout=180)
save("git_clone.txt",out)
if rc:fail("GIT_CLONE")
rc,out=run(["git","checkout","--quiet","--detach",pinned],cwd=source,timeout=180)
save("git_checkout.txt",out)
if rc:fail("GIT_CHECKOUT")
rc,head=run(["git","rev-parse","HEAD"],cwd=source)
if rc or head.strip()!=pinned:fail("SOURCE_PIN_MISMATCH")
import candidate,baseline
pr={"candidate":candidate.propose(source),"baseline":baseline.propose(source)}
if any(p["arm"]!=arm for arm in pr for p in pr[arm]):fail("ARM_IMPERSONATION")
for arm in pr:
    if len(pr[arm])>4:fail("BUDGET_EXCEEDED")
    for p in pr[arm]:
        file=source/p["file"]
        if sha(file)!=p["source_sha256"]:fail("CLAIM_SOURCE_IDENTITY_MISMATCH")
save("SEALED_PROPOSALS.json",json.dumps(pr,sort_keys=True,indent=2)+"\n")
save("SEALED_PROPOSALS_SHA256.txt",sha(EV/"SEALED_PROPOSALS.json")+"\n")
print("PROPOSALS_SEALED_BEFORE_NATIVE_BUILD",sha(EV/"SEALED_PROPOSALS.json"),{k:len(v) for k,v in pr.items()},flush=True)
# Source-native verifying toolchain: respect package declared lean-toolchain, no source edits.
env=os.environ.copy()
env["PATH"]=str(pathlib.Path.home()/".elan"/"bin")+os.pathsep+env["PATH"]
rc,out=run(["lake","--version"],cwd=source,timeout=180,env=env)
save("lake_version.txt",out)
if rc:fail("NO_NATIVE_LEAN_TOOLCHAIN")
# If project uses mathlib cache, source-neutral prebuild; failure is recorded and build still attempted.
if any("mathlib" in p.read_text(encoding="utf-8",errors="ignore").lower()
       for p in [source/"lakefile.lean",source/"lakefile.toml"] if p.exists()):
    cr,co=run(["lake","exe","cache","get"],cwd=source,timeout=420,env=env)
    save("mathlib_cache_result.txt","exit="+str(cr)+"\n"+co[-20000:])
rc,out=run(["lake","build"],cwd=source,timeout=2100,env=env)
save("native_build.txt","exit="+str(rc)+"\n"+out[-180000:])
save("native_exit.txt",str(rc)+"\n")
print("NATIVE_BUILD_EXIT",rc,flush=True)
if rc:fail("NATIVE_BUILD_FAILED")
# Evaluate exactly the sealed proposals; no mutation / reselection after observing outcomes.
result={"candidate":[],"baseline":[]}
for arm,items in pr.items():
    for idx,p in enumerate(items):
        q=EV/("probe_"+arm+"_"+str(idx)+".lean")
        q.write_text("import "+p["module"]+"\n#check "+p["name"]+"\n#print axioms "+p["name"]+"\n")
        rc,out=run(["lake","env","lean",str(q)],cwd=source,timeout=150,env=env)
        log=EV/("probe_"+arm+"_"+str(idx)+".txt")
        log.write_text("exit="+str(rc)+"\n"+out)
        lookedup=(p["name"]+" :" in out or p["name"]+"." in out)
        axioms=(re.search(r"depends on axioms:\s*\[([^\]]*)\]",out) or
                re.search(r"does not depend on any axioms",out))
        valid=(rc==0 and bool(lookedup) and bool(axioms)
               and "sorryAx" not in out and "error:" not in out)
        result[arm].append({"name":p["name"],"file":p["file"],
                            "verifier_exit":rc,"scope_warranted":valid,
                            "axioms":axioms.group(0) if axioms else None,
                            "log_sha256":sha(log)})
save("NATIVE_PROBE_RESULTS.json",json.dumps(result,sort_keys=True,indent=2)+"\n")
# Bounded source/receipt graph only; no source→external-semantic lift.
sys.path.insert(0,str(ROOT))
from mathgraph_check.warrant_resolution import Claim,Receipt,Route,resolve_graph
scope="third_source_documentary:"+repo+"@"+pinned
claims=[Claim("source.metadata_frozen","documentary",scope),
        Claim("native.lean_build","documentary",scope),
        Claim("external.semantic_equivalence","documentary",scope),
        Claim("control.unrelated","documentary",scope)]
receipts=[Receipt("metadata","documentary",scope),Receipt("native","documentary",scope),
          Receipt("unrelated","documentary",scope)]
routes=[Route("source.metadata_frozen",("metadata",)),Route("native.lean_build",("native",)),
        Route("control.unrelated",("unrelated",))]
for arm,records in result.items():
    for i,z in enumerate(records):
        if z["scope_warranted"]:
            name=arm+"."+str(i)+".qualified_formal_observation"
            claims.append(Claim(name,"documentary",scope))
            receipts.append(Receipt(arm+"."+str(i)+".proof","documentary",scope))
            routes.append(Route(name,("native",arm+"."+str(i)+".proof"),("source.metadata_frozen",)))
original=dict(resolve_graph(claims,routes,receipts).states)
if original["external.semantic_equivalence"]!="UNKNOWN":fail("INVENTED_SEMANTIC_AUTHORITY")
physical={}
# Withhold real file copies, not just resolver state toggles; restore exact bytes.
for receipt,path in [("metadata",EV/"source_metadata_lock.json"),("native",EV/"native_build.txt")]:
    origin=sha(path);moved=path.with_suffix(path.suffix+".withheld")
    path.rename(moved)
    if path.exists():fail("FAILED_PHYSICAL_WITHDRAWAL")
    after=dict(resolve_graph(claims,routes,receipts,withdrawn=frozenset((receipt,))).states)
    lost=sorted(k for k in original if original[k]!="UNKNOWN" and after[k]=="UNKNOWN")
    expected=sorted(["source.metadata_frozen"]+
                    [c.id for c in claims if c.id.endswith("qualified_formal_observation")]) if receipt=="metadata" else sorted(["native.lean_build"]+[c.id for c in claims if c.id.endswith("qualified_formal_observation")])
    if lost!=expected:fail("SELECTIVE_WITHDRAWAL_"+receipt)
    moved.rename(path)
    if sha(path)!=origin or dict(resolve_graph(claims,routes,receipts).states)!=original:
        fail("RESTORATION_"+receipt)
    physical[receipt]={"lost_only":lost,"bytes_restored":True}
scores={k:sum(z["scope_warranted"] for z in v) for k,v in result.items()}
if scores["candidate"]+scores["baseline"]==0:
    verdict="UNKNOWN_NO_ADMITTED_THIRD_SOURCE_THEOREM"
elif scores["candidate"]==scores["baseline"]:
    verdict="WARRANTED_BOUNDED_SOURCE_FORMAL_TIE"
elif scores["candidate"]>scores["baseline"]:
    verdict="WARRANTED_BOUNDED_PROXY_ADVANTAGE_NOT_HUMAN"
else:
    verdict="WARRANTED_BOUNDED_PROXY_BASELINE_BETTER"
final={"schema":"heldout.lean.observer.v1","source_repo":repo,"source_sha":pinned,
       "frozen_method_commit":method_commit,"proposals_sha256":sha(EV/"SEALED_PROPOSALS.json"),
       "native_build_exit":0,"results":result,"scores":scores,"verdict":verdict,
       "external_semantic_correspondence":"UNKNOWN_NO_INDEPENDENT_EXTERNAL_REQUIREMENT",
       "physical_withdrawals":physical,
       "limitations":["Prototype source-neutral lexical observer, not a formal source-language parser",
                      "Comparator independently authored expert-rule proxy, not a human expert",
                      "Source file proposition is a formal theorem statement, not independently authored real-world intent",
                      "The source-authored-to-Len theorem name linkage is exact but not an external semantic bridge",
                      "Local physically moved snapshots are not upstream authority revocation",
                      "Method run is a new source snapshot, not autonomous method invention"]}
save("RESULT.json",json.dumps(final,sort_keys=True,indent=2)+"\n")
print("FINAL_RESULT",json.dumps({"verdict":verdict,"scores":scores,"withdrawals":physical},sort_keys=True),flush=True)
