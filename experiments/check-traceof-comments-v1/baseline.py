#!/usr/bin/env python3
import hashlib, json, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
rows=[]
def run(label, args, must=0):
    p=subprocess.run(args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(label+".log")).write_text(p.stdout)
    rows.append({"label":label,"args":args,"exit":p.returncode,"sha256":hashlib.sha256(p.stdout.encode()).hexdigest()})
    (out/"commands.json").write_text(json.dumps(rows,indent=2))
    print(label,p.returncode,flush=True)
    if must is not None and p.returncode != must: raise RuntimeError(label+" failed: "+p.stdout[-3000:])
    return p
assert run("source",["git","rev-parse","HEAD"]).stdout.strip()=="1153d648425fb15f6fe49061544f7ffe4bdcb520"
run("pure-build",["lake","build","Scripts.TraceOf.Gen"])
probe=root/"NestedCommentProbe.lean"
probe.write_text('import Scripts.TraceOf.Gen\nopen Scripts.TraceOf.Gen\n#eval stripComments "SCNsProperties n /- outer /- inner -/ outer -/ c"\n#guard stripComments "SCNsProperties n /- outer /- inner -/ outer -/ c" == "SCNsProperties n  c"\n')
p=run("pure-nested-comment",["lake","env","lean",str(probe)],None)
assert p.returncode != 0 and "did not evaluate to" in p.stdout, "Expected a native guard failure"
run("golden-check",["lake","run","gen-traceof","--","--check"])
gold=run("golden-generation",["lake","run","gen-traceof"]).stdout
(out/"golden.lean").write_text(gold)
surface=root/"L4YAML/Surface/Node.lean"
original=surface.read_text()
needle="SCNsProperties n c"
assert needle in original
mutated=original.replace(needle,"SCNsProperties n /- outer /- inner -/ outer -/ c",1)
surface.write_text(mutated)
(out/"comment-only-source.patch").write_text("".join(__import__("difflib").unified_diff(original.splitlines(True),mutated.splitlines(True),fromfile="original",tofile="comment-only")))
try:
    run("commented-source-build",["lake","build","L4YAML.Surface.Node"])
    generated=run("commented-generation",["lake","run","gen-traceof"],None)
    (out/"commented.lean").write_text(generated.stdout)
    assert generated.returncode != 0 or generated.stdout != gold, "Hypothesis refuted: unchanged output"
    (out/"result.json").write_text(json.dumps({"status":"COUNTEREXAMPLE_BOUNDED","head":"1153d648425fb15f6fe49061544f7ffe4bdcb520","source_build_exit":0,"original_guard_exit":p.returncode,"generation_exit":generated.returncode,"generation_changed":generated.stdout!=gold,"scope":"Nested block comment inserted into one native grammar premise; source compilation and generator output comparison."},indent=2))
finally:
    surface.write_text(original)
    probe.unlink(missing_ok=True)
