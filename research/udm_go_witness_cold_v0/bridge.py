"""Research-only typed cold replay of source-native Go observation witnesses.

A portable MathGraph capability.v1 descriptor is NOT a qualification.  Fresh
source-native replay is mandatory and never grants permission to act.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from mathgraph_protocol.capability_v1 import validate_contract, evaluate_contract

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
PKG = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,60}\Z")
TEST_NAME = "TestMathGraphProposedWitness"
TEST_FILE = "mathgraph_generated_observer_test.go"
EVIDENCE_STATUS = "WARRANTED_BOUNDED_GENERATED_NATIVE_WITNESS"
PREVIOUS_STATUS = "WARRANTED_BOUNDED_ONE_OR_MORE_NEW_WITNESS"
EXPECTED = {"base":("FAIL_NATIVE_ASSERTION",1), "head":("PASS_SOURCE_NATIVE",1),
            "ablation":("UNKNOWN_ZERO_NAMED_TESTS",0), "restoration":("FAIL_NATIVE_ASSERTION",1)}


def canonical(x) -> bytes:
    return (json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode()


def digest(b:bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def die(s):
    raise ValueError(s)


def need(test, reason):
    if not test: die(reason)


def parse(data:bytes):
    # Use canonical strict JSON rules, including duplicate-key and nonfinite refusal.
    from mathgraph_protocol.json_strict import strict_json_loads
    return strict_json_loads(data)


def artifact(ident:str, name:str, contents:bytes, media:str="application/json"):
    return {"id":ident,"locator":name,"sha256":digest(contents),
            "size_bytes":len(contents),"media_type":media}


def prior_warrant(e:dict, mode:str, code:bytes, pair:dict):
    need(e.get("schema")=="mathgraph.g2.go-native-qualification.v1", "UNKNOWN_EVALUATION_SCHEMA")
    need(e.get("status")==PREVIOUS_STATUS,"UNKNOWN_PRIOR_EVALUATION")
    need(e.get("base_sha")==pair["base"] and e.get("head_sha")==pair["head"],"UNKNOWN_PRIOR_SOURCE_MISMATCH")
    selected=[x for x in e.get("results",[]) if isinstance(x,dict) and x.get("mode")==mode]
    need(len(selected)==1,"UNKNOWN_PRIOR_MODE")
    x=selected[0]
    need(x.get("status")==EVIDENCE_STATUS,"UNKNOWN_PRIOR_WITNESS_STATUS")
    need(x.get("proposal_sha256")==digest(code),"UNKNOWN_PRIOR_CODE_MISMATCH")
    for field,(s,n) in EXPECTED.items():
        a=x.get(field)
        need(isinstance(a,dict) and a.get("status")==s and a.get("count")==n,"UNKNOWN_PRIOR_NATIVE_BOUNDARY_"+field)
    need(e.get("strict_g2")=="UNKNOWN" and e.get("strict_g3")=="UNKNOWN","UNKNOWN_PRIOR_OVERCLAIM")


def validate_pair(pair):
    need(isinstance(pair,dict) and set(pair)=={"repository","package","base","head","mode","origin_run"},"UNKNOWN_PAIR_FIELDS")
    need(all(isinstance(pair[k],str) for k in pair),"UNKNOWN_PAIR_FIELD_TYPE")
    need(SHA.fullmatch(pair["base"]) and SHA.fullmatch(pair["head"]) and pair["base"]!=pair["head"],"UNKNOWN_SOURCE_PINS")
    need(PKG.fullmatch(pair["package"]),"UNKNOWN_PACKAGE_NAME")
    need(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",pair["repository"]),"UNKNOWN_REPOSITORY")
    need(pair["mode"] in ("bridge","direct") and re.fullmatch(r"[0-9]{7,20}",pair["origin_run"]),"UNKNOWN_MODE_OR_RUN")


def export(proposal:bytes, evaluation:bytes, pair:dict, store:Path):
    validate_pair(pair)
    model=parse(proposal);receipt=parse(evaluation)
    need(isinstance(model,dict) and isinstance(model.get("code"),str) and model["code"].strip(),"UNKNOWN_PROPOSAL")
    code=model["code"].encode("utf-8")
    need(len(code)<12001 and code.startswith(("package "+pair["package"]).encode()),"UNKNOWN_CODE_PACKAGE_OR_SIZE")
    prior_warrant(receipt,pair["mode"],code,pair)
    files={"sources.json":canonical(pair), "candidate.go":code,
           "prior-evaluation.json":evaluation}
    src=artifact("exact_go_source_pair","sources.json",files["sources.json"])
    test=artifact("original_generated_go_test","candidate.go",code,"text/x-go")
    proof=artifact("original_native_provenance","prior-evaluation.json",evaluation)
    contract={
      "schema_version":"mathgraph.capability-contract.v1",
      "id":"go-source-native-witness:"+pair["repository"]+":"+pair["mode"],
      "version":"0.1.0", "profile":"research.go-version-separator.native-recheck.v0",
      "claim":{"id":"original-author-regression-witness", "kind":"source-version-separator",
               "scope":pair["repository"]+"@"+pair["base"]+".."+pair["head"]},
      "inputs":[{"type_id":"GoSourceCommitPair.v0","schema":src}],
      "outputs":[{"type_id":"GoNativeVersionWitness.v0","schema":test}],
      "preconditions":["Exact source commit checkout", "Fresh Go toolchain and immutable candidate test"],
      "guarantees":["Only exact scoped test result; fresh native source replay required"],
      "assumptions":["Tested package code may execute inside a credential-free isolated runner"],
      "boundary":proof,"implementation":test,"evidence":[proof],
      "limitations":["Historical original-author repair, not a discovered new upstream bug",
                     "No trusted effect permission or verified future transfer",
                     "Stored receipt alone never authorizes ACCEPT or a G2/G3 promotion"],
      "extensions":[]
    }
    validate_contract(contract)
    # Base portable capability evaluator MUST remain conservative (not admitted).
    static=evaluate_contract(contract)
    need(static.get("validation")=="VALID" and static.get("qualification")=="UNKNOWN" and static.get("action_authorization")=="NONE", "UNKNOWN_UNSAFE_STATIC_PROMOTION")
    files["contract.json"]=canonical(contract)
    root=digest(files["contract.json"])
    dest=store/"objects"/root
    if dest.exists():
        inspect(store,root)
        for name,data in files.items():
            need((dest/name).read_bytes()==data,"UNKNOWN_CONTENT_ADDRESS_COLLISION")
    else:
        dest.mkdir(parents=True, exist_ok=False)
        for name,data in files.items():(dest/name).write_bytes(data)
    return {"root_sha256":root,"status":"CANDIDATE_COLD_TRANSPORT","qualification":"UNKNOWN_FRESH_REPLAY_REQUIRED",
            "action_authorization":"NONE","scope":contract["claim"]["scope"], "object_dir":str(dest)}


def inspect(store:Path, root:str, revoked:set[str]|None=None):
    need(bool(DIGEST.fullmatch(root)),"UNKNOWN_INVALID_OBJECT_ID")
    need(root not in (revoked or set()),"UNKNOWN_REVOKED_OBJECT")
    dest=store/"objects"/root
    need(dest.is_dir() and not dest.is_symlink(),"UNKNOWN_CAPABILITY_WITHDRAWN")
    need(all((dest/n).is_file() and not (dest/n).is_symlink() for n in ("contract.json","candidate.go","sources.json","prior-evaluation.json")),"UNKNOWN_MISSING_OBJECT_FILE")
    contract_raw=(dest/"contract.json").read_bytes()
    need(digest(contract_raw)==root,"UNKNOWN_CONTRACT_HASH_MISMATCH")
    c=parse(contract_raw);validate_contract(c)
    need(c.get("profile")=="research.go-version-separator.native-recheck.v0","UNKNOWN_UNADMITTED_PROFILE")
    files={"candidate.go":(dest/"candidate.go").read_bytes(),"sources.json":(dest/"sources.json").read_bytes(),"prior-evaluation.json":(dest/"prior-evaluation.json").read_bytes()}
    pair=parse(files["sources.json"]);validate_pair(pair)
    need(c["claim"]["scope"]==pair["repository"]+"@"+pair["base"]+".."+pair["head"],"UNKNOWN_SCOPE_TAMPER")
    for a in (c["inputs"][0]["schema"],c["outputs"][0]["schema"],c["boundary"],c["implementation"],*c["evidence"]):
        name=a["locator"]
        need(name in files and digest(files[name])==a["sha256"] and len(files[name])==a["size_bytes"],"UNKNOWN_OBJECT_CONTENT_MISMATCH")
    need(c["implementation"]["sha256"]==c["outputs"][0]["schema"]["sha256"],"UNKNOWN_IMPLEMENTATION_OUTPUT_MISMATCH")
    prior_warrant(parse(files["prior-evaluation.json"]),pair["mode"],files["candidate.go"],pair)
    need(c["claim"]["kind"]=="source-version-separator", "UNKNOWN_CLAIM_KIND")
    static=evaluate_contract(c)
    need(static["validation"]=="VALID" and static["qualification"]=="UNKNOWN" and static["action_authorization"]=="NONE", "UNKNOWN_UNSAFE_STATIC_PROMOTION")
    return pair,files


def run(args:list[str],cwd:Path,timeout:int=120):
    env={k:os.environ[k] for k in ("PATH","HOME","GOPATH","GOCACHE","GOPROXY","GOSUMDB","TMPDIR","LANG","CI") if k in os.environ}
    env["GOTOOLCHAIN"]="local"
    try:
        done=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout,env=env)
        return {"exit":done.returncode,"stdout":done.stdout,"stderr":done.stderr}
    except subprocess.TimeoutExpired:return {"exit":124,"stdout":"","stderr":"UNKNOWN_TIMEOUT"}
    except OSError as ex:return {"exit":125,"stdout":"","stderr":"UNKNOWN_OS_ERROR:"+type(ex).__name__}


def test_summary(raw:str, exit:int):
    events=[]
    for line in raw.splitlines():
        try:x=json.loads(line)
        except ValueError:return {"status":"UNKNOWN_MALFORMED_GO_EVENTS","count":0}
        if not isinstance(x,dict):return {"status":"UNKNOWN_INVALID_GO_EVENT","count":0}
        events.append(x)
    items=[x for x in events if x.get("Test")==TEST_NAME]
    if any("panic:" in str(x.get("Output", "")) or "fatal error:" in str(x.get("Output","")) for x in items):
        return {"status":"UNKNOWN_PANIC_NOT_ASSERTION","count":0}
    started=sum(x.get("Action")=="run" for x in items)
    passed=sum(x.get("Action")=="pass" for x in items)
    failed=sum(x.get("Action")=="fail" for x in items)
    if exit==124:return {"status":"UNKNOWN_TIMEOUT","count":started}
    if started!=1:return {"status":"UNKNOWN_ZERO_OR_MULTIPLE_NAMED_TESTS","count":started}
    if exit==0 and passed==1 and failed==0:return {"status":"PASS_SOURCE_NATIVE","count":1}
    if exit!=0 and passed==0 and failed==1:return {"status":"FAIL_NATIVE_ASSERTION","count":1}
    return {"status":"UNKNOWN_NATIVE_TEST_OUTCOME","count":started}


def verify_identity(root:Path,sha:str):
    return run(["git","rev-parse","HEAD"],root,20)["stdout"].strip()==sha and not run(["git","status","--porcelain"],root,20)["stdout"].strip()


def cold_replay(store:Path,root:str,git_source:Path,static_validator:Path,revoked:set[str]|None=None):
    t=time.monotonic()
    result={"schema":"mathgraph.udm.go-native-cold-replay.v0","object_sha256":root,
            "status":"UNKNOWN_PRECHECK","permission":"NONE","strict_g2":"UNKNOWN","strict_g3":"UNKNOWN","arms":{}}
    try:
        pair,files=inspect(store,root,revoked)
        source=git_source.resolve()
        need(verify_identity(source,pair["base"]),"UNKNOWN_SOURCE_BASE_IDENTITY")
        need(run(["git","cat-file","-e",pair["head"]+"^{commit}"],source,20)["exit"]==0,"UNKNOWN_SOURCE_HEAD_MISSING")
        with tempfile.TemporaryDirectory(prefix="mg-udm-cold-") as tmp:
            base=Path(tmp)/"base";head=Path(tmp)/"head"
            for target,sha in ((base,pair["base"]),(head,pair["head"])):
                need(run(["git","worktree","add","--detach",str(target),sha],source,45)["exit"]==0,"UNKNOWN_WORKTREE_CONSTRUCTION")
                need(verify_identity(target,sha),"UNKNOWN_WORKTREE_IDENTITY")
            testpath=Path(tmp)/"candidate.go";testpath.write_bytes(files["candidate.go"])
            # Original finite Go validator deliberately cannot approve code's semantics.
            check=run(["go","run",str(static_validator.resolve()),"--",str(testpath),pair["package"]],source,45)
            need(check["exit"]==0,"UNKNOWN_STATIC_VERIFIER_EXECUTION")
            try: j=json.loads(check["stdout"])
            except ValueError: die("UNKNOWN_STATIC_RESPONSE")
            need(j.get("status")=="ADMITTED_TEST_ONLY_CANDIDATE","UNKNOWN_STATIC_ADMISSION:"+str(j.get("reason")))
            def arm(name,target,include):
                dest=target/TEST_FILE
                need(not dest.exists(),"UNKNOWN_TEST_FILE_COLLISION")
                if include:dest.write_bytes(files["candidate.go"])
                try:
                    raw=run(["go","test","-json","-count=1","-run","^"+TEST_NAME+"$","."],target,180)
                finally:
                    dest.unlink(missing_ok=True)
                out=test_summary(raw["stdout"],raw["exit"])
                result["arms"][name]=out
                return out
            for name,target,include in (("base",base,True),("head",head,True),("withdrawn",base,False),("restored",base,True)):
                arm(name,target,include)
            need([result["arms"][k]["status"] for k in ("base","head","withdrawn","restored")]==[
                "FAIL_NATIVE_ASSERTION","PASS_SOURCE_NATIVE","UNKNOWN_ZERO_OR_MULTIPLE_NAMED_TESTS","FAIL_NATIVE_ASSERTION"],"UNKNOWN_NATIVE_OBSERVATION_NOT_REQUALIFIED")
            need(verify_identity(base,pair["base"]) and verify_identity(head,pair["head"]),"UNKNOWN_POST_SOURCE_MUTATION")
        result["status"]="WARRANTED_BOUNDED_COLD_NATIVE_REPLAY"
        result["owner_authority"]="NOT_GRANTED"
    except Exception as ex:
        result["status"]=str(ex) if isinstance(ex,ValueError) and str(ex).startswith("UNKNOWN_") else "UNKNOWN_REPLAY_EXCEPTION"
        result["exception_kind"]=type(ex).__name__
    result["elapsed_seconds"]=round(time.monotonic()-t,3)
    return result


def main():
    cli=argparse.ArgumentParser()
    sub=cli.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("export")
    a.add_argument("--proposal",required=True);a.add_argument("--evaluation",required=True)
    a.add_argument("--pair",required=True);a.add_argument("--store",required=True)
    b=sub.add_parser("replay")
    b.add_argument("--store",required=True);b.add_argument("--root",required=True)
    b.add_argument("--source",required=True);b.add_argument("--validator",required=True)
    b.add_argument("--revoke-file")
    args=cli.parse_args()
    if args.cmd=="export":
        try:r=export(Path(args.proposal).read_bytes(),Path(args.evaluation).read_bytes(),parse(Path(args.pair).read_bytes()),Path(args.store))
        except Exception as e:r={"status":str(e) if isinstance(e,ValueError) else "UNKNOWN_EXPORT_EXCEPTION", "qualification":"UNKNOWN", "permission":"NONE"}
    else:
        denied=set()
        if args.revoke_file:denied=set(parse(Path(args.revoke_file).read_bytes()))
        r=cold_replay(Path(args.store),args.root,Path(args.source),Path(args.validator),denied)
    print(json.dumps(r,sort_keys=True))
    return 0

if __name__=="__main__":raise SystemExit(main())
