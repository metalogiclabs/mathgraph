#!/usr/bin/env python3
"""Authenticated native author-test-entrypoint experiment on the exact selected source.

Never equate two counts with subset coverage absent test-ID equivalence.
Candidate and expert-rule comparator get identical source documentation.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,re,subprocess,sys,time

def load(path):
    spec=importlib.util.spec_from_file_location("source_author_v8",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def sha(x):
    return hashlib.sha256(x).hexdigest()

def run(argv,cwd,timeout=240):
    start=time.monotonic()
    try:
        r=subprocess.run(argv,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         timeout=timeout,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
        return {"argv":argv,"cwd":str(cwd),"exit":r.returncode,"elapsed_seconds":round(time.monotonic()-start,3),
                "output":r.stdout}
    except subprocess.TimeoutExpired as ex:
        out=ex.stdout or b""
        if isinstance(out,bytes):out=out.decode("utf8","replace")
        return {"argv":argv,"cwd":str(cwd),"exit":None,"elapsed_seconds":round(time.monotonic()-start,3),
                "timeout":True,"output":out}

def count_native(output):
    unittest_counts=[int(m) for m in re.findall(r"Ran (\d+) tests? in [\d.]+s",output)]
    if unittest_counts:return max(unittest_counts),"original-author-unittest-harness"
    # Test summary should come from the terminal pytest summary and have a real count.
    found=re.findall(r"(?:(\d+) passed|(?:(\d+) tests? passed))",output)
    if found:return max(int(a or b) for a,b in found),"pytest-stdout"
    return 0,"NO_VERIFIABLE_CASE_COUNT"

def main():
    p=argparse.ArgumentParser()
    for name in ("source","selection","proposal","observer","out"):
        p.add_argument("--"+name,type=pathlib.Path,required=True)
    a=p.parse_args()
    source=a.source.resolve()
    meta=json.loads(a.selection.read_text())
    view=json.loads(a.proposal.read_text())
    assert meta["selected"]["repository"]==view["source"]["repository"]
    assert meta["selected"]["source_sha"]==view["source"]["source_sha"]
    obs=load(a.observer)
    candidate=view["candidate"];expert=view["expert"]
    original_census=obs.collect(source)
    assert candidate==original_census,"PRENATIVE_SOURCE_DOC_AUTHORITY_DRIFT"
    # Native comparison arm: generic pytest executes same original source unchanged.
    default=run([sys.executable,"-m","pytest","-q",str(source)],source,timeout=240)
    default["case_count"],default["counter_source"]=count_native(default["output"])
    selected=candidate.get("selected")
    author=None
    withdrawn=None
    if candidate["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER" and selected:
        command=selected["command"]
        cwd=(source/command["cwd"]).resolve()
        assert cwd.is_relative_to(source) and cwd.is_dir(),"CWD_ESCAPE"
        argv=[sys.executable if command["argv"][0] in ("python","python3") else command["argv"][0],*command["argv"][1:]]
        author=run(argv,cwd,timeout=240)
        author["case_count"],author["counter_source"]=count_native(author["output"])
        # Independently recheck that source author really contained cited documentation.
        doc=source/selected["source_doc"]
        original=doc.read_bytes()
        assert sha(original)==selected["doc_sha256"]
        lines=original.decode("utf8").splitlines(keepends=True)
        idx=selected["line"]-1
        assert lines[idx].strip()==selected["exact_line"]
        # Physically withdraw just this authored instruction in the ephemeral checkout.
        saved=lines[idx]
        lines[idx]="# V8 experimental doc authority withdrawn, original script untouched\n"
        doc.write_text("".join(lines))
        after=obs.collect(source)
        doc.write_bytes(original)
        assert sha(doc.read_bytes())==selected["doc_sha256"]
        restored=obs.collect(source)
        assert restored==candidate
        withdrawn={
            "authority_file":selected["source_doc"],"original_doc_sha256":selected["doc_sha256"],
            "experimental_line_removed":selected["line"],"after_status":after["status"],
            "remaining_independent_author_command_evidence":after["selected"] is not None,
            "exact_byte_restoration":True,
            "original_source_was_not_repaired":True,
        }
    def qualification(result):
        if result is None:return "UNKNOWN_NO_AUTHOR_DECLARED_RUNNER"
        if result["exit"] is None:return "UNKNOWN_NATIVE_TIMEOUT"
        if result["case_count"]==0:return "UNKNOWN_NO_VERIFIABLE_CASE_COUNT"
        if result["exit"]!=0:return "REJECTED_NATIVE_EXIT_NONZERO"
        return "WARRANTED_BOUNDED_EXECUTED_NATIVE_TEST_SCOPE"
    native_status=qualification(author)
    generic_status=qualification(default)
    equal_info=(expert["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER" and
                candidate["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER" and
                expert["selected"]["command"]==candidate["selected"]["command"])
    comparison="INCONCLUSIVE_NO_AUTHOR_RUNNER"
    if equal_info and native_status.startswith("WARRANTED"):
        comparison="EXPERT_RULE_SAME_COMMAND_TIE"
    elif candidate["status"]=="CANDIDATE_AUTHOR_DECLARED_RUNNER":
        comparison="INCONCLUSIVE_DIFFERENT_OR_UNSUPPORTED_EXPERT_SELECTION"
    delta=(author["case_count"]-default["case_count"]) if author else None
    receipt={
        "protocol":"SOURCE_AUTHOR_TEST_RUNNER_SCOPE_V8",
        "source":view["source"],
        "doc_evidence":candidate.get("evidence",[]),
        "original_doc_proposal_status":candidate["status"],
        "author_native_scope":{k:v for k,v in author.items() if k!="output"} if author else None,
        "generic_pytest_scope":{k:v for k,v in default.items() if k!="output"},
        "author_native_verdict":native_status,"generic_pytest_verdict":generic_status,
        "author_vs_generic_case_count_delta":delta,
        "NOT_a_test_superset_claim":"No test ID intersection or authoritative complete-suite equivalence established",
        "experimentally_withdrawn_authority":withdrawn,
        "expert_rule":expert,"equal_information_comparison":comparison,
        "proposal_sha256":sha(a.proposal.read_bytes()),"selected_revision":meta["selected"]["source_sha"],
        "generalization":"No automatic new observation grammar; finite Python-only author test command search",
    }
    out=a.out
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    (out.parent/"generic-native-stdout.log").write_text(default["output"])
    if author:(out.parent/"author-native-stdout.log").write_text(author["output"])
    print("V8_AUTHOR_NATIVE_VERIFIER_RESULT",json.dumps({
        "source":view["source"]["repository"],"candidate":candidate["status"],
        "author":native_status,"author_case_count":author["case_count"] if author else 0,
        "generic":generic_status,"generic_case_count":default["case_count"],
        "comparison":comparison,"withdrawn":withdrawn},sort_keys=True))

if __name__=="__main__":main()
