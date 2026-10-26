#!/usr/bin/env python3
"""Independent F1 V6 raw-evidence referee, intentionally source/output read-only.
This admits a bounded EXPOSED induced-fault witness, never whole-suite author
intention, new sensor grammar, or source-native commercial advantage.
"""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

ARCHIVE_SHA = "5972b81991a5a75b4813c20bec35802a0f1090af6daee90ddbd49d78487c7418"
SOURCE_HEAD = "58bc8bf7a0175771d050fb46ad412f377d2cc673"
SOURCE_SHA = "a3716b5e0aeba16b6e85965b2e5019d174328f36"
TARGET = "markdown2/tm/emphasis"
EXPECTED_FILES = {"result.json","original.log","candidate.log","informed.log",
                  "generic_original.log","generic.log","head.txt","experiment-blob.txt","SHA256SUMS"}
CASE = re.compile(r"^\s*((?:markdown2|cli)/.*?)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)\s*$")
INTER = re.compile(r"^\s*((?:markdown2|cli)/.*?)\s+\.\.\.\s+(WARNING:test:skipping .*)$")
WARN = re.compile(r"^WARNING:test:skipping (?:pygments|wavedrom|latex2mathml|emoji) tests .*")
COUNT = re.compile(r"\bRan\s+(\d+)\s+tests?\s+in\s+")
PYTEST = re.compile(r"(\d+) (passed|failed|skipped|xfailed|xpassed|error|errors)\b")

class Refusal(ValueError): pass
def sha(raw): return hashlib.sha256(raw).hexdigest()

def native_cases(raw):
    events=[];pending=None;bad=0
    text=raw.decode("utf8","replace")
    for line in text.splitlines():
        line=line.rstrip()
        if pending is not None:
            if WARN.fullmatch(line):continue
            if line.strip()=="ok":
                events.append((pending,"ok"));pending=None;continue
            bad+=1;pending=None
        m=CASE.fullmatch(line)
        if m:events.append((m.group(1),m.group(2)));continue
        m=INTER.fullmatch(line)
        if m:
            if WARN.fullmatch(m.group(2)):pending=m.group(1)
            else:bad+=1
            continue
        if WARN.fullmatch(line):continue
        if " ... " in line and line.lstrip().startswith(("markdown2/","cli/")):bad+=1
    counts=COUNT.findall(text)
    if len(counts)!=1 or bad or pending is not None:
        raise Refusal("UNKNOWN_NATIVE_LOG_GRAMMAR")
    if not events or int(counts[0])!=len(events) or len({x for x,_ in events})!=len(events):
        raise Refusal("UNKNOWN_NATIVE_TEST_IDENTITIES")
    return dict(events)

def generic_result(raw):
    text=raw.decode("utf8","replace")
    if "ModuleNotFoundError:" in text or "ImportError while importing" in text:
        raise Refusal("UNKNOWN_GENERIC_IMPORT_ENVIRONMENT")
    summaries=[line for line in text.splitlines()
               if re.search(r"\b\d+ (?:passed|failed|xfailed|skipped)\b",line)
               and " in " in line]
    if not summaries: raise Refusal("UNKNOWN_GENERIC_TEST_REPORT")
    outcomes={label:int(number) for number,label in PYTEST.findall(summaries[-1])}
    if not outcomes: raise Refusal("UNKNOWN_GENERIC_TEST_OUTCOME")
    return outcomes

def minimal_supports(alternatives,live):
    usable={frozenset(a) for a in alternatives if set(a)<=set(live)}
    return [sorted(a) for a in sorted(usable,key=lambda a:(len(a),sorted(a)))
            if not any(b<a for b in usable)]

