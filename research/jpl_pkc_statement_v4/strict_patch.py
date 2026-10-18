#!/usr/bin/env python3
"""Apply one measured fail-closed PKC import policy ONLY to CI's JPL checkout.

The authoritative source is verified against HEAD before editing; if the
expected exact source fragment changes, abort. Never update nasa-jpl upstream.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN = "e0deb453e05ffa63297d9704ceb47d0855193824"
REL = "interchange/PropertyKindCalculus/Interchange/Harvest.lean"
OLD = """  for (elem, c) in checkedOf m do
    let n := c.decl.toName
    if let some why ← notEvidence env n then
      out := out ++ [s!"{elem}: '{c.decl}' {why}"]
  return out"""
NEW = """  for (elem, c) in checkedOf m do
    -- A free-form SysML metadata string is not a typed Lean proposition.
    -- Preserve the declaration/axiom checks; refuse to certify the text.
    if c.statement.isSome then
      out := out ++ [s!"{elem}: @Checked.statement is unchecked free text; typed correspondence required"]
    let n := c.decl.toName
    if let some why ← notEvidence env n then
      out := out ++ [s!"{elem}: '{c.decl}' {why}"]
  return out"""

def run_git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("jpl_checkout", type=Path)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()
    root = args.jpl_checkout.resolve()
    if run_git(root, "rev-parse", "HEAD").decode().strip() != PIN:
        raise SystemExit("FAIL_CLOSED_UPSTREAM_SHA")
    path = root / REL
    source = path.read_bytes()
    pristine = run_git(root, "show", "HEAD:" + REL)
    if source != pristine:
        raise SystemExit("FAIL_CLOSED_NOT_PRISTINE")
    raw = source.decode()
    if raw.count(OLD) != 1 or NEW in raw:
        raise SystemExit("FAIL_CLOSED_EXPECTED_FRAGMENT_CHANGED")
    changed = raw.replace(OLD, NEW, 1)
    path.write_text(changed)
    modified = run_git(root, "diff", "--name-only").decode().splitlines()
    if modified != [REL]:
        raise SystemExit("FAIL_CLOSED_EXTRA_CHANGED_FILES " + repr(modified))
    receipt = {
        "source": "nasa-jpl/PropertyKindCalculus@" + PIN,
        "old_sha256": hashlib.sha256(source).hexdigest(),
        "new_sha256": hashlib.sha256(changed.encode()).hexdigest(),
        "changed_files": modified,
        "repair_policy": "Reject any Some @Checked.statement (unchecked text) before citation gate",
        "expected_semantics": "Statement-free proven citations remain valid; free text no longer silently attested",
        "authority": "CI checkout only, candidate policy, not an upstream fix"
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"patch_applied": True, "files": modified,
                      "original_sha256": receipt["old_sha256"],
                      "patched_sha256": receipt["new_sha256"]}))

if __name__ == "__main__":
    main()
