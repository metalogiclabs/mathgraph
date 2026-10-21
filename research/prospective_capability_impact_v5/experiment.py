#!/usr/bin/env python3
"""V5: frozen source-family transfer; actual code change, honest closed-boundary controls."""
import ast, hashlib, json, statistics, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name("result.json")
BASE="e48f094fa400c77ab07404645f6e12cfba7ebf45"
TARGET="conformance/capability_v1/consumer.py"
OWNER_TEST="conformance/capability_v1/test_contract.py"
INDEPENDENT_TEST="tests/test_mathgraph_warrant_resolution_core.py"
CORE_DEP="mathgraph_check/warrant_resolution.py"
ORIG_BLOB="cbddfad2b01f1c5514b7af240bc05119b0a5a372"
NEW_BLOB="03a185f47b16dc6d4eea2af566d9689b3c7c7a11"
OWNER_BLOB="88ea546e7c7f0bfbb11a9b4e1bbb2e8c67ffb645"
INDEPENDENT_BLOB="96de1779d24e8c88a6bf3144c35368b61df89a6b"
CORE_BLOB="ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8"
FROM="hashlib.sha256(raw).hexdigest()"
TO="hashlib.sha256(raw).digest().hex()"
def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def pin_code():
    assert git("rev-parse",f"{BASE}:{TARGET}")==ORIG_BLOB
    assert git("hash-object",TARGET)==NEW_BLOB
    assert git("hash-object",OWNER_TEST)==OWNER_BLOB
    assert git("hash-object",INDEPENDENT_TEST)==INDEPENDENT_BLOB
    assert git("hash-object",CORE_DEP)==CORE_BLOB
    original=subprocess.check_output(["git","show",f"{BASE}:{TARGET}"],cwd=ROOT,text=True)
    updated=(ROOT/TARGET).read_text()
    assert original.count(FROM)>=1
    assert original.replace(FROM,TO,1)==updated, "UNAUTHORIZED_SOURCE_CHANGE"
    return original,updated

def closed_imports(source,dep):
    try:
        trees=[ast.parse(source),ast.parse(dep)]
    except SyntaxError:return False,"UNPARSEABLE"
    imported=set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node,ast.ImportFrom):
                if node.level:return False,"RELATIVE_IMPORT"
                imported.add(node.module or "")
            elif isinstance(node,ast.Call):
                f=node.func
                if isinstance(f,ast.Name) and f.id in ("eval","exec","open","__import__","getattr","setattr"):
                    return False,"DYNAMIC_CALL_"+f.id
                if isinstance(f,ast.Attribute) and f.attr in (
                   "import_module","spec_from_file_location","exec_module",
                   "Popen","run","check_output","read_text","read_bytes"):
                    return False,"DYNAMIC_ATTRIBUTE_"+f.attr
    allowed={"__future__","pytest","dataclasses","types","typing",
             "mathgraph_check.warrant_resolution"}
    unapproved=imported-allowed
    if unapproved:return False,"UNKNOWN_IMPORTS:"+",".join(sorted(unapproved))
    if "mathgraph_check.warrant_resolution" not in imported:
        return False,"UNATTESTED_REFERENCE_ROOT"
    if "conformance.capability_v1" in source or TARGET in source:
        return False,"CHANGED_COMPONENT_MENTION"
    return True,"FROZEN_CLOSED_IMPORTS"

def qualification(original,updated):
    test=(ROOT/INDEPENDENT_TEST).read_text()
    dep=(ROOT/CORE_DEP).read_text()
    safe,reason=closed_imports(test,dep)
    assert safe,reason
    # Controls authored before running native changed source regression.
    injected=test+"\nimport importlib\n_ = importlib.import_module('conformance.capability_v1.consumer')\n"
    assert not closed_imports(injected,dep)[0], "DYNAMIC_IMPORT_NEGATIVE_MISSED"
    shadow=dep+"\nfrom conformance.capability_v1.consumer import sha\n"
    assert not closed_imports(test,shadow)[0], "TRANSITIVE_DEPENDENCY_NEGATIVE_MISSED"
    assert updated!=original.replace(FROM,"hashlib.sha1(raw).hexdigest()",1)
    vectors=[b"",b"x",b"test",bytes(range(256)),bytearray(b"words")]
    for v in vectors:
        assert hashlib.sha256(v).hexdigest()==hashlib.sha256(v).digest().hex()
    assert hashlib.sha1(b"test").hexdigest()!=hashlib.sha256(b"test").hexdigest()
    owner=(ROOT/OWNER_TEST).read_text()
    assert "consumer.py" in owner or "capability_v1" in owner
    return {"real_independent_suite_closed":safe,"cause":reason,
      "dynamic_import_counterexample":"REVOKES",
      "helper_dependency_counterexample":"REVOKES",
      "unauthorized_source_mutation":"REJECTS",
      "bad_hash_mutation":"DETECTED",
      "native_digest_equivalence_examples":len(vectors)}

