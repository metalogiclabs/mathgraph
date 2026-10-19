#!/usr/bin/env python3
"""Local-only one-line semantic emitter authority intervention."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PIN = "fdef03caf19e8862792034793da11020b39d6110"
REL = Path("L4YAML/Output/Dump.lean")
BLOB = "e6495cba339246b1954f3d4be9dd286a564cb4c0"
OLD = "  allowReservedPlain : Bool := false"
NEW = "  allowReservedPlain : Bool := true"

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--lane",choices=["MUTANT","RESTORED"],required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    root=a.source.resolve()
    assert git(root,"rev-parse","HEAD")==PIN
    f=root/REL
    if a.lane=="MUTANT":
        assert git(root,"hash-object",str(REL))==BLOB
        assert not git(root,"diff","--name-only")
        before=f.read_text()
        assert before.count(OLD)==1 and before.count(NEW)==0
        after=before.replace(OLD,NEW)
        assert after.count(NEW)==1 and after.count(OLD)==0
        f.write_text(after)
        assert git(root,"diff","--name-only")==str(REL)
        diff=subprocess.check_output(["git","-C",str(root),"diff","--",str(REL)],text=True)
        assert diff.count("-"+OLD)==1 and diff.count("+"+NEW)==1
        (a.output.parent/"scalar-default-mutant.diff").write_text(diff)
        obj={"lane":"MUTANT","original_git_commit":PIN,
             "original_git_blob":BLOB,"mutant_git_blob":git(root,"hash-object",str(REL)),
             "mutant_source_sha256":sha(f.read_bytes()),
             "changed_file":str(REL),
             "actual_edit":OLD+" => "+NEW,
             "upstream_changed":False,"candidate_repair":False}
    else:
        assert git(root,"diff","--name-only")==str(REL)
        assert f.read_text().count(NEW)==1
        subprocess.check_call(["git","-C",str(root),"checkout","--",str(REL)])
        assert git(root,"hash-object",str(REL))==BLOB
        assert not git(root,"diff","--name-only")
        obj={"lane":"RESTORED","original_git_commit":PIN,"original_git_blob":BLOB,
             "source_sha256":sha(f.read_bytes()),"clean_checkout":True}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
    print("L4YAML_V8_PHYSICAL_SOURCE_"+a.lane+"_VERIFIED",json.dumps(obj,sort_keys=True))
if __name__=="__main__":
    main()