def unpack(raw,expected_sha=ARCHIVE_SHA):
    if expected_sha is not None and sha(raw)!=expected_sha:
        raise Refusal("ARCHIVE_DIGEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=z.namelist()
        if len(members)!=len(EXPECTED_FILES) or set(members)!=EXPECTED_FILES:
            raise Refusal("ZIP_MEMBER_SCOPE_MISMATCH")
        if any(z.getinfo(name).file_size>2500000 for name in members):
            raise Refusal("ZIP_MEMBER_TOO_LARGE")
        files={name:z.read(name) for name in members}
    expected={}
    for line in files["SHA256SUMS"].decode().splitlines():
        m=re.fullmatch(r"([a-f0-9]{64})  evidence/f1-v5-real/([A-Za-z0-9_.-]+)",line)
        if not m or m.group(2) in expected:
            raise Refusal("INVALID_INNER_RECEIPT")
        expected[m.group(2)]=m.group(1)
    if set(expected)!=EXPECTED_FILES-{"SHA256SUMS"}:
        raise Refusal("INCOMPLETE_INNER_RECEIPT")
    if any(sha(files[name])!=expected[name] for name in expected):
        raise Refusal("INNER_RECEIPT_DIGEST_MISMATCH")
    if files["head.txt"].decode().strip()!=SOURCE_HEAD:
        raise Refusal("SOURCE_HEAD_MISMATCH")
    return files

def verify(raw,expected_sha=ARCHIVE_SHA):
    f=unpack(raw,expected_sha)
    record=json.loads(f["result.json"])
    if record.get("pinned_source")!=SOURCE_SHA or record.get("source_module_blob")!="a55f7098ab952d547e7942ddc6b8626eaf15fcfc":
        raise Refusal("SOURCE_IDENTITY_MISMATCH")
    if record.get("target_original_case")!=TARGET:
        raise Refusal("PROTECTED_TARGET_MISMATCH")
    if record.get("heldout_source_access")!="NONE":
        raise Refusal("PROTECTED_SOURCE_SCOPE_MISMATCH")
    mappings=(("original","original.log"),("candidate","candidate.log"),
              ("same_information_rulebook","informed.log"),
              ("generic_original","generic_original.log"),("fixed_generic","generic.log"))
    if any(record[key]["log_sha256"]!=sha(f[name]) for key,name in mappings):
        raise Refusal("RUNNER_LOG_BINDING_MISMATCH")
    before=native_cases(f["original.log"])
    candidate=native_cases(f["candidate.log"])
    informed=native_cases(f["informed.log"])
    if set(before)!=set(candidate) or set(candidate)!=set(informed):
        raise Refusal("UNEQUAL_NATIVE_CASE_COVERAGE")
    if before.get(TARGET)!="ok" or candidate.get(TARGET) not in ("FAIL","ERROR"):
        raise Refusal("PROTECTED_CONSEQUENCE_ABSENT")
    if candidate!=informed:
        raise Refusal("INFORMED_COMPARATOR_DISAGREES")
    if record["original"]["exit"]!=0 or record["candidate"]["exit"]==0 or record["same_information_rulebook"]["exit"]==0:
        raise Refusal("NATIVE_EXIT_INCONSISTENT")
    ordinary_before=generic_result(f["generic_original.log"])
    ordinary_after=generic_result(f["generic.log"])
    if (ordinary_before.get("failed",0) or ordinary_before.get("errors",0)
       or not ordinary_after.get("failed",0)+ordinary_after.get("errors",0)
       or record["generic_original"]["exit"]!=0 or record["fixed_generic"]["exit"]!=1):
        raise Refusal("ORDINARY_COMPARATOR_NOT_SEPARATING")
    claims={"native":[["source","author_doc","native_program","before","after","caseid"]],
            "conventional":[["source","py_before","py_after"]],
            "independent":[["oracle"]]}
    live={"source","author_doc","native_program","before","after","caseid","py_before","py_after","oracle"}
    active={key:minimal_supports(value,live) for key,value in claims.items()}
    revoked={key:minimal_supports(value,live-{"author_doc"}) for key,value in claims.items()}
    if not active["native"] or revoked["native"] or not revoked["conventional"] or not revoked["independent"]:
        raise Refusal("SELECTIVE_WITHDRAWAL_FAILED")
    return {"status":"WARRANTED_BOUNDED_EXPOSED_FAULT_WITH_CONVENTIONAL_TIE",
            "source_head":SOURCE_HEAD,"original_source":SOURCE_SHA,
            "protected_case":TARGET,"protected_before":before[TARGET],
            "protected_after":candidate[TARGET],
            "native_unique_cases":len(candidate),
            "native_failed_cases":sum(x in ("FAIL","ERROR") for x in candidate.values()),
            "same_information_native":"TIE_EXACT_CASE_VERDICTS",
            "conventional":"TIE_ON_CLEAN_VS_FAULT_DECISION",
            "generic_before":ordinary_before,"generic_after":ordinary_after,
            "selective_document_withdrawal":True,
            "alternative_independent_support_survives":True,
            "unknowns":["original author whole-suite completeness","novel sensor grammar",
                        "unopened-source transfer","human-baseline advantage","external truth"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=verify(args.archive.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],
                      "cases":result["native_unique_cases"],
                      "failures":result["native_failed_cases"],
                      "baseline":result["conventional"]},sort_keys=True))
if __name__=="__main__":main()