def test_process(paths):
    t=time.perf_counter()
    process=subprocess.run([sys.executable,"-m","pytest","-q",*paths],
       cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return {"ok":process.returncode==0,"elapsed":round(time.perf_counter()-t,6),
            "tail":process.stdout.strip().splitlines()[-12:],
            "suite":paths}
def real_warrant():
    sys.path.insert(0,str(ROOT))
    from mathgraph_check.warrant_resolution import Claim,Receipt,Route,resolve_graph
    scope="mathgraph/capability_v1:closed-two-suite-impact:v5"
    ids=("source_pin","test_pin","closed_imports","negative_controls","selected_suite","policy")
    claims=[Claim(i,"documentary",scope) for i in ("source","closed","skip_review","independent","full_release")]
    receipts=[Receipt(i,"documentary",scope) for i in ids+("independent",)]
    routes=[Route("source",("source_pin","test_pin")),Route("closed",("closed_imports",),("source",)),
            Route("skip_review",("negative_controls","selected_suite","policy"),("closed",)),
            Route("independent",("independent",))]
    full=dict(resolve_graph(claims,routes,receipts).states)
    assert full["skip_review"]=="SOURCE_DOCUMENTED" and full["full_release"]=="UNKNOWN"
    for name in ids:
        state=dict(resolve_graph(claims,routes,receipts,withdrawn=frozenset({name})).states)
        assert state["skip_review"]=="UNKNOWN"
        assert state["independent"]=="SOURCE_DOCUMENTED"
    return {"scoped_skip":full["skip_review"],"full_release":full["full_release"],
            "selective_withdrawals":len(ids)}

def main():
    old,new=pin_code()
    qualified=qualification(old,new)
    full=[OWNER_TEST,INDEPENDENT_TEST]
    selective=[OWNER_TEST]
    trials=[]
    for i in range(5):
        for label,files in ((("full",full),("selective",selective)) if i%2==0
                            else (("selective",selective),("full",full))):
            result=test_process(files)
            result["mode"]=label;trials.append(result)
            if not result["ok"]:
                OUT.write_text(json.dumps({"status":"FAIL_CLOSED_NATIVE","trials":trials,
                                            "qualification":qualified},indent=2)+"\n")
                raise RuntimeError("Native "+label+" failed "+repr(result["tail"]))
    median={key:round(statistics.median(x["elapsed"] for x in trials if x["mode"]==key),6)
            for key in ("full","selective")}
    warrant=real_warrant()
    data={"status":"WARRANTED_SCOPED_SOURCE_DISTINCT_CLOSED_IMPACT",
          "source_old_blob":ORIG_BLOB,"source_new_blob":NEW_BLOB,
          "real_suite_omitted":[INDEPENDENT_TEST],"retained_suite":[OWNER_TEST],
          "qualification":qualified,"real_mathgraph_warrant":warrant,
          "matched_full_information_conventional_selector":[OWNER_TEST],
          "comparison":"TIE_EQUAL_INFORMATION_MODULE_SELECTOR",
          "trials":trials,"medians_seconds":median,
          "hypothetical_test_process_saving_seconds":round(median["full"]-median["selective"],6),
          "whole_experiment_test_seconds":round(sum(x["elapsed"] for x in trials),6),
          "full_application_release":"UNKNOWN",
          "limitations":["not previously unanticipated source semantics: preselected source family and rewrite shape",
                         "closed impact conclusion relies on pinned Python AST and runtime assumptions",
                         "not global Python noninterference theorem",
                         "all baseline/full tests run in experiment; no realized cost saving",
                         "no stronger than equal-information conventional dependency-aware selection"]}
    OUT.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":data["status"],"test_omitted":INDEPENDENT_TEST,
      "median":median,"conventional":"TIE","warrant":warrant},sort_keys=True))
if __name__=="__main__":main()
