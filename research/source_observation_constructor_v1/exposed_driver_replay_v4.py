#!/usr/bin/env python3
"""Controlled replay of ALREADY EXPOSED Markdown2 native author test entrypoint.

This is a deliberately non-prospective reference experiment. The source,
command family, author README and comparison arm were exposed in F0.
No protected source checkout or arbitrary shell command may be passed to it.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
KNOWN_SOURCE = "a3716b5e0aeba16b6e85965b2e5019d174328f36"
KNOWN_DRIVER = "test/test.py"
KNOWN_DOC = "test/README.md"
KNOWN_ARGS = ["python", "test.py", "--", "-knownfailure"]
CASE = re.compile(r"^\s*((?:markdown2|cli)/.*?)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)\s*$")
INTERRUPTED = re.compile(r"^\s*((?:markdown2|cli)/.*?)\s+\.\.\.\s+(WARNING:test:skipping .*)$")
SKIP_WARNING = re.compile(r"^WARNING:test:skipping (?:pygments|wavedrom|latex2mathml|emoji) tests .*")
SUMMARY = re.compile(r"\bRan\s+(\d+)\s+tests?\s+in\s+")


def read_module(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(source, *args):
    r = subprocess.run(["git", "-C", str(source), *args],
                       capture_output=True, text=True, timeout=15)
    if r.returncode:
        raise RuntimeError("EXPOSED_SOURCE_GIT_QUERY_FAILED")
    return r.stdout.strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract_native_ids(log):
    """Strict source-specific parser. Never infer a missing test-case identity.

    The original author harness can interleave four named optional-dependency
    warnings within a test result. Only these known warnings may be removed.
    """
    found, interrupted, warnings, malformed = [], None, 0, []
    for line in log.splitlines():
        line = line.rstrip()
        if interrupted is not None:
            if SKIP_WARNING.fullmatch(line):
                warnings += 1
                continue
            if line.strip() == "ok":
                found.append((interrupted, "ok"))
                interrupted = None
                continue
            malformed.append(line)
            interrupted = None
        m = CASE.fullmatch(line)
        if m:
            found.append((m.group(1), m.group(2)))
            continue
        m = INTERRUPTED.fullmatch(line)
        if m:
            if not SKIP_WARNING.fullmatch(m.group(2)):
                malformed.append(line)
            else:
                interrupted = m.group(1)
                warnings += 1
            continue
        if SKIP_WARNING.fullmatch(line):
            warnings += 1
            continue
        if " ... " in line or line.strip() in ("ok", "FAIL", "ERROR"):
            malformed.append(line)
    totals = SUMMARY.findall(log)
    if len(totals) != 1:
        return {"status":"UNKNOWN_AUTHOR_NATIVE_CASE_SUMMARY",
                "candidate_rows":len(found), "warnings":warnings}
    count = int(totals[0])
    if (interrupted is not None or malformed or not found
            or len(found) != count
            or len(set(name for name, _ in found)) != count):
        return {"status":"UNKNOWN_AUTHOR_NATIVE_TEST_IDENTITIES",
                "declared":count, "observed":len(found),
                "interrupted":interrupted is not None,
                "unmatched_lines":len(malformed), "warnings":warnings}
    if any(status != "ok" for _, status in found):
        return {"status":"UNKNOWN_NATIVE_FAILURE", "declared":count}
    return {"status":"WARRANTED_BOUNDED_EXECUTED_NATIVE_IDS",
            "case_ids": sorted(name for name, _ in found),
            "count":count, "recognized_optional_dependency_warnings":warnings}


def run_native(source, out, name):
    command = [sys.executable, "test.py", "--", "-knownfailure"]
    env = {k:v for k,v in os.environ.items()
           if not any(bad in k.upper() for bad in
                      ("TOKEN", "PASSWORD", "SECRET", "PRIVATE_KEY", "CREDENTIAL"))}
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env["PYTHONNOUSERSITE"]="1"
    t = time.monotonic()
    try:
        process = subprocess.run(command, cwd=source/"test", env=env,
                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=280)
        output = process.stdout
        rc = process.returncode
    except subprocess.TimeoutExpired as e:
        output = e.stdout or b""
        rc = 124
    out.joinpath(name + ".log").write_bytes(output)
    decoded = output.decode("utf-8", "replace")
    observed = extract_native_ids(decoded)
    return {"command":KNOWN_ARGS, "exit_code":rc,
            "elapsed_seconds":round(time.monotonic()-t,3),
            "log_sha256":digest(output), "observation":observed}


def replay(source:Path, out:Path) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    source=source.resolve(strict=True)
    constructor=read_module("construct.py","candidate_constr_exposed_v4")
    identity=read_module("source_identity_guard_v3.py","identity_exposed_v4")
    if git(source, "rev-parse", "HEAD") != KNOWN_SOURCE:
        raise RuntimeError("SOURCE_REVISION_MISMATCH")
    identity.verify_source(source, KNOWN_SOURCE)
    proposal=constructor.propose(source)
    selected=proposal.get("selected")
    if (selected is None or selected.get("kind")!="AUTHOR_DRIVER"
        or selected.get("argv")!=KNOWN_ARGS or selected.get("cwd")!="test"):
        return {"status":"UNKNOWN_NO_SUPPORTED_NATIVE_AUTHOR_DRIVER",
                "source":KNOWN_SOURCE,"author_intent":"UNKNOWN"}
    receipt=identity.verify_driver(source,KNOWN_SOURCE,selected)
    assert receipt["executable"] == KNOWN_DRIVER
    support=next((s for s in selected["supports"]
                  if s["path"]==KNOWN_DOC),None)
    if support is None:
        raise RuntimeError("UNKNOWN_MISSING_SOURCE_AUTHOR_DOC")
    doc=source/KNOWN_DOC
    before=doc.read_bytes()
    if digest(before)!=support["sha256"]:
        raise RuntimeError("UNKNOWN_AUTHOR_DOC_SHA")
    text=before.decode("utf-8")
    if not ("To run the test suite" in text and
            "without" in text and
            "python test.py -- -knownfailure" in text):
        return {"status":"UNKNOWN_AUTHOR_DOC_SCOPE_NOT_ESTABLISHED"}
    # Equal-information mechanical rulebook: explicitly choose the same
    # ORIGINAL source-author documented command; not a real human trial.
    candidate=run_native(source,out,"candidate")
    baseline=run_native(source,out,"same_info_rulebook")
    if git(source,"status","--porcelain=v1","--untracked-files=all"):
        return {"status":"UNKNOWN_SOURCE_CHANGED_AFTER_NATIVE_RUN",
                "candidate":candidate,"baseline":baseline}
    a,b=candidate["observation"],baseline["observation"]
    if candidate["exit_code"] or baseline["exit_code"]:
        comparison="UNKNOWN_NATIVE_RUN_FAILED"
    elif (a["status"]=="WARRANTED_BOUNDED_EXECUTED_NATIVE_IDS"
          and b["status"]=="WARRANTED_BOUNDED_EXECUTED_NATIVE_IDS"):
        comparison=("TIE_EXACT_NATIVE_IDENTITIES"
                    if a["case_ids"]==b["case_ids"]
                    else "DIFFERENT_SOURCE_NATIVE_IDENTITIES")
    else:
        comparison="UNKNOWN_CASE_IDS"
    # Selective withdrawal in disposable source checkout, with exact restore.
    # This is an exposed training project and no native code runs during withdrawal.
    try:
        doc.unlink()
        after=constructor.propose(source)
        remaining=[c for c in after["all_candidates"]
                   if c["kind"]=="AUTHOR_DRIVER" and c["argv"]==KNOWN_ARGS]
        withdrawn=not remaining
    finally:
        doc.write_bytes(before)
    assert digest(doc.read_bytes())==support["sha256"]
    assert constructor.propose(source)==proposal, "restoration changed proposal"
    assert not git(source,"status","--porcelain=v1","--untracked-files=all")
    return {
      "status": ("WARRANTED_BOUNDED_EXPOSED_NATIVE_DRIVER_INSTANCE"
                 if comparison=="TIE_EXACT_NATIVE_IDENTITIES" and withdrawn
                 else "UNKNOWN_NATIVE_OR_WITHDRAWAL_SCOPE"),
      "source_repo":"trentm/python-markdown2",
      "source_sha":KNOWN_SOURCE,
      "driver_blob":receipt["git_blob"],
      "source_doc_sha256":digest(before),
      "operator_kind":"AUTHOR_DRIVER",
      "source_author_command":KNOWN_ARGS,
      "candidate":candidate,
      "equal_info_rulebook":baseline,
      "comparison":comparison,
      "withdrawal_retracts_specific_author_driver":withdrawn,
      "source_restored":True,
      "historical_author_scope":"EXPOSED_README_NATIVE_COMMAND_WITH_KNOWN_FAILURE_EXCLUSIONS",
      "author_complete_suite":"UNKNOWN (knownfailure tests deliberately excluded)",
      "human_expert_advantage":"UNKNOWN_NOT_MEASURED",
      "protected_heldout_source_read":"NONE",
      "new_grammar_type_invented":False,
      "reusable_general_observation_gain":"UNKNOWN"
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=replay(a.source,a.out)
    a.out.joinpath("result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":result["status"],"comparison":result.get("comparison"),
                      "cases":result.get("candidate",{}).get("observation",{}).get("count")},
                     sort_keys=True))
