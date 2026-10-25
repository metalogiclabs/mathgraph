#!/usr/bin/env python3
"""Complete source-blind V6.1 schema replay tests, not simply dict unit tests."""
import argparse,importlib.util,json,pathlib,subprocess,sys,tempfile

def readmodule(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def run(*args):
    p=subprocess.run([sys.executable,*map(str,args)],text=True,capture_output=True)
    if p.returncode:
        raise AssertionError("SUBPROCESS_FAILED: "+" ".join(map(str,args))+"\n"+p.stdout+"\n"+p.stderr)
    return p.stdout

def main():
    pa=argparse.ArgumentParser()
    for name in ("frozen_v6","frozen_v4"):
        pa.add_argument("--"+name.replace("_","-"),type=pathlib.Path,required=True)
    a=pa.parse_args()
    prop=readmodule(a.frozen_v6/"propose.py","frozen_v6_prop")
    resolver=readmodule(a.frozen_v4/"resolve.py","frozen_v4_resolver")
    binder=pathlib.Path(__file__).with_name("v6_1_bind.py")
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); src=root/"source";src.mkdir()
        package=src/"demo";package.mkdir()
        original="""__all__ = ['Demo']
class Demo:
    def lower(self, text):
        \"\"\"Lower the text.

        >>> Demo().lower('ABC')
        'abc'
        \"\"\"
        return text.lower()
"""
        package.joinpath("__init__.py").write_text(original)
        meta=root/"metadata.json"
        meta.write_text(json.dumps({"repository":"synthetic/demo","source_sha":"a"*40}))
        junit=root/"native.xml";junit.write_text('<testsuite tests="3" failures="0" errors="0" skipped="0"/>')
        def episode(name):
            proposer=prop.scan(src,resolver)
            proposal=root/(name+"-proposal.json")
            proposal.write_text(json.dumps(proposer,sort_keys=True)+"\n")
            output=root/(name+"-result.json");bound=root/(name+"-bound.json")
            run(binder,"--metadata",meta,"--proposals",proposal,"--source",src,
                "--native-junit",junit,"--evaluator",a.frozen_v6/"evaluate.py",
                "--out",output,"--bound-proposals",bound)
            return proposer,json.loads(output.read_text())
        baseline,good=episode("positive")
        assert baseline["status"]=="SOURCE_DOC_EXAMPLE_CANDIDATES"
        assert len(baseline["obligations"])==1,baseline
        assert good["candidate_source_doc_warrants"]==1,good
        assert good["stdlib_doctest_reference_warrants"]==1,good
        assert good["comparison"]=="TIE"
        package.joinpath("__init__.py").write_text(original.replace("'abc'\n        \"\"\"","'WRONG'\n        \"\"\""))
        changed,bad=episode("counterexample")
        assert bad["source_doc_examples_rejected"]==1,bad
        package.joinpath("__init__.py").write_text(original.replace("        >>> Demo().lower('ABC')\n        'abc'\n",""))
        no_example,unknown=episode("zero")
        assert no_example["status"]=="UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE"
        assert unknown["comparison"]=="INCONCLUSIVE_ZERO_CLAIMS"
        assert unknown["status"]=="UNKNOWN_NO_APPLICABLE_DOC_EXAMPLES"
        package.joinpath("__init__.py").write_text(original)
        junit.write_text('<testsuite tests="3" failures="1" errors="0" skipped="0"/>')
        _,non_native=episode("failed-native")
        assert non_native["candidate_source_doc_warrants"]==0
        assert non_native["observations"][0]["verdict"]=="UNKNOWN_NO_NATIVE_AUTHORITY"
        assert prop.scan(src,resolver)["obligations"]==baseline["obligations"],"RESTORED_ORIGINAL_DOC_BYTES"
        tampered={"repository":"synthetic/other","source_sha":"a"*40}
        try:
            readmodule(binder,"binder_v6_1").bind(tampered,{"status":"SOURCE_DOC_EXAMPLE_CANDIDATES",
                "api":baseline["api"],"files":baseline["files"],"obligations":[],"repository":"synthetic/demo"})
        except AssertionError:
            pass
        else:
            raise AssertionError("MISMATCHED_SOURCE_BINDING_ACCEPTED")
    print("V6_1_END_TO_END_PROPOSE_BIND_NATIVE_DOCTEST_POSITIVE_NEGATIVE_UNKNOWN_AND_RESTORATION_PASS")
if __name__=="__main__":
    main()
