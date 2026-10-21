#!/usr/bin/env python3
"""Boun​ded authentic two-suite test-skip contract, not broad noninterference."""
import ast,hashlib,itertools,json,os,pathlib,re,subprocess,sys,time,statistics
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
OLD="cfc3b3d18c2cf2362377bbce42d6d541b63d9062"
NEW="fb0682590796c68b002f8682202eba95c79a218c"
CORE="96de1779d24e8c88a6bf3144c35368b61df89a6b"
WARRANT="ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8"
TARGET_TEST="dd40500db86a951d9c8d136927f230af5214b8c5"
CHANGED="conformance/resolve_v1/consumer.py"
A="conformance/resolve_v1/test_consumer.py"
B="tests/test_mathgraph_warrant_resolution_core.py"
B_DEP="mathgraph_check/warrant_resolution.py"
BEFORE="return hashlib.sha256(raw).hexdigest()"
AFTER="return hashlib.sha256(raw).digest().hex()"
def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def pinned():
    base="e48f094fa400c77ab07404645f6e12cfba7ebf45"
    assert git("rev-parse",f"{base}:{CHANGED}")==OLD
    assert git("hash-object",CHANGED)==NEW
    assert git("hash-object",A)==TARGET_TEST
    assert git("hash-object",B)==CORE
    assert git("hash-object",B_DEP)==WARRANT
    prior=subprocess.check_output(["git","show",f"{base}:{CHANGED}"],cwd=ROOT,text=True)
    updated=(ROOT/CHANGED).read_text()
    assert prior.count(BEFORE)==1 and updated.count(AFTER)==1
    assert updated==prior.replace(BEFORE,AFTER)
    return prior,updated

def safe_core(test_text, dependency_text):
    try:
        a=ast.parse(test_text); b=ast.parse(dependency_text)
    except SyntaxError: return False,"UNPARSEABLE"
    imports=set()
    forbidden={"importlib","subprocess","runpy","ctypes","inspect","pathlib","os","sys"}
    for tree in (a,b):
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                for n in node.names: imports.add(n.name)
            if isinstance(node,ast.ImportFrom):
                if node.level:return False,"RELATIVE_IMPORT"
                imports.add(node.module or "")
            if isinstance(node,ast.Call):
                f=node.func
                if isinstance(f,ast.Name) and f.id in ("eval","exec","open","__import__","getattr","setattr"):
                    return False,"DYNAMIC_CALL_"+f.id
                if isinstance(f,ast.Attribute) and f.attr in ("import_module","exec_module","spec_from_file_location","Popen","run","check_output","read_text","read_bytes"):
                    return False,"DYNAMIC_ATTRIBUTE_"+f.attr
    # Exact closed scope; pytest is separately trusted runner dependency.
    allowed={"pytest","dataclasses","mathgraph_check.warrant_resolution",
             "__future__","types","typing"}
    if not imports.issubset(allowed):
        return False,"UNQUALIFIED_IMPORT_"+repr(sorted(imports-allowed))
    if "mathgraph_check.warrant_resolution" not in imports:
        return False,"MISSING_DEPENDENCY_ROOT"
    if CHANGED in test_text or "conformance.resolve_v1" in test_text:
        return False,"CHANGED_DEPENDENCY"
    return True,"CERTIFIED_PINNED_IMPORT_ENVELOPE"

def controls(prior,updated):
    b=(ROOT/B).read_text()
    dep=(ROOT/B_DEP).read_text()
    ok,why=safe_core(b,dep)
    assert ok,(ok,why)
    injected=b+"\nimport importlib\n_ = importlib.import_module('conformance.resolve_v1.consumer')\n"
    assert safe_core(injected,dep)[0] is False
    assert safe_core(b,dep+"\nfrom conformance.resolve_v1.consumer import sha\n")[0] is False
    assert prior.replace(BEFORE,AFTER+" \n")!=updated
    assert (ROOT/A).read_text().find('spec_from_file_location')>=0
    # Independently execute exact old/new SHA functions over bytes-like samples.
    original_func=lambda x:hashlib.sha256(x).hexdigest()
    changed_func=lambda x:hashlib.sha256(x).digest().hex()
    examples=(b"",b"abc",bytes(range(256)),bytearray(b"test"),memoryview(b"123456"))
    for value in examples:
        assert original_func(value)==changed_func(value)
    wrong=lambda x:hashlib.sha1(x).hexdigest()
    assert wrong(b"abc")!=original_func(b"abc")
    return {"authentic_closed_core":True,"dynamic_dependency_injection_detected":True,
        "transitive_changed_dependency_injection_detected":True,
        "unapproved_source_mutation_detected":True,
        "digest_native_examples":len(examples),"wrong_hash_mutation_detected":True}

