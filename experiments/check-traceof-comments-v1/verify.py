#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys,difflib
root=pathlib.Path(sys.argv[1]).resolve()
candidate=pathlib.Path(sys.argv[2]).resolve()
out=pathlib.Path(sys.argv[3]).resolve()
out.mkdir(parents=True,exist_ok=True)
records=[]
def run(label,args,expected=0):
    p=subprocess.run(args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(label+".log")).write_text(p.stdout)
    records.append({"label":label,"exit":p.returncode,"args":args})
    (out/"commands.json").write_text(json.dumps(records,indent=2))
    print(label,p.returncode,flush=True)
    if expected is not None and p.returncode!=expected: raise RuntimeError(label+": "+p.stdout[-5000:])
    return p
assert run("source",["git","rev-parse","HEAD"]).stdout.strip()=="1153d648425fb15f6fe49061544f7ffe4bdcb520"
gen=root/"Scripts/TraceOf/Gen.lean"
surface=root/"L4YAML/Surface/Node.lean"
original_gen=gen.read_text(); original_surface=surface.read_text()
fixed=candidate.read_text()
(out/"candidate.patch").write_text("".join(difflib.unified_diff(original_gen.splitlines(True),fixed.splitlines(True),fromfile="a/Scripts/TraceOf/Gen.lean",tofile="b/Scripts/TraceOf/Gen.lean")))
# Freeze twenty independently constructed valid block-comment strings.
cases=[]
for depth in range(1,6):
    for body in ["note","line\ntext","-- is comment text","λ unicode"]:
        comment="/- "+body+" "
        for _ in range(depth-1): comment="/- outer "+comment+" -/ "
        comment+="-/"
        cases.append(("SCNsProperties n "+comment+" c","SCNsProperties n  c"))
probe=root/"CommentRegressionProbe.lean"
fixture='import Scripts.TraceOf.Gen\nopen Scripts.TraceOf.Gen\n'
for text,expected in cases:
    fixture+="#guard stripComments "+json.dumps(text,ensure_ascii=False)+" == "+json.dumps(expected,ensure_ascii=False)+"\n"
probe.write_text(fixture)
(out/"frozen-probes.lean").write_text(fixture)
mutated=original_surface.replace("SCNsProperties n c","SCNsProperties n /- outer /- inner -/ outer -/ c",1)
assert mutated!=original_surface
try:
    run("original-pure-build",["lake","build","Scripts.TraceOf.Gen"])
    p=run("original-probes",["lake","env","lean",str(probe)],None)
    assert p.returncode!=0 and "did not evaluate to" in p.stdout
    run("original-golden-check",["lake","run","gen-traceof","--","--check"])
    gold=run("original-generate",["lake","run","gen-traceof"]).stdout
    (out/"golden.lean").write_text(gold)
    surface.write_text(mutated)
    run("valid-commented-source-build",["lake","build","L4YAML.Surface.Node"])
    bad=run("original-commented-generate",["lake","run","gen-traceof"],None)
    assert bad.returncode!=0 or bad.stdout!=gold
    (out/"original-commented.lean").write_text(bad.stdout)
    gen.write_text(fixed)
    run("candidate-pure-build",["lake","build","Scripts.TraceOf.Gen"])
    run("candidate-probes",["lake","env","lean",str(probe)])
    good=run("candidate-commented-generate",["lake","run","gen-traceof"])
    (out/"candidate-commented.lean").write_text(good.stdout)
    assert good.stdout==gold,"Candidate did not restore exact generated module"
    surface.write_text(original_surface)
    run("candidate-golden-check",["lake","run","gen-traceof","--","--check"])
    run("candidate-full-build",["lake","build"])
    run("candidate-all-tests",["lake","run","run-all-tests"])
    gen.write_text(original_gen)
    run("withdrawn-pure-build",["lake","build","Scripts.TraceOf.Gen"])
    withdrawn=run("withdrawn-probes",["lake","env","lean",str(probe)],None)
    assert withdrawn.returncode!=0 and "did not evaluate to" in withdrawn.stdout
    surface.write_text(mutated)
    again=run("withdrawn-commented-generate",["lake","run","gen-traceof"],None)
    assert again.returncode==bad.returncode and again.stdout==bad.stdout
    result={"status":"WARRANTED_BOUNDED","head":"1153d648425fb15f6fe49061544f7ffe4bdcb520","probe_count":len(cases),"original":"FAIL","candidate":"PASS","withdrawn":"FAIL","native_source_with_comment_compiles":True,"candidate_generation_matches_original_golden":True,"candidate_sha256":hashlib.sha256(fixed.encode()).hexdigest(),"scope":"Nested block comments in grammar premise spans, depths 1 through 5; full frozen repository build/tests. Other lexical constructs and arbitrary PRs remain unqualified."}
    (out/"result.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
finally:
    gen.write_text(original_gen);surface.write_text(original_surface);probe.unlink(missing_ok=True)
