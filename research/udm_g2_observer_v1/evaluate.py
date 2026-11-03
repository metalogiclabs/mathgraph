"""Independent read-only-code verifier for model-supplied Go test observations.

No API credentials may be passed to this process. The model proposal is
untrusted; Go-source admission is only a finite lexical/AST filter, not a sandbox.
Use a separate, restricted CI runner with no token-bearing environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import os
import re
import subprocess
import tempfile
import time
from typing import Any

ROOT=Path(__file__).resolve().parent
SHA=re.compile(r"[0-9a-f]{40}\Z")
TEST_NAME="TestMathGraphProposedWitness"
TEST_FILE="mathgraph_generated_observer_test.go"


def run(argv:list[str],cwd:Path,timeout:int=130)->dict[str,Any]:
    started=time.monotonic()
    try:
        p=subprocess.run(argv,cwd=cwd,text=True,capture_output=True,timeout=timeout,
            env={**{k:v for k,v in os.environ.items() if k in {"PATH","HOME","GOPATH","GOCACHE","GOPROXY","GOSUMDB","TMPDIR","LANG","CI"}}, "GOTOOLCHAIN":"local"})
        return {"exit":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"seconds":round(time.monotonic()-started,3)}
    except subprocess.TimeoutExpired:
        return {"exit":124,"stdout":"","stderr":"UNKNOWN_TIMEOUT","seconds":round(time.monotonic()-started,3)}
    except OSError as exc:
        return {"exit":125,"stdout":"","stderr":f"UNKNOWN_EXEC:{type(exc).__name__}","seconds":round(time.monotonic()-started,3)}


def test_summary(raw:str,exit_code:int)->dict[str,Any]:
    events=[]
    for line in raw.splitlines():
        try:e=json.loads(line)
        except ValueError:return {"status":"UNKNOWN_TEST_EVENTS_NOT_JSON","count":0}
        if not isinstance(e,dict):return {"status":"UNKNOWN_TEST_EVENTS_NOT_OBJECT","count":0}
        events.append(e)
    relevant=[e for e in events if e.get("Test")==TEST_NAME]
    if any("panic:" in str(e.get("Output","")) or "fatal error:" in str(e.get("Output","")) for e in relevant):
        return {"status":"UNKNOWN_TEST_PANIC_NOT_ASSERTION","count":0}
    started=sum(e.get("Action")=="run" for e in relevant)
    passed=sum(e.get("Action")=="pass" for e in relevant)
    failed=sum(e.get("Action")=="fail" for e in relevant)
    if exit_code==124:return {"status":"UNKNOWN_TIMEOUT","count":started}
    if started==0:return {"status":"UNKNOWN_ZERO_NAMED_TESTS","count":0}
    if started!=1:return {"status":"UNKNOWN_WRONG_TEST_COUNT","count":started}
    if exit_code==0 and passed==1 and failed==0:
        return {"status":"PASS_SOURCE_NATIVE","count":started}
    if exit_code!=0 and passed==0 and failed==1:
        return {"status":"FAIL_NATIVE_ASSERTION","count":started}
    return {"status":"UNKNOWN_GO_TEST_OUTCOME","count":started,"exit":exit_code}


def correct_source(root:Path,sha:str)->bool:
    if not SHA.fullmatch(sha):return False
    p=run(["git","rev-parse","HEAD"],root,timeout=20)
    return p["exit"]==0 and p["stdout"].strip()==sha


def evaluate_model(mode:str,proposal_path:Path,base:Path,head:Path,identity:dict,out:Path,package:str="zerolog")->dict[str,Any]:
    out.mkdir(parents=True,exist_ok=True)
    item:dict[str,Any]={"mode":mode,"status":"UNKNOWN_NOT_RUN","strict_g2":"UNKNOWN",
       "strict_g3":"UNKNOWN","permission":"ADVISORY_ONLY"}
    if not proposal_path.exists():item["status"]="UNKNOWN_MISSING_PROPOSAL";return item
    try: proposal=json.loads(proposal_path.read_text())
    except ValueError:item["status"]="UNKNOWN_INVALID_PROPOSAL";return item
    code=proposal.get("code")
    if not isinstance(code,str) or not code.strip() or len(code.encode())>12000:
        item["status"]="UNKNOWN_NO_ADMISSIBLE_CODE";return item
    item["proposal_sha256"]=hashlib.sha256(code.encode()).hexdigest()
    item["observation_kind"]=str(proposal.get("observation_kind", ""))[:300]
    with tempfile.TemporaryDirectory(prefix="mg-g2-eval-") as td:
        c=Path(td)/"candidate.go"
        c.write_text(code)
        validation=run(["go","run",str(ROOT/"validate.go"),"--",package,str(c)],ROOT,timeout=45)
        (out/"static-validation.txt").write_text(validation["stdout"]+validation["stderr"])
        if validation["exit"]:
            item["status"]="UNKNOWN_STATIC_VERIFIER_EXECUTION";return item
        try: report=json.loads(validation["stdout"])
        except ValueError:item["status"]="UNKNOWN_STATIC_VERIFIER_RESPONSE";return item
        item["static_admission"]=report
        if report.get("status")!="ADMITTED_TEST_ONLY_CANDIDATE":
            item["status"]="UNKNOWN_REJECTED_TEST_STATIC_ADMISSION";return item
        if not correct_source(base,identity["base"]) or not correct_source(head,identity["head"]):
            item["status"]="UNKNOWN_SUBJECT_SHA_MISMATCH";return item
        for root in (base,head):
            if (root/TEST_FILE).exists():
                item["status"]="UNKNOWN_OBSERVER_TEST_PATH_COLLISION";return item
        def invoke(root:Path,name:str,include:bool=True)->dict[str,Any]:
            target=root/TEST_FILE
            try:
                if include:target.write_text(code)
                else:target.unlink(missing_ok=True)
                result=run(["go","test","-json","-count=1","-run","^"+TEST_NAME+"$","."],root,timeout=180)
                (out/(name+"-events.jsonl")).write_text(result["stdout"])
                (out/(name+"-stderr.txt")).write_text(result["stderr"])
                summary=test_summary(result["stdout"],result["exit"])
                summary["seconds"]=result["seconds"]
                summary["exit"]=result["exit"]
                return summary
            finally:
                target.unlink(missing_ok=True)
        baseResult=invoke(base,"base-embedded")
        item["base"]=baseResult
        if baseResult["status"]!="FAIL_NATIVE_ASSERTION":
            item["status"]="UNKNOWN_NO_NEW_BASE_NATIVE_WITNESS";return item
        headResult=invoke(head,"head-embedded")
        item["head"]=headResult
        if headResult["status"]!="PASS_SOURCE_NATIVE":
            item["status"]="UNKNOWN_NO_HEAD_NATIVE_PASS";return item
        ablation=invoke(base,"base-withdrawn",include=False)
        item["ablation"]=ablation
        if ablation["status"]!="UNKNOWN_ZERO_NAMED_TESTS":
            item["status"]="UNKNOWN_NO_PHYSICAL_OBSERVER_WITHDRAWAL";return item
        restoration=invoke(base,"base-restored")
        item["restoration"]=restoration
        if restoration["status"]!="FAIL_NATIVE_ASSERTION":
            item["status"]="UNKNOWN_NO_RESTORED_WITNESS";return item
        if not correct_source(base,identity["base"]) or not correct_source(head,identity["head"]):
            item["status"]="UNKNOWN_POST_SOURCE_IDENTITY";return item
        item["status"]="WARRANTED_BOUNDED_GENERATED_NATIVE_WITNESS"
        item["strict_g2"]="UNKNOWN_NOT_META_LANGUAGE_INVENTION"
        item["total_native_seconds"]=sum(item.get(k,{}).get('seconds',0) for k in ('base','head','ablation','restoration'))
        return item


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--package',default='zerolog')
    ap.add_argument('--source',required=True)
    ap.add_argument('--base',required=True)
    ap.add_argument('--head',required=True)
    ap.add_argument('--proposals',required=True)
    ap.add_argument('--output',required=True)
    ns=ap.parse_args()
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,59}',ns.package):
        raise SystemExit('UNKNOWN_INVALID_PACKAGE_NAME')
    root=Path(ns.source).resolve()
    out=Path(ns.output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    summary={"schema":"mathgraph.g2.go-native-qualification.v1","status":"UNKNOWN",
             "base_sha":ns.base,"head_sha":ns.head,
             "strict_g2":"UNKNOWN","strict_g3":"UNKNOWN","results":[]}
    if not SHA.fullmatch(ns.base) or not SHA.fullmatch(ns.head):
        summary['status']='UNKNOWN_BAD_SOURCE_PINS'
    else:
      with tempfile.TemporaryDirectory(prefix='mg-g2-dual-') as td:
        work=Path(td)
        base=work/'base';head=work/'head'
        ready=True
        for where,sha in [(base,ns.base),(head,ns.head)]:
            t=run(['git','worktree','add','--detach',str(where),sha],root,timeout=60)
            if t['exit']!=0:ready=False
        if not ready:
            summary['status']='UNKNOWN_GIT_WORKTREE_SETUP'
        else:
            for mode in ('bridge','direct'):
                try:
                    res=evaluate_model(mode,Path(ns.proposals)/(mode+'.json'),base,head,
                                     {'base':ns.base,'head':ns.head},out/mode,package=ns.package)
                except Exception as exc:
                    res={'mode':mode,'status':'UNKNOWN_NATIVE_EVALUATOR_EXCEPTION','kind':type(exc).__name__}
                summary['results'].append(res)
                print('NATIVE_PROPOSAL',mode,res['status'],flush=True)
            qualified=[x['mode'] for x in summary['results'] if x['status']=='WARRANTED_BOUNDED_GENERATED_NATIVE_WITNESS']
            summary['status']='WARRANTED_BOUNDED_ONE_OR_MORE_NEW_WITNESS' if qualified else 'UNKNOWN_NO_VERIFIED_GENERATED_WITNESS'
            summary['fair_comparison']='SEMANTIC_TIE' if len(qualified)==2 else ('BRIDGE_ONLY_NATIVE_SUCCESS' if qualified==['bridge'] else ('DIRECT_ONLY_NATIVE_SUCCESS' if qualified==['direct'] else 'NO_SUCCESS'))
    (out/'evaluation.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print('SCIENTIFIC_G2',summary['strict_g2'],'G3',summary['strict_g3'])
    return 0

if __name__=='__main__':raise SystemExit(main())