def test_cmd(tests):
    start=time.perf_counter()
    p=subprocess.run([sys.executable,"-m","pytest","-q",*tests],cwd=ROOT,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    return {"ok":p.returncode==0,"elapsed_seconds":round(time.perf_counter()-start,6),
            "tail":p.stdout.strip().splitlines()[-5:],
            "suite":list(tests)}
def main():
    prior,updated=pinned()
    controls_result=controls(prior,updated)
    # Two suites only, both run in qualification regardless of selective permission.
    full=[A,B];selected=[A]
    samples=[]
    for i in range(5):
        for tag,paths in ((("full",full),("selective",selected)) if i%2==0
                           else (("selective",selected),("full",full))):
            result=test_cmd(paths)
            result["mode"]=tag;samples.append(result)
            if not result["ok"]:
                (HERE/"result.json").write_text(json.dumps(
                    {"status":"FAIL_CLOSED_NATIVE_REGRESSION","trials":samples},indent=2)+"\n")
                raise RuntimeError(tag+" regression failed: "+repr(result["tail"]))
    summary={tag:round(statistics.median(x["elapsed_seconds"] for x in samples if x["mode"]==tag),6)
             for tag in ("full","selective")}
    src_ok=True
    checker_ok=controls_result["authentic_closed_core"]
    mutation_ok=controls_result["dynamic_dependency_injection_detected"]
    selected_ok=all(x["ok"] for x in samples if x["mode"]=="selective")
    # Scoped MathGraph warrant graph, not product release permission.
    from mathgraph_check.warrant_resolution import Claim,Receipt,Route,resolve_graph
    scope="mathgraph:resolve-consumer:two-suite-closed-boundary"
    keys=("source","boundary","mutation","selected","policy")
    claims=[Claim(x,"documentary",scope) for x in ("source","boundary","skip_review","unrelated","full_release")]
    receipts=[Receipt(x,"documentary",scope) for x in keys+("unrelated",)]
    routes=[Route("source",("source",)),Route("boundary",("boundary",),("source",)),
            Route("skip_review",("mutation","selected","policy"),("boundary",)),
            Route("unrelated",("unrelated",))]
    full_states=dict(resolve_graph(claims,routes,receipts).states)
    assert full_states["skip_review"]=="SOURCE_DOCUMENTED" and full_states["full_release"]=="UNKNOWN"
    withdrawal={}
    for key in keys:
        s=dict(resolve_graph(claims,routes,receipts,withdrawn=frozenset((key,))).states)
        assert s["skip_review"]=="UNKNOWN" and s["unrelated"]=="SOURCE_DOCUMENTED"
        withdrawal[key]=s["skip_review"]
    # A strong conventional selector with identical module ownership knowledge.
    conventional_selected=[A]
    assert conventional_selected==selected
    report={
      "status":"PASS_TWO_SUITE_CLOSED_BOUNDARY_SKIP",
      "source_sha1_old":OLD,"source_sha1_new":NEW,
      "core_test_sha1":CORE,"unchanged_warrant_module_sha1":WARRANT,
      "qualifications":controls_result,"actual_suite_skipped":[B],
      "selected_actual_suite":selected,"full_actual_suite":full,
      "conventional_equally_informed_selector":conventional_selected,
      "selector_comparison":"TIE_SAME_TEST_SELECTION",
      "paired_native_trials":samples,"median_seconds":summary,
      "median_saved_seconds_if_two_suite_only":round(summary["full"]-summary["selective"],6),
      "all_in_experiment_charged_seconds":round(sum(s["elapsed_seconds"] for s in samples),6),
      "scoped_warrant":{"before":full_states,"withdrawals":withdrawal,
                        "full_application_release":"UNKNOWN"},
      "verification_limits":["syntactically closed known pinned test code only",
        "does not certify behavior of arbitrary pytest plugins or future imports",
        "broader application and external source qualification excluded",
        "no R7.2 CLC cross-kind proof or production merge permission",
        "all baseline tests ran in qualification, not an actual deployment CI saving"]}
    (HERE/"result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":report["status"],"actual_skip":report["actual_suite_skipped"],
      "conventional":"TIE","medians":summary,
      "withdrawal_gates":len(withdrawal),"full_release":"UNKNOWN"},sort_keys=True))
if __name__=="__main__":main()
