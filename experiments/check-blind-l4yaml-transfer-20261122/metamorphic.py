#!/usr/bin/env python3
"""Metamorphic relation runner: evaluates paired observations, not claimed correctness."""
import argparse
import hashlib
import json
from pathlib import Path
from probe import execute

def relation(left, right, rule):
    if left["kind"] != "EXECUTED" or right["kind"] != "EXECUTED":
        return "UNKNOWN"
    if rule == "same_exit":
        equal = left["exit"] == right["exit"]
    elif rule == "same_stdout":
        equal = left["exit"] == right["exit"] and left["stdout_sha256"] == right["stdout_sha256"]
    elif rule == "same_stderr":
        equal = left["exit"] == right["exit"] and left["stderr_sha256"] == right["stderr_sha256"]
    else:
        return "UNKNOWN"
    return "RELATION_SATISFIED" if equal else "RELATION_VIOLATED"

def run(spec, repo, timeout):
    rows = []
    for pair in spec["pairs"]:
        left = execute(pair["left"], repo, timeout)
        right = execute(pair["right"], repo, timeout)
        rows.append({"id": pair["id"], "relation": pair["relation"],
                     "requirement": pair["requirement"], "left": left, "right": right,
                     "status": relation(left, right, pair["relation"])})
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--revision", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()
    if not 1 <= args.timeout <= 600:
        p.error("invalid timeout")
    out = Path(args.out)
    if out.exists():
        p.error("output already exists")
    spec_bytes = Path(args.spec).read_bytes()
    spec = json.loads(spec_bytes)
    if spec.get("schema") != "mathgraph.metamorphic-pairs.v0" or not spec.get("pairs"):
        p.error("invalid schema or empty pairs")
    ids = []
    for pair in spec["pairs"]:
        ids.append(pair["id"])
        if (not isinstance(pair.get("requirement"), str) or not pair["requirement"].strip()
            or pair.get("relation") not in ("same_exit", "same_stdout", "same_stderr")
            or any(not isinstance(pair.get(side), list) or not pair[side]
                   or not all(isinstance(x, str) and x for x in pair[side])
                   for side in ("left", "right"))):
            p.error("invalid pair")
    if len(ids) != len(set(ids)):
        p.error("duplicate IDs")
    repo = str(Path(args.repo).resolve())
    before = execute(["git", "rev-parse", "HEAD"], repo, args.timeout)
    dirty = execute(["git", "status", "--porcelain", "--untracked-files=all"], repo, args.timeout)
    if (before["kind"] != "EXECUTED" or before["exit"] != 0 or
        before["stdout"].strip() != args.revision or
        dirty["kind"] != "EXECUTED" or dirty["exit"] != 0 or dirty["stdout"].strip()):
        p.error("source revision mismatch or dirty tree")
    rows = run(spec, repo, args.timeout)
    after = execute(["git", "rev-parse", "HEAD"], repo, args.timeout)
    after_dirty = execute(["git", "status", "--porcelain", "--untracked-files=all"], repo, args.timeout)
    stable = (after["kind"] == "EXECUTED" and after["exit"] == 0 and
              after["stdout"].strip() == args.revision and
              after_dirty["kind"] == "EXECUTED" and after_dirty["exit"] == 0 and
              not after_dirty["stdout"].strip())
    status = ("UNKNOWN" if not stable or any(x["status"] == "UNKNOWN" for x in rows)
              else "RELATION_VIOLATIONS" if any(x["status"] == "RELATION_VIOLATED" for x in rows)
              else "BOUNDED_RELATION_AGREEMENT")
    receipt = {"schema": "mathgraph.metamorphic-receipt.v0", "status": status,
               "source_revision": args.revision, "source_stable": stable,
               "spec_sha256": hashlib.sha256(spec_bytes).hexdigest(), "pairs": rows,
               "requirement_validity": "UNVERIFIED", "novelty": "UNKNOWN",
               "blindness": "NOT_ESTABLISHED", "model_calls": 0,
               "boundary": "Pairwise observed relation only; independent requirement warrant absent"}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "pairs": len(rows)}))
    return 2 if status == "UNKNOWN" else 1 if status == "RELATION_VIOLATIONS" else 0

if __name__ == "__main__":
    raise SystemExit(main())
