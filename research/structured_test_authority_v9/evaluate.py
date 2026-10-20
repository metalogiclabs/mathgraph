#!/usr/bin/env python3
"""Execute identical source-pinned native pytest for default and sealed explicit roots.

Never execute Makefile recipes. Compare exact original testcase identities, not counts.
A passing default pytest command is an execution receipt, NOT author-suite completeness.
"""
import argparse,hashlib,json,os,pathlib,re,subprocess,sys,time,xml.etree.ElementTree as ET


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ids(path):
    if not path.is_file():return None
    root=ET.parse(path).getroot()
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    tests=sum(int(s.attrib.get("tests",0)) for s in suites)
    fail=sum(int(s.attrib.get("failures",0)) for s in suites)
    err=sum(int(s.attrib.get("errors",0)) for s in suites)
    skip=sum(int(s.attrib.get("skipped",0)) for s in suites)
    cases=[(c.attrib.get("file",""),c.attrib.get("classname",""),c.attrib.get("name",""))
           for c in root.iter("testcase")]
    return {"tests":tests,"failures":fail,"errors":err,"skipped_or_xfail":skip,
            "unique_testcase_ids":len(set(cases)),"case_ids":sorted(set(cases)),
            "complete":tests==len(cases) and len(set(cases))==len(cases) and tests>skip}


def run_pytest(source,extra,stem,outdir):
    stdout_path=outdir/(stem+".log")
    junit=outdir/(stem+".xml")
    cmd=[sys.executable,"-m","pytest","-q",*extra,"--junitxml="+str(junit)]
    env={k:v for k,v in os.environ.items() if not any(w in k for w in ("TOKEN","PASSWORD","SECRET","PRIVATE_KEY"))}
    t=time.monotonic()
    try:
        proc=subprocess.run(cmd,cwd=source,text=True,stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,timeout=280,env=env)
        status=proc.returncode
        stdout_path.write_text(proc.stdout)
    except subprocess.TimeoutExpired as exc:
        status=None
        data=exc.stdout or b""
        stdout_path.write_text(data.decode("utf8","replace") if isinstance(data,bytes) else data)
    counts=test_ids(junit)
    return {"argv":cmd,"cwd":str(source),"exit_code":status,"runtime_sec":round(time.monotonic()-t,3),
            "stdout_sha256":sha(stdout_path),"junit_sha256":sha(junit) if junit.is_file() else None,
            "junit":counts}


def selected_valid(source,selection):
    if selection is None:return False
    roots=selection["testpaths"]
    return bool(roots) and all(
        (source / x).resolve().is_relative_to(source) and (source/x).is_dir()
        for x in roots)


def verdict(receipt):
    if receipt is None:return "UNKNOWN_NO_AUTHORITY"
    j=receipt["junit"]
    if receipt["exit_code"] is None:return "UNKNOWN_TIMEOUT"
    if receipt["exit_code"]!=0:return "UNKNOWN_NATIVE_EXECUTION_FAILED"
    if j is None or not j["complete"] or j["failures"] or j["errors"]:
        return "UNKNOWN_NATIVE_TEST_ID_INCOMPLETE_OR_FAILURE"
    return "WARRANTED_BOUNDED_EXECUTED_PYTEST_SCOPE"


def main():
    p=argparse.ArgumentParser()
    for name in ("source","selection","proposal","out"):
        p.add_argument("--"+name,type=pathlib.Path,required=True)
    a=p.parse_args()
    source=a.source.resolve()
    lock=json.loads(a.selection.read_text())
    proposal=json.loads(a.proposal.read_text())
    assert proposal["source"]["repository"]==lock["selected"]["repository"]
    assert proposal["source"]["source_sha"]==lock["selected"]["source_sha"]
    # Repo SHA anchored by workflow checkout before this verifier.
    expected=proposal["candidate"]["evidence_files"]
    for name,digest in expected.items():
        assert sha(source/name)==digest,"SOURCE_CONFIG_SHA_CHANGED_BEFORE_NATIVE"
    outdir=a.out.parent
    outdir.mkdir(parents=True,exist_ok=True)
    default=run_pytest(source,[],"default",outdir)
    candidate_sel=proposal["candidate"]["selected"]
    expert_sel=proposal["expert_rule"]["selected"]
    candidate=run_pytest(source,candidate_sel["testpaths"],"candidate",outdir) if selected_valid(source,candidate_sel) else None
    # Equal-information expert-run selection, independently coded; invoke same source/env.
    expert=run_pytest(source,expert_sel["testpaths"],"expert",outdir) if selected_valid(source,expert_sel) else None

    def setids(r):
        return set(tuple(v) for v in r["junit"]["case_ids"]) if r and r["junit"] else set()
    d,c,e=setids(default),setids(candidate),setids(expert)
    comparison={
        "default_testcases":len(d),"candidate_testcases":len(c),"expert_testcases":len(e),
        "candidate_minus_default":len(c-d),"default_minus_candidate":len(d-c),
        "candidate_minus_expert":len(c-e),"expert_minus_candidate":len(e-c),
        "candidate_equals_default":c==d if candidate is not None else None,
        "candidate_equals_expert":c==e if candidate is not None and expert is not None else None,
        "comparison":"INCONCLUSIVE_NO_AUTHOR_ROOTS",
        "baseline":"Original pytest automatic source config + equal-informed independently coded cookbook (not a human)",
    }
    statuses={"default":verdict(default),"candidate":verdict(candidate),"expert_rule":verdict(expert)}
    if statuses["candidate"].startswith("WARRANTED") and statuses["expert_rule"].startswith("WARRANTED"):
        comparison["comparison"]="TIE_IN_TEST_ID_SCOPE" if c==e else "DIFFERENT_SCOPES_NOT_SUPERIORITY"
    elif candidate is not None or expert is not None:
        comparison["comparison"]="INCONCLUSIVE_NATIVE_OR_SEMANTIC_AUTHORITY"
    # Provenance claims intentionally narrow, no author suite completeness inference.
    result={"protocol":"STRUCTURED_PYTEST_SCOPE_V9","source":proposal["source"],
            "root_authority":proposal["candidate"],"baseline_authority":proposal["expert_rule"],
            "status":statuses,"comparison":comparison,
            "runs":{"default":default,"candidate":candidate,"expert_rule":expert},
            "proposal_sha256":sha(a.proposal),"source_lock_sha256":sha(a.selection),
            "not_warranted":"Completeness of author native suite, superiority over competent reviewer, or arbitrary program intent"}
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("V9_NATIVE_STRUCTURED_SCOPE",json.dumps({
        "statuses":statuses,"comparison":comparison},sort_keys=True))


if __name__=="__main__":
    main()
