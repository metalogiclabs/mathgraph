#!/usr/bin/env python3
"""Frozen L4YAML native+independent-consumer experiment observer.

The external reader AND its four reference predicates are extracted unchanged
from the exact original RED analyzer, not reinvented after mutant results.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
import yaml
from ruamel.yaml import YAML

BROKEN=("quoted_42_string","quoted_true_string","quoted_true_not_bool",
        "quoted_null_string_option","quoted_null_struct",
        "distinct_dump_option_values","round_trip_some_null")
PASS=("plain_null_option","plain_true_bool","plain_42_nat","ordinary_string")
EXTERNAL=("bool_true_is_bool_in_both","none_is_null_in_both",
          "qNone_is_null_in_both","qStringNull_is_string_in_both")
BASE_EXTERNAL={
    "bool_true_is_bool_in_both":False,
    "none_is_null_in_both":False,
    "qNone_is_null_in_both":False,
    "qStringNull_is_string_in_both":True,
}
MUTANT_EXTERNAL={name:(not value) for name,value in BASE_EXTERNAL.items()}
SOURCE="nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110"
SOURCE_PATH="L4YAML/Output/Dump.lean"
ORIGINAL_GIT_BLOB="e6495cba339246b1954f3d4be9dd286a564cb4c0"
FROZEN_ANALYZER_BLOB="1e701edbfac8ef6cd6f2b92dac28d6bc6639e7e2"
FROZEN_PROBE_BLOB="81659ba21ccfdf6e1a43879c2318a8010f58ae55"

def sha(x): return hashlib.sha256(x).hexdigest()

def git_blob(p):
    return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()

def read_native(path):
    checks={};dumps={}
    for line in path.read_text().splitlines():
        if line.startswith("CHECK:"):
            key,sep,value=line[6:].partition("=")
            assert sep and key not in checks and value in ("true","false"),line
            checks[key]=(value=="true")
        if line.startswith("DUMP:"):
            key,sep,value=line[5:].partition("=")
            assert sep and key not in dumps,line
            dumps[key]=value.replace("\\n","\n")
    assert set(checks)==set(BROKEN)|set(PASS)
    assert set(dumps)=={"true","none","qNone","qStringNull"}
    assert all(checks[k] is False for k in BROKEN), checks
    assert all(checks[k] is True for k in PASS), checks
    return checks,dumps

def independent_original_algorithm(path, dumps):
    assert git_blob(path)==FROZEN_ANALYZER_BLOB
    source=path.read_text()
    start=source.index('p12=YAML(typ="safe")')
    stop=source.index("failures=[k for k",start)
    fragment=source[start:stop]
    assert "p12.version=(1,2)" in fragment
    assert "yaml.safe_load" in fragment
    assert "independent={" in fragment
    space={"yaml":yaml,"YAML":YAML,"dumps":dumps}
    exec(compile(fragment,str(path), "exec"),space,space)
    assert set(space["independent"])==set(EXTERNAL)
    return space["independent"],sha(fragment.encode())

def check(root,target,original, lane):
    assert git_blob(original/"Probe.lean")==FROZEN_PROBE_BLOB
    reader=original/"analyze.py"
    native_log=root/f"{lane}-lean.log"
    checks,dumps=read_native(native_log)
    external,method_sha=independent_original_algorithm(reader,dumps)
    want=MUTANT_EXTERNAL if lane=="MUTANT" else BASE_EXTERNAL
    assert external==want,(lane,external,want)
    expected_dumps = (
        {"true":'true', "none":'null',
         "qNone":"x: null","qStringNull":"x: null"}
        if lane=="MUTANT" else
        {"true":'"true"', "none":'"null"',
         "qNone":'x: "null"',"qStringNull":'x: "null"'}
    )
    # Style may append a final line break; preserve full raw evidence bytes.
    assert {k: v.strip() for k,v in dumps.items()}==expected_dumps,(lane,dumps)
    src=target/SOURCE_PATH
    if lane=="MUTANT":
        mutated=json.loads((root/"physical-mutant.json").read_text())
        assert mutated["mutant_source_sha256"]==sha(src.read_bytes())
        assert mutated["original_git_blob"]==ORIGINAL_GIT_BLOB
        assert git_blob(src)==mutated["mutant_git_blob"]
        assert "allowReservedPlain : Bool := true" in src.read_text()
    else:
        assert git_blob(src)==ORIGINAL_GIT_BLOB
        assert "allowReservedPlain : Bool := false" in src.read_text()
    receipt={
        "lane":lane,"source":SOURCE,
        "source_file_sha256":sha(src.read_bytes()),
        "source_file_git_blob":git_blob(src),
        "native_checks":checks,
        "independent_checks":external,
        "native_dumps":dumps,
        "frozen_lean_stdout_sha256":sha(native_log.read_bytes()),
        "external_oracle_method_sha256":method_sha,
        "original_oracle_file_git_blob":FROZEN_ANALYZER_BLOB,
        "original_native_probe_git_blob":FROZEN_PROBE_BLOB,
        "original_source_changed_only_in_ephemeral_runner":(lane=="MUTANT"),
    }
    (root/f"{lane}-receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("L4YAML_V8_NATIVE_AND_BOTH_INDEPENDENT_READERS_QUALIFIED",lane,
          json.dumps(external,sort_keys=True))

def finalize(root):
    receipts=[json.loads((root/f"{name}-receipt.json").read_text())
              for name in ("BASE","MUTANT","RESTORED")]
    a,b,c=receipts
    assert a["native_checks"]==b["native_checks"]==c["native_checks"]
    assert a["independent_checks"]==c["independent_checks"]==BASE_EXTERNAL
    assert b["independent_checks"]==MUTANT_EXTERNAL
    assert a["source_file_sha256"]==c["source_file_sha256"]
    assert a["source_file_sha256"]!=b["source_file_sha256"]
    assert a["source_file_git_blob"]==c["source_file_git_blob"]==ORIGINAL_GIT_BLOB
    assert len(set(q["external_oracle_method_sha256"] for q in receipts))==1
    assert set(k for k in EXTERNAL
               if a["independent_checks"][k]!=b["independent_checks"][k])==set(EXTERNAL)
    assert {x for x in BROKEN if a["native_checks"][x]!=b["native_checks"][x]}==set()
    result={
        "status":"WARRANTED_BOUNDED_PHYSICAL_L4YAML_SCALAR_POLICY_CAUSAL_REVERSAL",
        "original_source":SOURCE,
        "source_change":"one-line DumpConfig.allowReservedPlain default false->true->false",
        "original_upstream_source_unchanged":True,
        "lanes":{rec["lane"]:rec for rec in receipts},
        "external_interpretations_flipped":list(EXTERNAL),
        "source_native_checks_retained":{**{k:False for k in BROKEN},
                                         **{k:True for k in PASS}},
        "local_mutation_not_an_upstream_fix":True,
        "all_original_native_7_red_remain_red":True,
        "limits":[
            "Four selected Core Schema reader observations only",
            "No full YAML fixed-GREEN established",
            "One intentionally synthetic source policy intervention, not a repair",
            "The unchanged original parser accepts source-native inputs but does not itself prove external semantic preservation",
        ],
    }
    (root/"v8-result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("L4YAML_V8_SOURCE_NATIVE_PHYSICAL_MUTATION_RESTORATION_PASS")
    print(json.dumps({q["lane"]:q["independent_checks"] for q in receipts},sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["check","finalize"])
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--target",type=Path)
    p.add_argument("--original",type=Path)
    p.add_argument("--lane",choices=["BASE","MUTANT","RESTORED"])
    a=p.parse_args()
    if a.command=="check":
        assert a.target and a.original and a.lane
        check(a.root,a.target,a.original,a.lane)
    else:
        finalize(a.root)
