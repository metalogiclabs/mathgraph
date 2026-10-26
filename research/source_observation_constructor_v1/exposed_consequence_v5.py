#!/usr/bin/env python3
"""F1 V5 controlled consequence: EXPOSED Markdown2 only; no protected target access.

A frozen fault in a disposable copy must change one author-native test judgment.
A default pytest observer and an equal-information native-rulebook are compared.
The original source stays pinned, clean and unmodified. This is a deliberate
synthetic fault on authentic code, not an observed upstream defect or G2 invention.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

BASE=Path(__file__).resolve().parent
SOURCE_SHA="a3716b5e0aeba16b6e85965b2e5019d174328f36"
MODULE_BLOB="a55f7098ab952d547e7942ddc6b8626eaf15fcfc"
DRIVER_BLOB="a33a338f215c79c76d4dd00695505892152dab50"
DOC_BLOB="8c510658a76c28bffa8d0f4a9304319fb58266ab"
DRIVER=["python","test.py","--","-knownfailure"]
TARGET="markdown2/tm/emphasis"
OLD="        if self._iab_processor.test(text):\n"
NEW="        if False and self._iab_processor.test(text):  # F1_V5_CONTROLLED_FAULT\n"
CASE=re.compile(r"^\s*((?:markdown2|cli)/.*?)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)\s*$")
INTERRUPTED=re.compile(r"^\s*((?:markdown2|cli)/.*?)\s+\.\.\.\s+(WARNING:test:skipping .*)$")
WARN=re.compile(r"^WARNING:test:skipping (?:pygments|wavedrom|latex2mathml|emoji) tests .*")
SUMMARY=re.compile(r"\bRan\s+(\d+)\s+tests?\s+in\s+")

def module(file,name):
    spec=importlib.util.spec_from_file_location(name,BASE/file)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

def sha(raw): return hashlib.sha256(raw).hexdigest()

def git(root,*argv):
    p=subprocess.run(["git","-C",str(root),*argv],capture_output=True,text=True,timeout=15)
    if p.returncode: raise RuntimeError("ORIGINAL_GIT_QUERY_FAILED")
    return p.stdout.strip()

def preflight(root):
    identity=module("source_identity_guard_v3.py","f1_v5_source_identity")
    constructor=module("construct.py","f1_v5_frozen_constructor")
    assert git(root,"rev-parse","HEAD")==SOURCE_SHA
    identity.verify_source(root,SOURCE_SHA)
    for name,blob in [("lib/markdown2.py",MODULE_BLOB),
                      ("test/test.py",DRIVER_BLOB),("test/README.md",DOC_BLOB)]:
        assert git(root,"rev-parse","HEAD:"+name)==blob
        assert git(root,"hash-object","--",name)==blob
    proposed=constructor.propose(root)
    chosen=proposed.get("selected")
    assert chosen is not None and chosen.get("kind")=="AUTHOR_DRIVER"
    assert chosen.get("argv")==DRIVER and chosen.get("cwd")=="test"
    identity.verify_driver(root,SOURCE_SHA,chosen)
    assert any(e["path"]=="test/README.md" for e in chosen["supports"])
    return proposed

def parse_original(raw):
    events=[]; pending=None; warnings=0; invalid=0
    for line in raw.decode("utf8","replace").splitlines():
        line=line.rstrip()
        if pending is not None:
            if WARN.fullmatch(line): warnings+=1; continue
            if line.strip()=="ok":
                events.append((pending,"ok")); pending=None; continue
            invalid+=1; pending=None
        m=CASE.fullmatch(line)
        if m: events.append((m.group(1),m.group(2)));continue
        m=INTERRUPTED.fullmatch(line)
        if m:
            if WARN.fullmatch(m.group(2)):
                pending=m.group(1);warnings+=1
            else: invalid+=1
            continue
        if WARN.fullmatch(line): warnings+=1;continue
        if " ... " in line and (line.startswith("markdown2/") or line.startswith("cli/")):
            invalid+=1
    counts=SUMMARY.findall(raw.decode("utf8","replace"))
    declared=int(counts[0]) if len(counts)==1 else None
    names=[a for a,_ in events]
    complete=(declared is not None and len(events)==declared and
              len(set(names))==declared and pending is None and not invalid)
    return {"status":"EXACT_NATIVE_CASE_IDS" if complete else "UNKNOWN_INCOMPLETE_NATIVE_IDENTITIES",
            "declared":declared,"observed":len(events),"unique":len(set(names)),
            "warnings":warnings,"invalid":invalid,
            "cases":dict(events)}

def run(cmd,cwd,env,path,native):
    started=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,timeout=180)
        rc=p.returncode; data=p.stdout
    except subprocess.TimeoutExpired as e:
        rc=124;data=e.stdout or b""
    path.write_bytes(data)
    return {"exit":rc,"seconds":round(time.monotonic()-started,3),
            "log_sha256":sha(data),"log_file":path.name,
            "identity":parse_original(data) if native else None,
            "generic_no_tests":"no tests ran" in data.decode("utf8","replace")}

def conduct(root,out):
    root=root.resolve(strict=True)
    out.mkdir(parents=True,exist_ok=True)
    preflight(root)
    original_bytes=(root/"lib/markdown2.py").read_bytes()
    assert original_bytes.count(OLD.encode())==1
    with tempfile.TemporaryDirectory(prefix="f1_v5_exposed_") as td:
        td=Path(td)
        original=td/"unchanged"
        mutant=td/"fault"
        for target in (original,mutant):
            shutil.copytree(root,target,
                            ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc"),
                            symlinks=True)
        assert (original/"lib/markdown2.py").read_bytes()==original_bytes
        altered=original_bytes.replace(OLD.encode(),NEW.encode())
        (mutant/"lib/markdown2.py").write_bytes(altered)
        assert (mutant/"lib/markdown2.py").read_bytes()==altered
        env={k:v for k,v in os.environ.items()
             if not any(x in k.upper() for x in ("TOKEN","SECRET","PASSWORD","PRIVATE_KEY","CREDENTIAL","PYTHONPATH"))}
        env.update(PYTHONNOUSERSITE="1",PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
        native=[sys.executable,"test.py","--","-knownfailure"]
        original_obs=run(native,original/"test",env,out/"original.log",True)
        # Match the original author runner's source-library discovery for
        # BOTH clean and mutated conventional arms. The first generically
        # failed collection only because its import root was not configured.
        generic_cmd=[sys.executable,"-m","pytest","-q","-p","no:cacheprovider"]
        generic_clean_env=dict(env,PYTHONPATH=str(original/"lib"))
        generic_clean=run(generic_cmd,original,generic_clean_env,out/"generic_original.log",False)
        generic_mutant_env=dict(env,PYTHONPATH=str(mutant/"lib"))
        generic_obs=run(generic_cmd,mutant,generic_mutant_env,out/"generic.log",False)
        new_obs=run(native,mutant/"test",env,out/"candidate.log",True)
        reference_obs=run(native,mutant/"test",env,out/"informed.log",True)
    source_clean=((root/"lib/markdown2.py").read_bytes()==original_bytes
                  and not git(root,"status","--porcelain=v1","--untracked-files=all"))
    a,b,c=original_obs["identity"],new_obs["identity"],reference_obs["identity"]
    all_identities=all(z["status"]=="EXACT_NATIVE_CASE_IDS" for z in (a,b,c))
    target_different=(a["cases"].get(TARGET)=="ok" and b["cases"].get(TARGET) in ("FAIL","ERROR"))
    same_cases=all_identities and set(a["cases"])==set(b["cases"])==set(c["cases"])
    informed_tie=all_identities and b["cases"]==c["cases"]
    recognized=(all_identities and target_different and same_cases and informed_tie
                and original_obs["exit"]==0 and new_obs["exit"]!=0
                and reference_obs["exit"]!=0 and source_clean)
    generic_text=(out/"generic.log").read_text(encoding="utf8",errors="replace")
    if "ModuleNotFoundError" in generic_text or "ImportError while importing" in generic_text:
        generic_evidence_status="UNKNOWN_COLLECTION_ENVIRONMENT"
    elif generic_obs["exit"] in (0,1) and " passed" in generic_text or generic_obs["exit"] in (0,1) and " failed" in generic_text:
        generic_evidence_status="EXECUTED_GENERIC_PYTEST_CASES"
    elif generic_obs["exit"]==5 and "no tests ran" in generic_text:
        generic_evidence_status="UNKNOWN_NO_GENERIC_CASES"
    else:
        generic_evidence_status="UNKNOWN_GENERIC_RECEIPT"
    clean_generic_text=(out/"generic_original.log").read_text(encoding="utf8",errors="replace")
    generic_pair_qualified=(generic_clean["exit"]==0 and generic_obs["exit"]==1
                            and " passed" in clean_generic_text
                            and " failed" in generic_text)
    result={
        "status":"WARRANTED_BOUNDED_INDUCED_FAULT_CONSEQUENCE" if recognized else "UNKNOWN_CONSEQUENTIAL_OBSERVATION",
        "generic_evidence_status":generic_evidence_status,
        "generic_decision_separation":("TIE_ON_CLEAN_VS_FAULT_DECISION"
                                        if generic_pair_qualified and recognized
                                        else "UNKNOWN_CONVENTIONAL_CLEAN_FAULT_DECISION"),
        "generic_import_root":"source/lib (original native test bootstrap equivalent)",
        "source":"trentm/python-markdown2","pinned_source":SOURCE_SHA,
        "source_module_blob":MODULE_BLOB,"target_original_case":TARGET,
        "author_documented_command":DRIVER,
        "controlled_mutation":{"old":OLD.strip(),"new":NEW.strip(),
                               "pristine_sha256":sha(original_bytes),
                               "mutated_sha256":sha(altered),
                               "mutation_is_real_bug":False},
        "original":original_obs,"generic_original":generic_clean,
        "fixed_generic":generic_obs,
        "candidate":new_obs,"same_information_rulebook":reference_obs,
        "checks":{"original_passes_target":a["cases"].get(TARGET)=="ok",
                  "mutant_fails_protected_target":target_different,
                  "all_native_case_IDs_authenticated":bool(same_cases),
                  "equal_information_comparator_tie":bool(informed_tie),
                  "original_source_unmodified":source_clean,
                  "conventional_clean_passes_and_fault_fails":bool(generic_pair_qualified),
                  "generic_zero_collection":generic_obs["exit"]==5 and generic_obs["generic_no_tests"]},
        "not_warranted":["authentic upstream defect","full author-test coverage",
                          "human baseline superiority","general-purpose intervention safety",
                          "autonomously invented observation constructor","held-out source transfer"],
        "heldout_source_access":"NONE"
    }
    (out/"result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"native_cases":b["declared"],
                      "protected_before":a["cases"].get(TARGET),
                      "protected_after":b["cases"].get(TARGET),
                      "baseline_tie":bool(informed_tie),
                      "generic_zero_collection":result["checks"]["generic_zero_collection"]},sort_keys=True))
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    conduct(args.source,args.out)
