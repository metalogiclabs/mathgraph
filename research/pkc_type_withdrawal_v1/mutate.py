#!/usr/bin/env python3
"""Exact, reproducible, local-only physical intervention on original JPL Part3.lean."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PIN = "e0deb453e05ffa63297d9704ceb47d0855193824"
REL = Path("iso80000/PropertyKindCalculus/Iso80000/Part3.lean")
BLOB = "9d3359e126fd76298c99e8f9ff5bd3658ebcf5d4"
OLD = "  | width_length : Edge width.kind length.kind"
NEW = ("  | width_length : Edge width.kind height.kind\n"
       "  | width_length_original : Edge width.kind length.kind")
PROOF = "Specializes.of_edge Edge.width_length"
PROOF_MUTANT = "Specializes.of_edge Edge.width_length_original"

def cmd(target, *args):
    return subprocess.check_output(["git", "-C", str(target), *args], text=True).strip()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--action", choices=["mutate", "restore"], required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    t = a.target.resolve()
    assert cmd(t, "rev-parse", "HEAD") == PIN
    source = t / REL
    if a.action == "mutate":
        assert not cmd(t, "diff", "--name-only"), "original source not clean"
        assert cmd(t, "hash-object", str(REL)) == BLOB, "original blob SHA mismatch"
        before = source.read_text()
        assert before.count(OLD) == 1, "original constructor site changed"
        assert before.count(PROOF) == 3, "original dependence census changed"
        changed = before.replace(OLD, NEW).replace(PROOF, PROOF_MUTANT)
        assert changed.count("  | width_length : Edge width.kind height.kind") == 1
        assert changed.count("  | width_length_original : Edge width.kind length.kind") == 1
        assert re.search(re.escape(PROOF) + r"(?!_original)", changed) is None
        assert changed.count(PROOF_MUTANT) == 3
        source.write_text(changed)
        assert cmd(t, "diff", "--name-only") == str(REL), "modified other source paths"
        assert cmd(t, "hash-object", str(REL)) != BLOB
        identity = {
            "lane": "MUTANT",
            "upstream_original_commit": PIN,
            "original_git_blob": BLOB,
            "modified_source_sha256": digest(changed.encode()),
            "modified_source_git_blob": cmd(t, "hash-object", str(REL)),
            "original_type": "Edge width.kind length.kind",
            "changed_type": "Edge width.kind height.kind",
            "original_type_preserved_under_new_name": "width_length_original",
            "dependent_proof_uses_rebound": 3,
            "changed_files": [str(REL)],
            "candidate_upstream_repair": False,
        }
        (a.out.parent / "physical-source-mutant.diff").write_text(
            subprocess.check_output(["git", "-C", str(t), "diff", "--", str(REL)], text=True))
    else:
        assert cmd(t, "diff", "--name-only") == str(REL), "wrong dirty state to restore"
        assert source.read_text().count("  | width_length : Edge width.kind height.kind") == 1
        subprocess.check_call(["git", "-C", str(t), "checkout", "--", str(REL)])
        assert cmd(t, "hash-object", str(REL)) == BLOB
        assert not cmd(t, "diff", "--name-only")
        identity = {
            "lane": "RESTORED",
            "upstream_original_commit": PIN,
            "original_git_blob": BLOB,
            "restored_source_sha256": digest(source.read_bytes()),
            "restore_clean": True,
        }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n")
    print("V7_PHYSICAL_DECLARATION_" + a.action.upper() + "_VERIFIED",
          json.dumps(identity, sort_keys=True))

if __name__ == "__main__":
    main()
