#!/usr/bin/env python3
"""Fail-closed, source-bound test impact classification. Not a general soundness proof."""
import ast, hashlib, json, pathlib, subprocess, sys, time
from collections import deque
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
OLD="ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8"
NEW="85de97a95f225ad564feb29faec24ce67f3f2e0e"
CHANGE="mathgraph_check/warrant_resolution.py"
TESTS=("tests/test_mathgraph_warrant_resolution_core.py",
 "tests/test_mathgraph_living_warrants_v1.py",
 "tests/test_mathgraph_resolve_publication_v1.py",
 "conformance/protocol_v1/test_consumer.py",
 "conformance/resolve_v1/test_consumer.py")
OPAQUE={"importlib","subprocess","eval","exec","__import__","runpy","getattr","setattr"}
def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def pin_change():
    assert git("rev-parse","e48f094fa400c77ab07404645f6e12cfba7ebf45")=="e48f094fa400c77ab07404645f6e12cfba7ebf45"
    assert git("rev-parse","e48f094fa400c77ab07404645f6e12cfba7ebf45:"+CHANGE)==OLD
    assert git("hash-object",CHANGE)==NEW
def refs(tree):
    names=[]
    opaque=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            if node.level:opaque.append("RELATIVE_IMPORT")
            if node.module:names.append(node.module)
        elif isinstance(node,ast.Call):
            f=node.func
            if isinstance(f,ast.Name) and f.id in OPAQUE:opaque.append(f.id)
            if isinstance(f,ast.Attribute):
                root=f.value
                if isinstance(root,ast.Name) and root.id in OPAQUE:opaque.append(root.id+"."+f.attr)
                # External process/effects, runtime-loaded modules and file-based consumers
                if f.attr in ("exec_module","spec_from_file_location","read_bytes","read_text","run","Popen","check_output","system"):
                    opaque.append("DYNAMIC_OR_EXTERNAL_EFFECT:"+f.attr)
    return names,sorted(set(opaque))
def local(module):
    if not module:return None
    rel=pathlib.Path(*module.split("."))
    choices=[ROOT/(str(rel)+".py"),ROOT/rel/"__init__.py"]
    for path in choices:
        if path.is_file():return path
    return None
def analyze_source(text,label,synthetic_modules=None):
    modules=synthetic_modules or {}
    q=deque([(label,text)])
    visited=set()
    unknown=[];reachable=[];observed=[]
    while q:
        name,body=q.popleft()
        if name in visited:continue
        visited.add(name)
        try: tree=ast.parse(body)
        except SyntaxError:
            unknown.append("UNPARSEABLE:"+name);continue
        imports,opaque=refs(tree)
        if opaque:unknown.extend(name+":"+x for x in opaque)
        for mod in imports:
            observed.append(mod)
            if mod=="mathgraph_check.warrant_resolution" or mod.startswith("mathgraph_check.warrant_resolution."):
                reachable.append(name+" -> "+mod)
            if mod in modules:
                q.append((mod,modules[mod]));continue
            p=local(mod)
            if p is not None and str(p) not in visited:
                q.append((str(p),p.read_text()))
            elif mod.startswith(("mathgraph_check","scripts.","conformance.")):
                unknown.append("UNRESOLVED_LOCAL:"+mod)
    status="KEEP_CHANGED_DEPENDENCY" if reachable else (
       "KEEP_UNKNOWN_DYNAMIC" if unknown else "SYNTACTICALLY_DISJOINT_ONLY")
    return {"status":status,"reachable":reachable[:18],"unknown":unknown[:18],
            "examined_modules":len(visited),"imports":len(observed)}
def conventional_heuristic(text):
    # Common quick heuristic: look for direct changed module import in test file only.
    return "KEEP" if "mathgraph_check.warrant_resolution" in text else "SKIP"
def synthetic_controls():
    independent=analyze_source("def test_pure():\n    assert (2+2)==4\n","synthetic_pure")
    dynamic=analyze_source("import importlib\nx=importlib.import_module('mathgraph_check.warrant_resolution')\n","synthetic_dynamic")
    helper=analyze_source("from localhelper import fn\nfn()\n","synthetic_helper",{
       "localhelper":"from mathgraph_check.warrant_resolution import resolve_graph\nfn=resolve_graph\n"})
    assert independent["status"]=="SYNTACTICALLY_DISJOINT_ONLY"
    assert dynamic["status"]=="KEEP_UNKNOWN_DYNAMIC"
    assert helper["status"]=="KEEP_CHANGED_DEPENDENCY"
    assert conventional_heuristic("import importlib\nx=importlib.import_module('mathgraph_check.'+'warrant_resolution')")=="SKIP"
    return {"pure_finite_no_effects":independent["status"],
       "dynamic_import_fails_closed":dynamic["status"],
       "transitive_helper_detected":helper["status"],
       "conventional_dynamic_false_skip_detected":True}
def main():
    pin_change()
    start=time.perf_counter()
    positive=synthetic_controls()
    tests=[]
    for path in TESTS:
        body=(ROOT/path).read_text()
        result=analyze_source(body,path)
        basic=conventional_heuristic(body)
        # The syntactic disjointness evidence is insufficient to issue a release waiver.
        permit_skip=False
        tests.append({"test_file":path,"source_sha256":hashlib.sha256(body.encode()).hexdigest(),
            "conservative":result,"conventional_file_heuristic":basic,
            "protected_permission_to_skip":permit_skip})
    # All genuinely owned tests must stay within the protected scope if
    # source-impact closure or external effect semantics cannot be guaranteed.
    safe_skips=[x["test_file"] for x in tests if x["protected_permission_to_skip"]]
    assert not safe_skips
    report={"status":"UNKNOWN_NO_SOURCE_AUTHORITATIVE_SAFE_SKIP",
      "changed_module":CHANGE,"old_blob_sha1":OLD,"new_blob_sha1":NEW,
      "actual_frozen_test_universe":list(TESTS),
      "analyses":tests,"negative_controls":positive,"safe_to_omit_authentic_tests":safe_skips,
      "conventional_heuristic_skips":[x["test_file"] for x in tests if x["conventional_file_heuristic"]=="SKIP"],
      "protected_full_release":"UNKNOWN_MUST_RUN_EXISTING_BROAD_GATE",
      "duration_seconds":round(time.perf_counter()-start,6),
      "interpretation":"No independent semantic/side-effect theorem supporting omission of actual test files",
      "R7_CLC_MATHGRAPH":"existing components unchanged; this script does not issue cross-kind formal adapters"}
    (HERE/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"safe_skips":safe_skips,
       "conventional_heuristic_skips":report["conventional_heuristic_skips"],
       "synthetic_controls":positive,
       "analyses":[{"file":x["test_file"],"status":x["conservative"]["status"],
                     "unknown_count":len(x["conservative"]["unknown"])} for x in tests]},sort_keys=True))
if __name__=="__main__":main()
